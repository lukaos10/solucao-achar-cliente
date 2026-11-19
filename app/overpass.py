import httpx

ENDPOINTS = (
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)
BBOX = "(-4.05,-38.95,-3.65,-38.15)"
USER_AGENT = "solucao-achar-cliente/0.1 (local lead queue; OpenStreetMap)"


class OverpassError(Exception):
    pass


def consultar(query: str) -> dict:
    ultimo_erro = "o mapa não respondeu"
    for url in ENDPOINTS:
        try:
            resposta = httpx.post(
                url,
                content=query.encode("utf-8"),
                headers={"User-Agent": USER_AGENT},
                timeout=50,
            )
            resposta.raise_for_status()
            return resposta.json()
        except (httpx.HTTPError, ValueError):
            ultimo_erro = "Os servidores do OpenStreetMap não responderam. Tente de novo em um minuto."
    raise OverpassError(ultimo_erro)


def escapar(nome: str) -> str:
    return nome.replace("\\", "\\\\").replace('"', '\\"')


def comercios_do_bairro(bairro: str) -> list[dict]:
    nome = escapar(bairro.strip())
    if not nome:
        raise OverpassError("Informe o bairro.")
    confirmacao = consultar(
        f"""
[out:json][timeout:60];
relation["name"="Fortaleza"]["boundary"="administrative"]["admin_level"="8"]{BBOX};
map_to_area -> .city;
relation["name"="{nome}"]["boundary"="administrative"](area.city);
out ids;
"""
    )
    if not confirmacao.get("elements"):
        raise OverpassError(f"Não encontrei o bairro {bairro.strip()} no mapa de Fortaleza.")
    dados = consultar(
        f"""
[out:json][timeout:90];
relation["name"="Fortaleza"]["boundary"="administrative"]["admin_level"="8"]{BBOX};
map_to_area -> .city;
relation["name"="{nome}"]["boundary"="administrative"](area.city);
map_to_area -> .bairro;
(
  nwr["shop"]["name"](area.bairro);
  nwr["amenity"~"restaurant|cafe|fast_food|bar|pharmacy|clinic|dentist|veterinary"]["name"](area.bairro);
);
out center tags;
"""
    )
    return dados.get("elements") or []
