#!/bin/sh
# Restaura un respaldo. BORRA los datos actuales de la base y los reemplaza por los del archivo.
# Se corre desde la carpeta del proyecto, en el servidor:
#   sh ops/restaurar.sh respaldos/restaurant_20261030_040000.dump
#   sh ops/restaurar.sh --si respaldos/...    (sin preguntar)
set -eu

if [ "${1:-}" = "--si" ]; then
    confirmado=1
    shift
else
    confirmado=0
fi
archivo="${1:-}"
if [ -z "$archivo" ] || [ ! -f "$archivo" ]; then
    echo "Uso: sh ops/restaurar.sh <archivo.dump>" >&2
    exit 1
fi
if [ "$confirmado" != "1" ]; then
    printf 'Se BORRAN los datos actuales y se reemplazan por %s. Escribe RESTAURAR para seguir: ' "$archivo"
    read -r respuesta
    [ "$respuesta" = "RESTAURAR" ] || { echo "Cancelado."; exit 1; }
fi

docker compose up -d --wait db
docker compose stop backend respaldos
# Sin dueños ni permisos: el archivo sirve también en un servidor nuevo. seed.py los vuelve a poner con el aislamiento (RLS)
docker compose exec -T db sh -c 'pg_restore --clean --if-exists --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < "$archivo"
docker compose run --rm backend python seed.py
docker compose up -d --wait
echo "Restauración lista. Revisa en la aplicación que los datos sean los esperados."
