import os
import re
import socket
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import httpx

from app.classify import classificar, sem_acento

RUIDO = {
    "bar",
    "cafeteria",
    "cafe",
    "clinica",
    "da",
    "das",
    "de",
    "delivery",
    "do",
    "dos",
    "e",
    "em",
    "express",
    "filial",
    "food",
    "lanchonete",
    "lanche",
    "loja",
    "matriz",
    "oficial",
    "pizzaria",
    "pizza",
    "restaurante",
    "salao",
    "shopping",
    "unidade",
}

GRAFIAS = {
    "stylo": ("estylo", "estilo"),
    "stylos": ("estylos", "estilos"),
    "estylo": ("estilo", "stylo"),
    "estylos": ("estilos", "stylos"),
    "estilo": ("estylo",),
    "estilos": ("estylos",),
}

CANON = {
    "stylo": "estilo",
    "estylo": "estilo",
    "estilo": "estilo",
    "stylos": "estilos",
    "estylos": "estilos",
    "estilos": "estilos",
}

HOSPEDES = (
    "instagram.com",
    "facebook.com",
    "fb.com",
    "fb.me",
    "linktr.ee",
    "tiktok.com",
    "wa.me",
    "whatsapp.com",
    "google.com",
    "goo.gl",
    "youtube.com",
    "ifood.com.br",
    "rappi.com.br",
    "tripadvisor.com",
    "tripadvisor.com.br",
    "telelistas.net",
    "apontador.com.br",
    "guiamais.com.br",
    "solutudo.com.br",
    "wikipedia.org",
    "yelp.com",
)

AVISO_PARK = (
    "dominio a venda",
    "domain for sale",
    "this domain is parked",
    "buy this domain",
    "sedoparking",
    "hugedomains",
)

RUAS = {"avenida", "rua", "av", "travessa", "praca", "alameda", "rodovia", "numero"}


def chave_marca(nome: str) -> str:
    return "".join(CANON.get(palavra, palavra) for palavra in _palavras(nome))


def site_proprio(nome: str, cidade: str, endereco: str = "") -> str:
    return sites_por_nome([(nome, cidade, endereco)]).get(chave_marca(nome), "")


def sites_por_nome(consultas: list[tuple[str, str, str]]) -> dict[str, str]:
    unicos: dict[str, tuple[str, str, str]] = {}
    for nome, cidade, endereco in consultas:
        marca = chave_marca(nome)
        if len(marca) < 5 or marca.isdigit():
            continue
        atual = unicos.get(marca)
        if atual is None or (endereco and not atual[2]):
            unicos[marca] = (nome, cidade, endereco)
    if not unicos:
        return {}
    itens = list(unicos.items())
    if os.environ.get("VERCEL"):
        return dict(_consultar(item) for item in itens)
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            return dict(pool.map(_consultar, itens))
    except RuntimeError:
        return dict(_consultar(item) for item in itens)


def _consultar(item: tuple[str, tuple[str, str, str]]) -> tuple[str, str]:
    marca, (nome, cidade, endereco) = item
    try:
        for slug in _candidatos(nome):
            for sufixo in (".com.br", ".com"):
                host = slug + sufixo
                if not _resolve(host):
                    continue
                pagina = _baixar(f"https://{host}")
                if pagina and _confirma(pagina, marca, cidade, endereco):
                    return marca, pagina[0]
    except Exception:
        return marca, ""
    return marca, ""


def _palavras(nome: str) -> list[str]:
    texto = sem_acento(nome).replace("'", "").replace("’", "").replace("´", "")
    return [
        palavra
        for palavra in re.findall(r"[a-z0-9]+", texto)
        if palavra not in RUIDO and not (len(palavra) == 1 and palavra.isalpha())
    ]


def _candidatos(nome: str) -> list[str]:
    palavras = _palavras(nome)
    if not palavras:
        return []
    slugs = ["".join(palavras)]
    for indice, palavra in enumerate(palavras):
        for grafia in GRAFIAS.get(palavra, ()):
            copia = palavras[:]
            copia[indice] = grafia
            slugs.append("".join(copia))
    unicos = []
    for slug in slugs:
        if len(slug) >= 5 and not slug.isdigit() and slug not in unicos:
            unicos.append(slug)
    return unicos[:6]


def _resolve(host: str) -> bool:
    try:
        socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        return True
    except OSError:
        return False


def _baixar(url: str) -> tuple[str, str] | None:
    try:
        resposta = httpx.get(
            url,
            timeout=httpx.Timeout(6.0, connect=3.0),
            follow_redirects=True,
            headers={"User-Agent": "solucao-achar-cliente/0.1 (verificacao de site proprio)"},
        )
    except httpx.HTTPError:
        return None
    if resposta.status_code >= 400:
        return None
    final = str(resposta.url)
    host = (urlparse(final).hostname or "").lower().removeprefix("www.")
    if not host or any(host == item or host.endswith("." + item) for item in HOSPEDES):
        return None
    presenca, site = classificar(final)
    if presenca != "tem_site":
        return None
    return site, resposta.text[:80_000]


def _confirma(pagina: tuple[str, str], marca: str, cidade: str, endereco: str) -> bool:
    _site, html = pagina
    visivel = re.sub(r"\s+", " ", sem_acento(re.sub(r"<[^>]+>", " ", html)))
    if any(aviso in visivel for aviso in AVISO_PARK):
        return False
    compacto = re.sub(r"[^a-z0-9]", "", visivel)
    for origem, destino in (
        ("estylos", "estilos"),
        ("stylos", "estilos"),
        ("estylo", "estilo"),
        ("stylo", "estilo"),
    ):
        compacto = compacto.replace(origem, destino)
    if marca not in compacto:
        return False
    if cidade and sem_acento(cidade) in visivel:
        return True
    for parte in re.findall(r"[a-z0-9]+", sem_acento(endereco)):
        if len(parte) >= 5 and parte not in RUAS and not parte.isdigit() and parte in visivel:
            return True
    return False
