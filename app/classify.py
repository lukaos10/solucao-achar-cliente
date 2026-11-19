from urllib.parse import quote, urlparse

REDES = (
    "instagram.com",
    "facebook.com",
    "fb.com",
    "fb.me",
    "linktr.ee",
    "wa.me",
    "api.whatsapp.com",
    "tiktok.com",
)

REDES_COMERCIAIS = (
    "drogasil",
    "droga raia",
    "pague menos",
    "domino",
    "ampm",
    "mcdonald",
    "mc donald",
    "burger king",
    "subway",
    "bobs",
    "habib",
    "spoleto",
    "giraffas",
    "cacau show",
    "boticario",
    "americanas",
    "casas bahia",
    "magazine luiza",
    "magalu",
    "carrefour",
    "assai",
    "atacadao",
    "nike",
    "adidas",
    "centauro",
    "smart fit",
    "outback",
    "starbucks",
    "pizza hut",
    "havan",
    "petz",
    "cobasi",
    "oticas carol",
    "chilli beans",
    "renner",
    "riachuelo",
)

TIPOS = {
    "restaurant": "restaurante",
    "cafe": "café",
    "fast_food": "lanche",
    "hairdresser": "salão",
    "beauty": "estética",
    "bakery": "padaria",
    "pharmacy": "farmácia",
    "car_repair": "oficina",
    "pastry": "doceria",
    "clothes": "roupa",
    "supermarket": "mercado",
    "bicycle": "bicicleta",
    "pet": "pet",
    "clinic": "clínica",
    "dentist": "dentista",
    "veterinary": "veterinário",
    "hardware": "construção",
    "furniture": "móveis",
    "optician": "ótica",
    "butcher": "açougue",
    "bar": "bar",
    "car": "veículos",
    "yes": "loja",
}


def sem_acento(texto: str) -> str:
    trocas = str.maketrans("áàâãäéèêëíìîïóòôõöúùûüçñ", "aaaaaeeeeiiiiooooouuuucn")
    return texto.lower().translate(trocas)


def classificar(website: str | None) -> tuple[str, str]:
    endereco = (website or "").strip()
    if not endereco:
        return "sem_site", ""
    host = (
        urlparse(endereco if "://" in endereco else f"https://{endereco}").hostname or ""
    ).lower().removeprefix("www.")
    if any(host == rede or host.endswith("." + rede) for rede in REDES):
        return "so_rede", endereco
    return "tem_site", endereco


def eh_rede(nome: str) -> bool:
    base = sem_acento(nome)
    return any(marca in base for marca in REDES_COMERCIAIS)


def tipo_legivel(tags: dict) -> str:
    bruto = tags.get("shop") or tags.get("amenity") or "loja"
    return TIPOS.get(bruto, bruto.replace("_", " "))


def telefone_de(tags: dict) -> str:
    return (
        tags.get("phone")
        or tags.get("contact:phone")
        or tags.get("contact:mobile")
        or tags.get("contact:whatsapp")
        or ""
    ).strip()


def whatsapp_de(telefone: str) -> str:
    digitos = "".join(caractere for caractere in telefone if caractere.isdigit())
    if digitos.startswith("55"):
        nacional = digitos[2:]
    else:
        nacional = digitos
    if len(nacional) == 11 and nacional[2] == "9":
        return f"https://wa.me/55{nacional}"
    return ""


def endereco_de(tags: dict) -> str:
    return " ".join(
        parte for parte in (tags.get("addr:street"), tags.get("addr:housenumber")) if parte
    )


def link_mapa(nome: str, endereco: str, bairro: str) -> str:
    consulta = quote(f"{nome} {endereco} {bairro} Fortaleza".strip())
    return f"https://www.google.com/maps/search/?api=1&query={consulta}"
