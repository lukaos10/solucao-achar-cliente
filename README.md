# Fila sem site

Painel local para achar comércios de Fortaleza que não têm site próprio e guardar o telefone publicado no OpenStreetMap.

A busca usa o [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API). O botão Mapa abre uma pesquisa no Google com o nome e o endereço que já estão no OpenStreetMap. O telefone do Google não entra no banco.

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abra http://127.0.0.1:8000, escolha o bairro e clique em Buscar no mapa. A primeira consulta de um bairro grande pode levar cerca de um minuto.

A fila fica em `data/leads.db`, só na sua máquina. Os dados são © OpenStreetMap contributors.
