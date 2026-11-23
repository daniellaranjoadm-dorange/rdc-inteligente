# Publicar o RDC em rdc.dorange.com.br (Render)

O `render.yaml` cria tudo de uma vez: o servico web `rdc-inteligente`, o Postgres
`rdc-db` e um disco de 1 GB para arquivos enviados e exportacoes (`/var/data/media`).

Custo aproximado no Render: web *starter* (~US$ 7/mes) + Postgres *basic-256mb*
(~US$ 6/mes) + disco 1 GB (~US$ 0,25/mes).

## 1. Subir o codigo

Fazer commit e push destas mudancas na `main` do repositorio `rdc-inteligente`.

## 2. Criar o Blueprint no Render

1. Render > **New** > **Blueprint** > escolher o repositorio `rdc-inteligente`.
2. Conferir que ele vai criar `rdc-inteligente` (web) e `rdc-db` (Postgres) e aplicar.
3. Como `autoDeploy` esta desligado, os proximos deploys sao pelo botao **Manual Deploy**.

O `DJANGO_SECRET_KEY` e gerado pelo Render. O `DATABASE_URL` vem do `rdc-db`.
Se faltar algum dos dois, o app nao sobe (de proposito, para nao rodar inseguro
ou com SQLite, que seria apagado a cada deploy).

## 3. Apontar o dominio

No painel de DNS do dorange.com.br (o mesmo onde foi criado o `app.dorange.com.br`):

| Tipo  | Nome | Valor                          |
|-------|------|--------------------------------|
| CNAME | rdc  | rdc-inteligente.onrender.com   |

No Render, em **Settings > Custom Domains**, clicar em **Verify**. O certificado
HTTPS e emitido automaticamente.

## 4. Levar os dados do SQLite para o Postgres

Na maquina que tem o `db.sqlite3` atual, dentro de `rdc_inteligente`:

```powershell
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission -e admin.LogEntry -e sessions --indent 2 -o dados_rdc.json
```

Depois, usando a **External Database URL** do `rdc-db` (Render > rdc-db > Connect):

```powershell
$env:DATABASE_URL = "<External Database URL>"
python manage.py migrate --noinput
python manage.py loaddata dados_rdc.json
Remove-Item Env:DATABASE_URL
```

Apague o `dados_rdc.json` depois: ele tem os dados de funcionarios e usuarios.

## 5. Arquivos (opcional)

A pasta `media/` local tem importacoes antigas e RDCs exportados. Eles podem ser
gerados de novo, entao nao precisam ir. Se quiser manter o historico, envie a pasta
para `/var/data/media` pelo **Shell** ou por `scp` do Render.

## 6. Conferir

- Abrir https://rdc.dorange.com.br e fazer login.
- Gerar um RDC e exportar (usa o modelo em `assets/RDC - MODELO.xlsx`).
- No celular, abrir https://rdc.dorange.com.br/m/ e instalar o PWA.
