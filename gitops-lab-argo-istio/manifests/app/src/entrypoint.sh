#!/bin/sh
set -e

echo "[entrypoint] Oficina de Lanternagem e Pintura do Rasta - inicializando"

if [ -z "$DATABASE_URL" ]; then
  : "${DB_HOST:?DB_HOST obrigatório}"
  : "${DB_USER:?DB_USER obrigatório}"
  : "${DB_PASSWORD:?DB_PASSWORD obrigatório}"
  : "${DB_NAME:?DB_NAME obrigatório}"
  : "${DB_PORT:=5432}"
  export DATABASE_URL="postgresql+psycopg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
fi

echo "[entrypoint] Aguardando banco de dados..."
until python -c "
import psycopg, os
from urllib.parse import urlparse
url = os.environ['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://')
p = urlparse(url)
conn = psycopg.connect(host=p.hostname, port=p.port, user=p.username, password=p.password, dbname=p.path[1:], connect_timeout=3)
conn.close()
" 2>/dev/null; do
  sleep 2
done
echo "[entrypoint] Banco disponível"

export FLASK_APP=wsgi:app
python -m flask db upgrade || true

PORT="${PORT:-5000}"
WORKERS="${GUNICORN_WORKERS:-2}"
THREADS="${GUNICORN_THREADS:-4}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"

echo "Iniciando Gunicorn com ddtrace-run na porta ${PORT}..."
exec ddtrace-run gunicorn -w "${WORKERS}" -k gthread --threads "${THREADS}" -b "0.0.0.0:${PORT}" --timeout "${TIMEOUT}" --access-logfile - --error-logfile - wsgi:app
