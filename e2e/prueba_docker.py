"""Prueba del paquete de Docker ya levantado (la corre GitHub Actions): salud, lo que no debe quedar público, el límite
de tamaño de nginx y que un respaldo se pueda restaurar. Los flujos de la aplicación los prueba el recorrido fase1."""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

BASE = os.getenv("E2E_APP", "http://localhost")


def pedir(ruta, cuerpo=None, token=None):
    cabeceras = {"accept": "application/json", "Content-Type": "application/json"}
    if token:
        cabeceras["Authorization"] = f"Bearer {token}"
    datos = None if cuerpo is None else (cuerpo if isinstance(cuerpo, bytes) else json.dumps(cuerpo).encode())
    try:
        with urllib.request.urlopen(urllib.request.Request(BASE + ruta, datos, cabeceras)) as respuesta:
            return respuesta.status, respuesta.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def comprobar(nombre, condicion, detalle=""):
    print(("ok   " if condicion else "FALLA"), nombre, detalle)
    if not condicion:
        sys.exit(1)


def correr(*comando):
    subprocess.run(comando, check=True)


comprobar("salud", pedir("/api/salud")[0] == 200)
comprobar("la carta carga", b"<div id=\"app\"" in pedir("/")[1])
comprobar("las rutas de Vue no dan 404", pedir("/mesas")[0] == 200)
comprobar("la documentación de la API no es pública", pedir("/api/docs")[0] == 404)
comprobar("el backend no publica su puerto", subprocess.run(
    ["curl", "-s", "-o", "/dev/null", "--max-time", "3", "http://localhost:8000/salud"]).returncode != 0)

# Un Excel de 2 MB en base64 pesa 2,7 MB: nginx no debe cortarlo antes de llegar a la aplicación
estado, _ = pedir("/api/producto/importar/revisar", b'{"archivo":"' + b"A" * (2_800_000) + b'"}')
comprobar("nginx deja pasar un archivo de 2 MB", estado != 413, f"estado {estado}")

sesion = json.loads(pedir("/api/login", {"usuario": "admin.esquina", "password": "demo1234"})[1])["data"]
comprobar("ingreso", bool(sesion["token"]))
token = sesion["token"]


def total_productos():
    return len(json.loads(pedir("/api/producto/list", {"todos": True}, token)[1])["data"])


# Respaldo, daño y restauración: un respaldo que nunca se ha probado no existe (doc 40, sección 6)
antes = total_productos()
correr("docker", "compose", "exec", "-T", "respaldos", "/ops/respaldar.sh", "--ahora")
archivos = sorted(f for f in os.listdir("respaldos") if f.endswith(".dump"))
comprobar("se creó el respaldo", bool(archivos), str(archivos))

categoria = json.loads(pedir("/api/categoria/list", {}, token)[1])["data"][0]["id"]
estado, _ = pedir("/api/producto/create", {"nombre": "Creado después del respaldo", "categoria_id": categoria, "precio": 1000}, token)
comprobar("cambio posterior al respaldo", estado == 201 and total_productos() == antes + 1)

correr("sh", "ops/restaurar.sh", "--si", f"respaldos/{archivos[-1]}")
sesion = json.loads(pedir("/api/login", {"usuario": "admin.esquina", "password": "demo1234"})[1])["data"]
token = sesion["token"]
comprobar("volvió al estado del respaldo", total_productos() == antes)

# El aislamiento entre empresas sobrevive a la restauración
salida = subprocess.run(
    ["docker", "compose", "exec", "-T", "db", "sh", "-c",
     'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select count(*) from pg_class where relrowsecurity and relname = \'producto\'"'],
    capture_output=True, text=True, check=True).stdout.strip()
comprobar("RLS sigue activo", salida == "1", salida)
print("Paquete de Docker verificado.")
