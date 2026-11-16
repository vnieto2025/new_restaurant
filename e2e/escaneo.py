"""Recorrido del lector de código de barras: el administrador le pone el código a la gaseosa escaneándolo; en la venta
directa de la caja y en la mesa del mesero, pasar el lector agrega el producto sin tocar nada. Un código que no existe
avisa."""
from playwright.sync_api import sync_playwright, expect
from comun import APP, api, contexto, login, shot, abrir_navegador, terminar

CODIGO = "7702004003409"
admin = api("/login", {"usuario": "admin.esquina", "password": "demo1234"})["token"]
mesa = next(m for m in api("/mesa/list", {}, admin) if m["nombre"] == "Mesa 4")


def escanear(page, codigo, opciones=True):
    """ Como un lector USB: teclea muy rápido y termina con Enter """
    page.keyboard.type(codigo, delay=5)
    page.keyboard.press("Enter")
    page.wait_for_timeout(300)
    dialogo = page.get_by_role("dialog")
    # Si el producto tiene opciones se abre su ventana: se agrega sin elegir ninguna
    if opciones and dialogo.count():
        dialogo.get_by_role("button", name="Agregar").click()


with sync_playwright() as p:
    browser = abrir_navegador(p)

    # Administrador: el código se escanea en el formulario sin que el Enter lo guarde antes de tiempo
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/productos")
    page.get_by_role("row", name="Gaseosa 400 ml").get_by_role("button", name="Editar").click()
    dialogo = page.get_by_role("dialog")
    dialogo.get_by_label("Código de barras").click()
    escanear(page, CODIGO, opciones=False)
    expect(dialogo).to_be_visible()
    expect(dialogo.get_by_label("Código de barras")).to_have_value(CODIGO)
    shot(page, "e01-codigo")
    dialogo.get_by_role("button", name="Guardar").click()
    expect(page.get_by_text("Producto guardado.")).to_be_visible()
    page.context.close()

    # Caja: venta directa con el lector
    page = contexto(browser, 1280, 860)
    login(page, "caja.esquina")
    page.goto(f"{APP}/caja")
    if page.get_by_label("Base en efectivo").count():
        page.get_by_label("Base en efectivo").fill("100000")
        page.get_by_role("button", name="Abrir turno").click()
    page.get_by_role("tab", name="Venta directa").click()
    escanear(page, CODIGO)
    escanear(page, CODIGO)
    linea = page.locator(".cart .linea", has_text="Gaseosa 400 ml")
    expect(linea.locator(".cantidad")).to_have_text("2")
    expect(page.get_by_role("status").filter(has_text="Escaneado: Gaseosa 400 ml")).to_be_visible()
    escanear(page, "9999999999")
    expect(page.get_by_text("El código 9999999999 no está registrado")).to_be_visible()
    shot(page, "e02-caja")
    page.context.close()

    # Mesero: en la mesa, el código entra a la orden por enviar
    page = contexto(browser, 1180, 820)
    login(page, "mesero.salon")
    page.goto(f"{APP}/mesas/{mesa['id']}")
    expect(page.get_by_role("button", name="Enviar a cocina")).to_be_visible()
    escanear(page, CODIGO)
    expect(page.locator(".cart .linea", has_text="Gaseosa 400 ml")).to_be_visible()
    shot(page, "e03-mesa")
    browser.close()

terminar()
