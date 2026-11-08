"""
Marca con v-escribe los botones y formularios que guardan datos, para ocultarlos en solo lectura (ADR-055).

    backend/env/Scripts/python.exe frontend/scripts/marcar_escritura.py            informe, sin cambiar nada
    backend/env/Scripts/python.exe frontend/scripts/marcar_escritura.py --aplicar  agrega las marcas

Un botón escribe si su acción llama a una ruta que no está en RUTAS_LECTURA del backend, o si abre un formulario
de crear o editar. Los que solo emiten un evento a su pantalla salen en el informe con "??" para revisarlos a mano.
"""
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ.parent / "backend"))
from Utils.acceso import RUTAS_LECTURA  # noqa: E402

os.chdir(RAIZ / "src")
ABRE = ("Crear", "Editar", "Agregar", "Nuevo", "Nueva", "Importar", "Configurar", "Corregir", "Registrar", "Duplicar", "Copiar a")
# Llaman a una ruta de escritura pero sirven para consultar: en solo lectura fallan con su aviso, sin esconderse
CONSULTA = {("CajaView.vue", "· Pidió la cuenta")}
APLICAR = "--aplicar" in sys.argv
RUTA = re.compile(r"['`\"](/[a-z_]+/[a-z_/]*[a-z_])['`\"]")


def funciones(script):
    """ nombre -> cuerpo, partiendo el script en cada declaración de función de primer nivel """
    marcas = [(m.start(), m.group(1) or m.group(2)) for m in re.finditer(
        r"^(?:async\s+)?function\s+(\w+)|^const\s+(\w+)\s*=\s*(?:async\s*)?\(", script, re.M)]
    cuerpos = {}
    for i, (inicio, nombre) in enumerate(marcas):
        fin = marcas[i + 1][0] if i + 1 < len(marcas) else len(script)
        cuerpos[nombre] = script[inicio:fin]
    return cuerpos


def escribe_codigo(texto, cuerpos, vistos=None):
    vistos = vistos or set()
    if any(r not in RUTAS_LECTURA for r in RUTA.findall(texto)):
        return True
    for nombre in re.findall(r"\b(\w+)\s*\(", texto) + re.findall(r"^\s*(\w+)\s*$", texto):
        if nombre in cuerpos and nombre not in vistos:
            vistos.add(nombre)
            if escribe_codigo(cuerpos[nombre], cuerpos, vistos):
                return True
    return False


informe = []
for f in sorted(list(Path("views").rglob("*.vue")) + list(Path("components").glob("*.vue"))):
    if f.parent.name in ("plataforma", "publico"):
        continue
    s = f.read_text(encoding="utf-8")
    script =s[s.find("<script"):s.find("</script>")]
    cuerpos = funciones(script)
    ti = s.find("<template>")
    plantilla = s[ti:]
    cambios = []

    for m in re.finditer(r"<(button|form)\b([^>]*)>", plantilla):
        etiqueta, attrs = m.group(1), m.group(2)
        if "v-escribe" in attrs or "data-consulta" in attrs:
            continue
        if etiqueta == "form":
            h = re.search(r'@submit(?:\.prevent)?="([^"]*)"', attrs)
            if h and escribe_codigo(h.group(1), cuerpos):
                cambios.append((m.start(), "form", h.group(1)))
            continue
        if re.search(r'type="submit"', attrs):
            continue
        h = re.search(r'@click(?:\.\w+)*="([^"]*)"', attrs)
        cierre = plantilla.find("</button>", m.end())
        texto = " ".join(re.sub(r"<[^>]+>|\{\{.*?\}\}", " ", plantilla[m.end():cierre], flags=re.S).split())
        motivo = None
        if any(f.name == archivo and texto.startswith(prefijo) for archivo, prefijo in CONSULTA):
            continue
        if h and escribe_codigo(h.group(1), cuerpos):
            motivo = "api"
        elif texto.startswith(ABRE):
            motivo = "abre"
        elif h and "emit(" in h.group(1):
            motivo = "emite"
        if motivo and motivo != "emite":
            cambios.append((m.start(), "button", f"{motivo}: {texto[:40]}"))
        elif motivo == "emite":
            informe.append(f"   ?? {f}: emite {h.group(1)[:40]} [{texto[:30]}]")

    for pos, tipo, detalle in cambios:
        informe.append(f"{f}: {tipo} {detalle}")
    if APLICAR and cambios:
        for pos, tipo, _ in sorted(cambios, reverse=True):
            corte = ti + pos + len(tipo) + 1
            s = s[:corte] + " v-escribe" + s[corte:]
        f.write_text(s, encoding="utf-8", newline="")

print("\n".join(informe))
print(len([l for l in informe if not l.startswith("   ??")]), "marcas;", len([l for l in informe if l.startswith("   ??")]), "por revisar")
