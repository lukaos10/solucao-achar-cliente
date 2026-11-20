import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.classify import (
    classificar,
    eh_rede,
    endereco_de,
    bairro_de,
    link_mapa,
    telefone_de,
    tipo_legivel,
    whatsapp_de,
)
from app.nichos import nicho_de, nome_de
from app.sites import chave_marca, sites_por_nome

CAMINHO = Path(__file__).resolve().parent.parent / "data" / "leads.db"


def conexao() -> sqlite3.Connection:
    CAMINHO.parent.mkdir(parents=True, exist_ok=True)
    banco = sqlite3.connect(CAMINHO, timeout=30)
    banco.execute("PRAGMA journal_mode=WAL")
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
    colunas = {linha[1] for linha in banco.execute("PRAGMA table_info(leads)")}
    if "cidade" not in colunas:
        banco.execute("ALTER TABLE leads ADD COLUMN cidade TEXT NOT NULL DEFAULT 'Fortaleza'")
    if "uf" not in colunas:
        banco.execute("ALTER TABLE leads ADD COLUMN uf TEXT NOT NULL DEFAULT 'CE'")
    if "nicho" not in colunas:
        banco.execute("ALTER TABLE leads ADD COLUMN nicho TEXT NOT NULL DEFAULT ''")
    banco.execute(
        """
        CREATE TABLE IF NOT EXISTS bairros (
            cidade TEXT NOT NULL,
            uf TEXT NOT NULL,
            nome TEXT NOT NULL,
            PRIMARY KEY (cidade, uf, nome)
        )
        """
    )
    banco.execute(
        """
        CREATE TABLE IF NOT EXISTS sites_cache (
            marca TEXT NOT NULL,
            cidade TEXT NOT NULL,
            uf TEXT NOT NULL,
            site TEXT NOT NULL,
            PRIMARY KEY (marca, cidade, uf)
        )
        """
    )
    return banco


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def guardar_bairros(cidade: str, uf: str, nomes: list[str]) -> None:
    with conexao() as banco:
        banco.executemany(
            "INSERT OR IGNORE INTO bairros (cidade, uf, nome) VALUES (?, ?, ?)",
            [(cidade, uf, nome) for nome in nomes],
        )


def bairros_guardados(cidade: str, uf: str) -> list[str]:
    with conexao() as banco:
        linhas = banco.execute(
            """
            SELECT nome FROM bairros
            WHERE cidade = ? AND uf = ?
            ORDER BY nome COLLATE NOCASE
            """,
            (cidade, uf),
        ).fetchall()
    return [linha["nome"] for linha in linhas]


def _cache_de(banco: sqlite3.Connection, cidade: str, uf: str) -> dict[str, str]:
    linhas = banco.execute(
        "SELECT marca, site FROM sites_cache WHERE cidade = ? AND uf = ?",
        (cidade.strip(), uf.strip().upper()),
    ).fetchall()
    return {linha["marca"]: linha["site"] for linha in linhas}


def _guardar_cache(banco: sqlite3.Connection, cidade: str, uf: str, achados: dict[str, str]) -> None:
    banco.executemany(
        "INSERT OR REPLACE INTO sites_cache (marca, cidade, uf, site) VALUES (?, ?, ?, ?)",
        [(marca, cidade.strip(), uf.strip().upper(), site) for marca, site in achados.items()],
    )


def _marcar_tem_site(banco: sqlite3.Connection, cidade: str, uf: str, marca: str, site: str) -> int:
    if not marca or not site:
        return 0
    linhas = banco.execute(
        """
        SELECT id, nome FROM leads
        WHERE cidade = ? AND uf = ? AND presenca != 'tem_site'
        """,
        (cidade.strip(), uf.strip().upper()),
    ).fetchall()
    ids = [linha["id"] for linha in linhas if chave_marca(linha["nome"]) == marca]
    momento = agora()
    banco.executemany(
        """
        UPDATE leads
        SET presenca = 'tem_site',
            site = ?,
            status = CASE WHEN status = 'novo' THEN 'tem_site' ELSE status END,
            atualizado_em = ?
        WHERE id = ?
        """,
        [(site, momento, item) for item in ids],
    )
    return len(ids)


def _consultar_sites(cidade: str, uf: str, consultas: list[tuple[str, str]]) -> dict[str, str]:
    with conexao() as banco:
        cache = _cache_de(banco, cidade, uf)
    faltam = []
    vistos = set(cache)
    for nome, endereco in consultas:
        marca = chave_marca(nome)
        if len(marca) < 5 or marca in vistos:
            continue
        vistos.add(marca)
        faltam.append((nome, cidade, endereco))
    if not faltam:
        return cache
    achados: dict[str, str] = {}
    for inicio in range(0, len(faltam), 40):
        bloco = faltam[inicio : inicio + 40]
        achados.update(sites_por_nome(bloco))
        with conexao() as banco:
            _guardar_cache(banco, cidade, uf, {chave_marca(nome): achados.get(chave_marca(nome), "") for nome, _cidade, _endereco in bloco})
    cache.update(achados)
    return cache


