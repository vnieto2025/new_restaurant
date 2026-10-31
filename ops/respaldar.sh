#!/bin/sh
# Respaldos de la base de datos (doc 40, sección 6). Corre dentro del servicio "respaldos" de docker-compose.
#   respaldar.sh          se queda corriendo y respalda una vez al día a RESPALDO_HORA
#   respaldar.sh --ahora  hace un respaldo y termina
# Un respaldo solo queda con su nombre final si pg_restore puede leerlo: uno dañado no reemplaza a los buenos.
set -u

DESTINO=/respaldos
HORA="${RESPALDO_HORA:-04}"
DIAS="${RESPALDO_DIAS:-30}"

respaldar() {
    nombre="$DESTINO/${PGDATABASE}_$(date +%Y%m%d_%H%M%S).dump"
    if ! pg_dump -Fc -f "$nombre.parcial"; then
        echo "ERROR: falló el respaldo de $PGDATABASE" >&2
        rm -f "$nombre.parcial"
        return 1
    fi
    if ! pg_restore --list "$nombre.parcial" > /dev/null; then
        echo "ERROR: el respaldo quedó ilegible" >&2
        rm -f "$nombre.parcial"
        return 1
    fi
    mv "$nombre.parcial" "$nombre"
    find "$DESTINO" -name '*.dump' -mtime +"$DIAS" -delete
    echo "Respaldo listo: $nombre ($(du -h "$nombre" | cut -f1))"
}

if [ "${1:-}" = "--ahora" ]; then
    respaldar
    exit $?
fi

echo "Respaldos diarios a las $HORA:00, conservando $DIAS días, en $DESTINO"
ultimo=""
while true; do
    hoy=$(date +%Y%m%d)
    if [ "$(date +%H)" = "$HORA" ] && [ "$ultimo" != "$hoy" ]; then
        # Si falla se reintenta en el siguiente ciclo, mientras siga siendo la hora del respaldo
        respaldar && ultimo="$hoy"
    fi
    sleep 300
done
