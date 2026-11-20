import httpx

from app.nichos import consulta_de

ENDPOINTS = (
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)
USER_AGENT = "solucao-achar-cliente/0.1 (local lead queue; OpenStreetMap)"


class OverpassError(Exception):
    pass


def consultar(query: str, timeout: int = 50) -> dict:
    ultimo_erro = "o mapa não respondeu"
    for url in ENDPOINTS:
        try:
            resposta = httpx.post(
                url,
                content=query.encode("utf-8"),
                headers={"User-Agent": USER_AGENT},
                timeout=timeout,
            )
            resposta.raise_for_status()
            return resposta.json()
        except (httpx.HTTPError, ValueError):
            ultimo_erro = "Os servidores do OpenStreetMap não responderam. Tente de novo em um minuto."
    raise OverpassError(ultimo_erro)


def escapar(nome: str) -> str:
    return nome.replace("\\", "\\\\").replace('"', '\\"')


def nomes_de(dados: dict) -> list[str]:
    return sorted(
        {
            (elemento.get("tags") or {}).get("name", "").strip()
            for elemento in dados.get("elements") or []
        }
        - {""},
        key=str.casefold,
    )


def bairros_da_cidade(cidade: str, estado: str) -> list[str]:
    cidade_mapa = escapar(cidade.strip())
    estado_mapa = escapar(estado.strip())
    if not cidade_mapa or not estado_mapa:
        raise OverpassError("Escolha uma cidade da lista.")
    relacoes = consultar(
        f"""
[out:json][timeout:60];
area["name"="{estado_mapa}"]["boundary"="administrative"]["admin_level"="4"]->.uf;
relation["boundary"="administrative"]["admin_level"="8"]["name"="{cidade_mapa}"](area.uf);
map_to_area -> .cidade;
relation["boundary"="administrative"]["admin_level"="10"]["name"](area.cidade);
out tags;
"""
    )
    nomes = nomes_de(relacoes)
    if nomes:
        return nomes
    lugares = consultar(
        f"""
[out:json][timeout:60];
area["name"="{estado_mapa}"]["boundary"="administrative"]["admin_level"="4"]->.uf;
relation["boundary"="administrative"]["admin_level"="8"]["name"="{cidade_mapa}"](area.uf);
map_to_area -> .cidade;
nwr["place"~"suburb|neighbourhood|quarter"]["name"](area.cidade);
out tags;
"""
    )
    return nomes_de(lugares)


def comercios_do_bairro(cidade: str, estado: str, bairro: str, nicho: str) -> list[dict]:
    cidade_mapa = escapar(cidade.strip())
    estado_mapa = escapar(estado.strip())
    nome = escapar(bairro.strip())
    if not cidade_mapa or not estado_mapa:
        raise OverpassError("Escolha uma cidade da lista.")
    bloco = consulta_de(nicho)
    if bloco is None:
        raise OverpassError("Escolha um nicho da lista.")
    if not nome:
        return comercios_da_cidade(cidade, cidade_mapa, estado_mapa, bloco)
    confirmacao = consultar(
        f"""
[out:json][timeout:60];
area["name"="{estado_mapa}"]["boundary"="administrative"]["admin_level"="4"]->.uf;
relation["boundary"="administrative"]["admin_level"="8"]["name"="{cidade_mapa}"](area.uf);
map_to_area -> .city;
relation["name"="{nome}"]["boundary"="administrative"](area.city);
out ids;
"""
    )
    if not confirmacao.get("elements"):
        raise OverpassError(
            f"Não encontrei o bairro {bairro.strip()} no mapa de {cidade.strip()}."
        )
    dados = consultar(
        f"""
[out:json][timeout:90];
area["name"="{estado_mapa}"]["boundary"="administrative"]["admin_level"="4"]->.uf;
relation["boundary"="administrative"]["admin_level"="8"]["name"="{cidade_mapa}"](area.uf);
map_to_area -> .city;
relation["name"="{nome}"]["boundary"="administrative"](area.city);
map_to_area -> .bairro;
(
{bloco}
);
out center tags;
"""
    )
    return dados.get("elements") or []


def comercios_da_cidade(cidade: str, cidade_mapa: str, estado_mapa: str, bloco: str) -> list[dict]:
    confirmacao = consultar(
        f"""
[out:json][timeout:60];
area["name"="{estado_mapa}"]["boundary"="administrative"]["admin_level"="4"]->.uf;
relation["boundary"="administrative"]["admin_level"="8"]["name"="{cidade_mapa}"](area.uf);
out ids;
"""
    )
    if not confirmacao.get("elements"):
        raise OverpassError(f"Não encontrei {cidade.strip()} no mapa.")
    dados = consultar(
        f"""
[out:json][timeout:120];
area["name"="{estado_mapa}"]["boundary"="administrative"]["admin_level"="4"]->.uf;
relation["boundary"="administrative"]["admin_level"="8"]["name"="{cidade_mapa}"](area.uf);
map_to_area -> .cidade;
(
{bloco.replace("(area.bairro)", "(area.cidade)")}
);
out center tags;
""",
        timeout=130,
    )
    return dados.get("elements") or []