def reverificar_pendentes() -> int:
    with conexao() as banco:
        linhas = banco.execute(
            """
            SELECT nome, cidade, uf, endereco FROM leads
            WHERE presenca != 'tem_site'
            """
        ).fetchall()
    grupos: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for linha in linhas:
        chave = (linha["cidade"] or "", (linha["uf"] or "").upper())
        grupos.setdefault(chave, []).append((linha["nome"], linha["endereco"] or ""))
    atualizados = 0
    for (cidade, uf), consultas in grupos.items():
        achados = _consultar_sites(cidade, uf, consultas)
        with conexao() as banco:
            vistos: set[str] = set()
            for nome, _endereco in consultas:
                marca = chave_marca(nome)
                site = achados.get(marca, "")
                if not site or marca in vistos:
                    continue
                vistos.add(marca)
                atualizados += _marcar_tem_site(banco, cidade, uf, marca, site)
    return atualizados


def importar(cidade: str, uf: str, bairro: str, elementos: list[dict], nicho: str = "") -> dict:
    gravados = 0
    ignorados = 0
    com_site = 0
    preparados = []
    for elemento in elementos:
        tags = elemento.get("tags") or {}
        nome = (tags.get("name") or "").strip()
        if not nome or eh_rede(nome):
            ignorados += 1
            continue
        endereco = endereco_de(tags)
        presenca, site = classificar(
            tags.get("website")
            or tags.get("contact:website")
            or tags.get("url")
            or tags.get("contact:url")
        )
        preparados.append((elemento, tags, nome, endereco, presenca, site))
    achados = _consultar_sites(
        cidade,
        uf,
        [(nome, endereco) for _el, _tags, nome, endereco, presenca, _site in preparados if presenca != "tem_site"],
    )
    marcadas: set[str] = set()
    with conexao() as banco:
        for _elemento, tags, nome, endereco, presenca, site in preparados:
            marca = chave_marca(nome)
            if presenca != "tem_site" and achados.get(marca):
                presenca, site = "tem_site", achados[marca]
                if marca not in marcadas:
                    _marcar_tem_site(banco, cidade, uf, marca, site)
                    marcadas.add(marca)
                com_site += 1
            if presenca == "tem_site":
                ignorados += 1
                continue
            telefone = telefone_de(tags)
            bairro_lead = bairro.strip() or bairro_de(tags)
            nicho_lead = nome_de(nicho) or nicho_de(tags)
            osm_key = f"{_elemento.get('type')}/{_elemento.get('id')}"
            banco.execute(
                """
                INSERT INTO leads (
                    osm_key, nome, tipo, nicho, presenca, telefone, whatsapp,
                    endereco, bairro, cidade, uf, site, maps, atualizado_em
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(osm_key) DO UPDATE SET
                    nome = excluded.nome,
                    tipo = excluded.tipo,
                    nicho = excluded.nicho,
                    presenca = excluded.presenca,
                    telefone = excluded.telefone,
                    whatsapp = excluded.whatsapp,
                    endereco = excluded.endereco,
                    bairro = CASE WHEN excluded.bairro != '' THEN excluded.bairro ELSE bairro END,
                    cidade = excluded.cidade,
                    uf = excluded.uf,
                    site = excluded.site,
                    maps = excluded.maps,
                    atualizado_em = excluded.atualizado_em
                """,
                (
                    osm_key,
                    nome,
                    tipo_legivel(tags),
                    nicho_lead,
                    presenca,
                    telefone,
                    whatsapp_de(telefone),
                    endereco,
                    bairro_lead,
                    cidade.strip(),
                    uf.strip().upper(),
                    site,
                    link_mapa(nome, endereco, bairro_lead, cidade),
                    agora(),
                ),
            )
            gravados += 1
    return {"gravados": gravados, "ignorados": ignorados, "com_site": com_site}


def listar(
    cidade: str = "",
    uf: str = "",
    bairro: str = "",
    nicho: str = "",
    presenca: str = "",
    status: str = "",
    busca: str = "",
) -> list[dict]:
    clausulas = ["1 = 1"]
    valores: list[str] = []
    if cidade:
        clausulas.append("cidade = ?")
        valores.append(cidade)
    if uf:
        clausulas.append("uf = ?")
        valores.append(uf.upper())
    if bairro:
        clausulas.append("bairro = ?")
        valores.append(bairro)
    if nicho:
        clausulas.append("(nicho = ? OR (nicho = '' AND tipo = ?))")
        valores.extend([nicho, nicho.lower()])
    if presenca:
        clausulas.append("presenca = ?")
        valores.append(presenca)
    elif status != "tem_site":
        clausulas.append("presenca != 'tem_site'")
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
