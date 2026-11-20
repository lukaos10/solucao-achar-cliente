from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.db import atualizar, bairros_guardados, guardar_bairros, importar, listar
from app.locais import bairros_fortaleza, cidades, estado_de
from app.nichos import consulta_de, nome_de, nomes
from app.overpass import OverpassError, bairros_da_cidade, comercios_do_bairro

app = FastAPI(title="Fila sem site")
PAGINA = Path(__file__).parent / "static" / "index.html"


class Busca(BaseModel):
    cidade: str = Field(min_length=2, max_length=80)
    uf: str = Field(min_length=2, max_length=2)
    bairro: str = Field(default="", max_length=80)
    nicho: str = Field(default="", max_length=40)


class Atualizacao(BaseModel):
    status: str
    nota: str = ""


@app.get("/")
def inicio():
    return FileResponse(PAGINA)


@app.get("/api/cidades")
def lista_cidades():
    return {"cidades": cidades()}


@app.get("/api/bairros")
def bairros(cidade: str, uf: str):
    cidade = cidade.strip()
    uf = uf.strip().upper()
    estado = estado_de(cidade, uf)
    if not estado:
        raise HTTPException(status_code=400, detail="Escolha uma cidade da lista.")
    guardados = bairros_guardados(cidade, uf)
    if guardados:
        return {"bairros": guardados}
    if cidade == "Fortaleza" and uf == "CE":
        nomes = bairros_fortaleza()
        guardar_bairros(cidade, uf, nomes)
        return {"bairros": nomes}
    try:
        nomes = bairros_da_cidade(cidade, estado)
    except OverpassError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    guardar_bairros(cidade, uf, nomes)
    return {"bairros": nomes}


@app.get("/api/nichos")
def lista_nichos():
    return {"nichos": nomes()}


@app.get("/api/leads")
def leads(
    cidade: str = "",
    uf: str = "",
    bairro: str = "",
    nicho: str = "",
    presenca: str = "",
    status: str = "",
    busca: str = "",
):
    return {"leads": listar(cidade, uf, bairro, nicho, presenca, status, busca)}


@app.post("/api/buscar")
def buscar(pedido: Busca):
    estado = estado_de(pedido.cidade.strip(), pedido.uf.strip().upper())
    if not estado:
        raise HTTPException(status_code=400, detail="Escolha uma cidade da lista.")
    if consulta_de(pedido.nicho.strip()) is None:
        raise HTTPException(status_code=400, detail="Escolha um nicho da lista.")
    try:
        elementos = comercios_do_bairro(pedido.cidade, estado, pedido.bairro, pedido.nicho.strip())
    except OverpassError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"A busca falhou ({type(exc).__name__}).") from exc
    try:
        resumo = importar(pedido.cidade, pedido.uf, pedido.bairro, elementos, pedido.nicho.strip())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"A busca falhou ({type(exc).__name__}).") from exc
    return {
        **resumo,
        "leads": listar(
            pedido.cidade.strip(),
            pedido.uf,
            pedido.bairro.strip(),
            nome_de(pedido.nicho.strip()),
        ),
    }


@app.patch("/api/leads/{lead_id}")
def salvar(lead_id: int, pedido: Atualizacao):
    try:
        lead = atualizar(lead_id, pedido.status, pedido.nota)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead não encontrado.")
    return lead
