import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.classify import (
    classificar,
    eh_rede,
    endereco_de,
    link_mapa,
    telefone_de,
    tipo_legivel,
    whatsapp_de,
)

CAMINHO = Path(__file__).resolve().parent.parent / "data" / "leads.db"

BAIRROS = (
    "Aldeota",
    "Meireles",
    "Varjota",
    "Mucuripe",
    "Praia de Iracema",
    "Centro",
    "Dionísio Torres",
    "Joaquim Távora",
    "São João do Tauape",
    "Papicu",
    "Cocó",
    "Fátima",
    "Benfica",
    "Montese",
    "Parangaba",
    "Bom Jardim",
    "Cajazeiras",
    "Vila Peri",
)


def conexao() -> sqlite3.Connection:
    CAMINHO.parent.mkdir(parents=True, exist_ok=True)
    banco = sqlite3.connect(CAMINHO)
    banco.row_factory = sqlite3.Row
    banco.execute(
        """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY,
            osm_key TEXT UNIQUE,
            nome TEXT NOT NULL,
            tipo TEXT,
            presenca TEXT NOT NULL,
            telefone TEXT,
            whatsapp TEXT,
            endereco TEXT,
            bairro TEXT,
            site TEXT,
            maps TEXT,
            status TEXT NOT NULL DEFAULT 'novo',
            nota TEXT NOT NULL DEFAULT '',
            atualizado_em TEXT NOT NULL
        )
        """
    )
    return banco


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def importar(bairro: str, elementos: list[dict]) -> dict:
    gravados = 0
    ignorados = 0
    with conexao() as banco:
        for elemento in elementos:
            tags = elemento.get("tags") or {}
            nome = (tags.get("name") or "").strip()
            if not nome or eh_rede(nome):
                ignorados += 1
                continue
            presenca, site = classificar(
                tags.get("website") or tags.get("contact:website") or tags.get("url")
            )
            if presenca == "tem_site":
                ignorados += 1
                continue
            telefone = telefone_de(tags)
            endereco = endereco_de(tags)
            osm_key = f"{elemento.get('type')}/{elemento.get('id')}"
            banco.execute(
                """
                INSERT INTO leads (
                    osm_key, nome, tipo, presenca, telefone, whatsapp,
                    endereco, bairro, site, maps, atualizado_em
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(osm_key) DO UPDATE SET
                    nome = excluded.nome,
                    tipo = excluded.tipo,
                    presenca = excluded.presenca,
                    telefone = excluded.telefone,
                    whatsapp = excluded.whatsapp,
                    endereco = excluded.endereco,
                    bairro = excluded.bairro,
                    site = excluded.site,
                    maps = excluded.maps,
                    atualizado_em = excluded.atualizado_em
                """,
                (
                    osm_key,
                    nome,
                    tipo_legivel(tags),
                    presenca,
                    telefone,
                    whatsapp_de(telefone),
                    endereco,
                    bairro.strip(),
                    site,
                    link_mapa(nome, endereco, bairro),
                    agora(),
                ),
            )
            gravados += 1
    return {"gravados": gravados, "ignorados": ignorados}


def listar(bairro: str = "", presenca: str = "", status: str = "", busca: str = "") -> list[dict]:
    clausulas = ["1 = 1"]
    valores: list[str] = []
    if bairro:
        clausulas.append("bairro = ?")
        valores.append(bairro)
    if presenca:
        clausulas.append("presenca = ?")
        valores.append(presenca)
    if status:
        clausulas.append("status = ?")
        valores.append(status)
    if busca:
        clausulas.append("(nome LIKE ? OR endereco LIKE ? OR telefone LIKE ? OR tipo LIKE ?)")
        termo = f"%{busca}%"
        valores.extend([termo, termo, termo, termo])
    with conexao() as banco:
        linhas = banco.execute(
            f"""
            SELECT * FROM leads
            WHERE {' AND '.join(clausulas)}
            ORDER BY nome COLLATE NOCASE
            """,
            valores,
        ).fetchall()
    return [dict(linha) for linha in linhas]


def atualizar(lead_id: int, status: str, nota: str) -> dict | None:
    permitidos = {"novo", "ligar", "tem_site", "nao_perturbe", "proposta", "fechado"}
    if status not in permitidos:
        raise ValueError("Status inválido.")
    with conexao() as banco:
        banco.execute(
            "UPDATE leads SET status = ?, nota = ?, atualizado_em = ? WHERE id = ?",
            (status, nota, agora(), lead_id),
        )
        linha = banco.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    return dict(linha) if linha else None
