"""Recorrido de cupones: administración crea un cupón, caja aplica uno personal con cliente identificado y emite el de la
próxima visita, el cliente aplica un código desde su celular y administración ve los resultados."""
import uuid
from playwright.sync_api import sync_playwright, expect
from comun import APP, api, contexto, login, shot, abrir_navegador, terminar


mesero = api("/login", {"usuario": "mesero.terraza", "password": "demo1234"})["token"]
caja = api("/login", {"usuario": "caja.esquina", "password": "demo1234"})["token"]
admin = api("/login", {"usuario": "admin.esquina", "password": "demo1234"})["token"]
if not api("/caja/estado", {}, caja)["turno"]:
    api("/caja/turno/abrir", {"fondo_inicial": 100000}, caja)
productos = {p["nombre"]: p["id"] for p in api("/producto/list", {"todos": True}, admin)}
mesas = {m["nombre"]: m for m in api("/mesa/list", {"incluir_externa": True}, caja)}
api("/cliente/create", {"nombre": "Camila Rojas", "telefono": "3157778899", "acepta_datos": True, "acepta_comercial": True}, caja)


def ordenar(mesa, items):
    api("/orden/create", {"mesa_id": mesas[mesa]["id"], "clave_idempotencia": uuid.uuid4().hex, "items": [
        {"producto_id": productos[n], "cantidad": c} for n, c in items]}, mesero)


ordenar("Terraza 1", [("Limonada natural", 2), ("Papas a la francesa", 2)])
ordenar("Terraza 2", [("Limonada natural", 1), ("Papas a la francesa", 1)])
token_qr = next(q for q in api("/qr/list", {}, admin) if q["mesa"] == "Terraza 2")["url"].rsplit("/", 1)[1]

with sync_playwright() as p:
    browser = abrir_navegador(p)

    # Administración: nuevo cupón con reglas
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/cupones")
    expect(page.locator("tbody")).to_contain_text("BIENVENIDO")
    page.get_by_role("button", name="Nuevo cupón").click()
    dialogo = page.get_by_role("dialog")
    dialogo.get_by_role("button", name="Valor fijo").click()
    page.fill("#cp-valor", "2000")
    page.fill("#cp-nombre", "Terraza de la tarde")
    page.fill("#cp-codigo", "tarde2000")
    page.fill("#cp-desc", "$2.000 de descuento en la terraza")
    dialogo.locator("summary").click()
    dialogo.get_by_role("checkbox", name="Mesa").check()
    shot(page, "c01-nuevo-cupon")
    dialogo.get_by_role("button", name="Guardar").click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    expect(page.locator("tbody")).to_contain_text("TARDE2000")
    shot(page, "c02-lista-cupones")
    page.get_by_role("tab", name="Próxima visita").click()
    expect(page.locator("tbody")).to_contain_text("Vuelve pronto")
    shot(page, "c03-plantillas")
    page.context.close()

    # Caja: BIENVENIDO tiene límite por cliente, así que pide identificarlo; luego emite el cupón de la próxima visita
    page = contexto(browser, 1366, 900)
    login(page, "caja.esquina")
    page.goto(f"{APP}/caja")
    page.get_by_role("button", name="Terraza 1").first.click()
    page.fill("#cupon-codigo", "NOEXISTE")
    page.get_by_role("button", name="Aplicar").click()
    expect(page.locator("#cupon-error")).to_contain_text("no existe")
    page.fill("#cupon-codigo", "bienvenido")
    page.get_by_role("button", name="Aplicar").click()
    expect(page.locator("#cupon-error")).to_contain_text("identifica al cliente")
    shot(page, "c04-cupon-rechazado")
    page.get_by_role("button", name="Identificar cliente").click()
    page.get_by_label("Buscar cliente").fill("Camila")
    page.locator(".buscar-cliente").get_by_role("button", name="Buscar").click()
    page.get_by_role("button", name="Camila Rojas").click()
    expect(page.locator(".cupon-cliente")).to_contain_text("Camila Rojas")
    page.get_by_role("button", name="Aplicar").click()
    expect(page.locator(".aplicados")).to_contain_text("BIENVENIDO")
    expect(page.locator(".totales")).to_contain_text("Cupón")
    shot(page, "c05-cupon-aplicado")
    page.locator(".medios").get_by_role("button", name="Efectivo").click()
    page.get_by_role("button", name="Cobrar").click()
    expect(page.locator(".obsequio")).to_be_visible(timeout=10000)
    shot(page, "c06-cupon-proxima-visita")
    page.context.close()

    # Cliente en la mesa: código desde el celular
    page = contexto(browser, 390, 844, mobile=True)
    page.goto(f"{APP}/pagar?token={token_qr}")
    page.fill("#cupon", "DOMIGRATIS")
    page.get_by_role("button", name="Aplicar").click()
    expect(page.locator("#cupon-error")).to_contain_text("solo en domicilio")
    page.fill("#cupon", "tarde2000")
    page.get_by_role("button", name="Aplicar").click()
    expect(page.locator(".totales")).to_contain_text("Cupón TARDE2000")
    shot(page, "c07-cupon-celular")
    page.context.close()

    # Administración: resultados y ficha del cliente
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/cupones")
    page.get_by_role("tab", name="Resultados").click()
    expect(page.locator(".resumen")).to_contain_text("Cupones usados")
    shot(page, "c08-resultados")
    page.goto(f"{APP}/admin/clientes")
    page.locator("tr", has_text="Camila Rojas").get_by_role("button", name="Ver ficha").click()
    expect(page.get_by_role("dialog")).to_contain_text("Usó BIENVENIDO")
    shot(page, "c09-ficha-cliente")
    page.context.close()

    browser.close()

# Códigos rechazados a propósito: el que no existe (404) y los que no cumplen una regla (409)
terminar(esperados=("status of 404", "status of 409"))
