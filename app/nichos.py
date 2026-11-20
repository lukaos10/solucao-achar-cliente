import re

from app.classify import sem_acento

NICHOS = (
    {
        "id": "acougue",
        "nome": "Açougue",
        "consulta": 'nwr["shop"="butcher"]["name"](area.bairro);',
    },
    {
        "id": "academia",
        "nome": "Academia",
        "consulta": 'nwr["leisure"="fitness_centre"]["name"](area.bairro);',
    },
    {
        "id": "advocacia",
        "nome": "Advocacia",
        "consulta": 'nwr["office"="lawyer"]["name"](area.bairro);',
    },
    {
        "id": "barbearia",
        "nome": "Barbearia",
        "consulta": 'nwr["shop"="hairdresser"]["name"~"barbearia|barbeiro|barber",i](area.bairro);',
    },
    {
        "id": "bar",
        "nome": "Bar",
        "consulta": 'nwr["amenity"="bar"]["name"](area.bairro);',
    },
    {
        "id": "cafeteria",
        "nome": "Cafeteria",
        "consulta": 'nwr["amenity"="cafe"]["name"](area.bairro);',
    },
    {
        "id": "clinica",
        "nome": "Clínica",
        "consulta": """
nwr["amenity"="clinic"]["name"](area.bairro);
nwr["healthcare"="clinic"]["name"](area.bairro);
""",
    },
    {
        "id": "construcao",
        "nome": "Construção",
        "consulta": """
nwr["shop"="hardware"]["name"](area.bairro);
nwr["shop"="doityourself"]["name"](area.bairro);
""",
    },
    {
        "id": "contabilidade",
        "nome": "Contabilidade",
        "consulta": 'nwr["office"="accountant"]["name"](area.bairro);',
    },
    {
        "id": "dentista",
        "nome": "Dentista",
        "consulta": """
nwr["amenity"="dentist"]["name"](area.bairro);
nwr["healthcare"="dentist"]["name"](area.bairro);
""",
    },
    {
        "id": "doceria",
        "nome": "Doceria",
        "consulta": """
nwr["shop"="pastry"]["name"](area.bairro);
nwr["shop"="confectionery"]["name"](area.bairro);
""",
    },
    {
        "id": "estetica",
        "nome": "Estética",
        "consulta": """
nwr["shop"="beauty"]["name"](area.bairro);
nwr["shop"="cosmetics"]["name"](area.bairro);
""",
    },
    {
        "id": "farmacia",
        "nome": "Farmácia",
        "consulta": 'nwr["amenity"="pharmacy"]["name"](area.bairro);',
    },
    {
        "id": "hamburgueria",
        "nome": "Hamburgueria",
        "consulta": """
nwr["amenity"="fast_food"]["cuisine"~"burger|hamburguer",i]["name"](area.bairro);
nwr["amenity"]["name"~"burger|burguer|hamburguer|hambúrguer|smash",i](area.bairro);
nwr["shop"]["name"~"burger|burguer|hamburguer|hambúrguer|smash",i](area.bairro);
""",
    },
    {
        "id": "imobiliaria",
        "nome": "Imobiliária",
        "consulta": 'nwr["office"="estate_agent"]["name"](area.bairro);',
    },
    {
        "id": "lanche",
        "nome": "Lanche",
        "consulta": 'nwr["amenity"="fast_food"]["name"](area.bairro);',
    },
    {
        "id": "mercado",
        "nome": "Mercado",
        "consulta": 'nwr["shop"="supermarket"]["name"](area.bairro);',
    },
    {
        "id": "moveis",
        "nome": "Móveis",
        "consulta": 'nwr["shop"="furniture"]["name"](area.bairro);',
    },
    {
        "id": "oficina",
        "nome": "Oficina",
        "consulta": 'nwr["shop"="car_repair"]["name"](area.bairro);',
    },
    {
        "id": "otica",
        "nome": "Ótica",
        "consulta": 'nwr["shop"="optician"]["name"](area.bairro);',
    },
    {
        "id": "padaria",
        "nome": "Padaria",
        "consulta": 'nwr["shop"="bakery"]["name"](area.bairro);',
    },
    {
        "id": "pet",
        "nome": "Pet shop",
        "consulta": 'nwr["shop"="pet"]["name"](area.bairro);',
    },
    {
        "id": "restaurante",
        "nome": "Restaurante",
        "consulta": 'nwr["amenity"="restaurant"]["name"](area.bairro);',
    },
    {
        "id": "roupa",
        "nome": "Roupa",
        "consulta": 'nwr["shop"="clothes"]["name"](area.bairro);',
    },
    {
        "id": "salao",
        "nome": "Salão",
        "consulta": 'nwr["shop"="hairdresser"]["name"](area.bairro);',
    },
    {
        "id": "veterinario",
        "nome": "Veterinário",
        "consulta": 'nwr["amenity"="veterinary"]["name"](area.bairro);',
    },
)

_POR_ID = {item["id"]: item for item in NICHOS}


def nomes() -> list[dict]:
    return [{"id": item["id"], "nome": item["nome"]} for item in NICHOS]


def consulta_de(nicho_id: str) -> str | None:
    item = _POR_ID.get(nicho_id)
    if item is None:
        return None
    return item["consulta"]


def nome_de(nicho_id: str) -> str:
    item = _POR_ID.get(nicho_id)
    return item["nome"] if item else ""


def nicho_de(tags: dict) -> str:
    nome = sem_acento(tags.get("name") or "")
    shop = tags.get("shop") or ""
    amenity = tags.get("amenity") or ""
    healthcare = tags.get("healthcare") or ""
    office = tags.get("office") or ""
    leisure = tags.get("leisure") or ""
    cuisine = sem_acento(tags.get("cuisine") or "")
    if amenity == "dentist" or healthcare == "dentist":
        return "Dentista"
    if amenity == "clinic" or healthcare == "clinic":
        return "Clínica"
    if amenity == "veterinary":
        return "Veterinário"
    if amenity == "pharmacy":
        return "Farmácia"
    if amenity == "restaurant":
        return "Restaurante"
    if amenity == "cafe":
        return "Cafeteria"
    if amenity == "bar":
        return "Bar"
    if amenity == "fast_food" and (
        re.search(r"burger|burguer|hamburguer", nome) or "burger" in cuisine
    ):
        return "Hamburgueria"
    if amenity == "fast_food":
        return "Lanche"
    if shop == "hairdresser" and re.search(r"barbearia|barbeiro|barber", nome):
        return "Barbearia"
    if shop == "hairdresser":
        return "Salão"
    if shop in {"beauty", "cosmetics"}:
        return "Estética"
    if shop == "bakery":
        return "Padaria"
    if shop in {"pastry", "confectionery"}:
        return "Doceria"
    if shop == "butcher":
        return "Açougue"
    if shop in {"hardware", "doityourself"}:
        return "Construção"
    if shop == "supermarket":
        return "Mercado"
    if shop == "furniture":
        return "Móveis"
    if shop == "car_repair":
        return "Oficina"
    if shop == "optician":
        return "Ótica"
    if shop == "pet":
        return "Pet shop"
    if shop == "clothes":
        return "Roupa"
    if office == "lawyer":
        return "Advocacia"
    if office == "accountant":
        return "Contabilidade"
    if office == "estate_agent":
        return "Imobiliária"
    if leisure == "fitness_centre":
        return "Academia"
    return ""
