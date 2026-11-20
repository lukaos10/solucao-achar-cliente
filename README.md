# Fila sem site

Painel local para achar comércios sem site próprio e guardar o telefone publicado no OpenStreetMap. A cidade e o bairro abrem uma lista em ordem alfabética.

A busca usa o [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API). Se o mapa não traz um site, a fila ainda confere se o nome do comércio abre um endereço .com.br ou .com e tira da fila quem tem site próprio. O botão Mapa abre uma pesquisa no Google com o nome e o endereço que já estão no OpenStreetMap. O telefone do Google não entra no banco.

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abra http://127.0.0.1:8000, escolha a cidade, o nicho e, se quiser, o bairro. Sem bairro, a busca usa a cidade toda. Clique em Buscar no mapa. A primeira consulta de uma cidade inteira pode levar mais de um minuto.

A fila fica em `data/leads.db`, só na sua máquina. Os dados são © OpenStreetMap contributors.
