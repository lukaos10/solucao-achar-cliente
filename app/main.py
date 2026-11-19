from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.db import BAIRROS, atualizar, importar, listar
from app.overpass import OverpassError, comercios_do_bairro

app = FastAPI(title="Fila sem site")
PAGINA = Path(__file__).parent / "static" / "index.html"


class Busca(BaseModel):
    bairro: str = Field(min_length=2, max_length=80)


class Atualizacao(BaseModel):
    status: str
    nota: str = ""


@app.get("/")
def inicio():
    return FileResponse(PAGINA)


@app.get("/api/bairros")
def bairros():
    return {"bairros": BAIRROS}


@app.get("/api/leads")
def leads(bairro: str = "", presenca: str = "", status: str = "", busca: str = ""):
    return {"leads": listar(bairro, presenca, status, busca)}


@app.post("/api/buscar")
def buscar(pedido: Busca):
    try:
        elementos = comercios_do_bairro(pedido.bairro)
    except OverpassError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    resumo = importar(pedido.bairro, elementos)
    return {**resumo, "leads": listar(pedido.bairro)}


@app.patch("/api/leads/{lead_id}")
def salvar(lead_id: int, pedido: Atualizacao):
    try:
        lead = atualizar(lead_id, pedido.status, pedido.nota)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead não encontrado.")
    return lead
