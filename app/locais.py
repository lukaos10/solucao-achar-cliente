import json
from pathlib import Path

PASTA = Path(__file__).parent / "dados"
_cidades = None


def cidades() -> list[dict]:
    global _cidades
    if _cidades is None:
        _cidades = json.loads((PASTA / "cidades.json").read_text(encoding="utf-8"))
    return _cidades


def estado_de(cidade: str, uf: str) -> str:
    for item in cidades():
        if item["n"] == cidade and item["u"] == uf:
            return item["e"]
    return ""


def bairros_fortaleza() -> list[str]:
    return json.loads((PASTA / "bairros-fortaleza.json").read_text(encoding="utf-8"))
