"""
Apoyo común de los recorridos en el navegador: llamadas a la API, contextos de navegador, inicio de sesión y capturas.

Cada recorrido importa de aquí y recibe opcionalmente la carpeta de capturas como primer argumento.
Variables de entorno:
  E2E_APP        dirección del frontend (por defecto http://127.0.0.1:5173)
  E2E_API        dirección del backend (por defecto http://127.0.0.1:8000)
  E2E_NAVEGADOR  canal de Playwright: msedge (por defecto), chrome o chromium (el que instala Playwright)
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

APP = os.getenv("E2E_APP", "http://127.0.0.1:5173")
API = os.getenv("E2E_API", "http://127.0.0.1:8000")
NAVEGADOR = os.getenv("E2E_NAVEGADOR", "msedge")
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "capturas" / Path(sys.argv[0]).stem
OUT.mkdir(parents=True, exist_ok=True)
# Errores de la consola del navegador: cada recorrido los imprime al final y deben ser "ninguno"
errores = []


def api(path, body=None, token=None):
    headers = {"accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(API + path, json.dumps(body or {}).encode(), headers)
    return json.loads(urllib.request.urlopen(req).read())["data"]


def abrir_navegador(p):
    if NAVEGADOR == "chromium":
        return p.chromium.launch()
    return p.chromium.launch(channel=NAVEGADOR)


def contexto(browser, width, height, mobile=False):
    ctx = browser.new_context(viewport={"width": width, "height": height}, is_mobile=mobile, has_touch=mobile)
    # El botón flotante de Vue DevTools (solo en desarrollo) tapa la barra inferior del celular
    ctx.add_init_script("""document.addEventListener('DOMContentLoaded', () => {
      const style = document.createElement('style');
      style.textContent = '#__vue-devtools-container__{display:none!important}';
      document.head.appendChild(style);
    })""")
    # La impresión se simula: window.__impreso cuenta cuántas veces se mandó a imprimir
    ctx.add_init_script("window.print = () => { window.__impreso = (window.__impreso || 0) + 1 }")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errores.append(f"{m.text}"))
    page.on("pageerror", lambda e: errores.append(f"pageerror: {e}"))
    return page


def login(page, usuario, password="demo1234"):
    page.goto(f"{APP}/login")
    page.fill("#usuario", usuario)
    page.fill("#password", password)
    page.click("button[type=submit]")
    page.wait_for_url(lambda url: "/login" not in url)


def shot(page, name):
    """ Captura de pantalla; de paso revisa que la página no se desborde a lo ancho """
    page.wait_for_timeout(400)
    ancho = [page.evaluate("document.documentElement.scrollWidth"), page.viewport_size["width"]]
    if ancho[0] > ancho[1]:
        errores.append(f"{name}: desborde horizontal {ancho[0]}px en pantalla de {ancho[1]}px")
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)


def elegir_opciones(page, opciones):
    dialogo = page.get_by_role("dialog")
    for opcion in opciones:
        dialogo.get_by_role("button", name=opcion).click()
    dialogo.get_by_role("button", name="Agregar").click()


def terminar(esperados=()):
    """ Resultado del recorrido: sale con error si la consola del navegador registró alguno.
        esperados: textos de errores que el recorrido provoca a propósito (un código rechazado responde 409
        y el navegador lo anota en la consola); se informan aparte y no hacen fallar. """
    provocados = [e for e in errores if any(texto in e for texto in esperados)]
    reales = [e for e in errores if e not in provocados]
    if provocados:
        print("rechazos provocados a propósito:", len(provocados))
    print("errores:", reales or "ninguno")
    if reales:
        sys.exit(1)
