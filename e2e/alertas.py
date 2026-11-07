"""Recorrido de alertas y resumen del día: el dueño ve en Hoy lo que necesita atención, silencia una alerta,
ajusta un umbral; luego revisa el resumen de la jornada, configura su celular y, al cerrar la jornada,
el resumen queda en Avisos por enviar."""
import uuid
from playwright.sync_api import sync_playwright, expect
from comun import APP, api, contexto, login, shot, abrir_navegador, terminar

admin = api("/login", {"usuario": "admin.esquina", "password": "demo1234"})["token"]
caja = api("/login", {"usuario": "caja.esquina", "password": "demo1234"})["token"]
externa = next(m for m in api("/mesa/list", {"incluir_externa": True}, caja) if m["nombre"] == "Para llevar")
productos = {p["nombre"]: p["id"] for p in api("/producto/list", {}, admin)}


# Una venta cobrada con dos gaseosas que la cajera canceló antes de cobrar
api("/caja/turno/abrir", {"fondo_inicial": 100000}, caja)
efectivo = next(m["id"] for m in api("/caja/estado", {}, caja)["medios"] if m["nombre"] == "Efectivo")
orden = api("/orden/create", {"mesa_id": externa["id"], "clave_idempotencia": uuid.uuid4().hex, "cliente_nombre": "Recorrido", "items": [
    {"producto_id": productos["Salchipapa"], "cantidad": 2},
    {"producto_id": productos["Gaseosa 400 ml"], "cantidad": 1},
    {"producto_id": productos["Gaseosa 400 ml"], "cantidad": 1, "nota": "Sin hielo"}]}, caja)
for item in orden["items"]:
    if item["nombre"] == "Gaseosa 400 ml":
        api("/orden/cancelar_item", {"orden_item_id": item["id"], "motivo": "El cliente cambió de idea"}, caja)
cuenta = api("/cuenta/abrir", {"sesion_mesa_id": api("/cuenta/pendientes", {}, caja)[0]["sesion_mesa_id"]}, caja)
api("/cuenta/pagar", {"cuenta_id": cuenta["id"], "clave_idempotencia": uuid.uuid4().hex,
                      "pagos": [{"medio_pago_id": efectivo, "monto": cuenta["saldo"]}]}, caja)

with sync_playwright() as p:
    browser = abrir_navegador(p)
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin")

    alertas = page.locator("section.alertas")
    expect(alertas).to_contain_text("Stock bajo o negativo")
    expect(alertas).to_contain_text("Tocineta")

    # Umbral de cancelaciones en 2: aparece la cajera
    alertas.get_by_role("button", name="Configurar alertas").click()
    dialogo = page.get_by_role("dialog")
    dialogo.get_by_label("Umbral de Muchas cancelaciones de una persona en ítems en la jornada").fill("2")
    shot(page, "l01-configurar")
    dialogo.get_by_role("button", name="Guardar").click()
    expect(page.get_by_text("Alertas guardadas.")).to_be_visible()
    expect(alertas).to_contain_text("1 persona canceló 2 o más ítems hoy")
    alertas.scroll_into_view_if_needed()
    shot(page, "l02-alertas")

    # Silenciar el inventario por hoy
    alertas.get_by_role("button", name="Silenciar hoy Stock bajo o negativo").click()
    expect(alertas.get_by_role("button", name="1 alerta silenciada hoy")).to_be_visible()
    expect(alertas.locator("li.alerta", has_text="Tocineta")).to_have_count(0)

    # Resumen del día
    page.get_by_role("link", name="Resumen del día").click()
    hoja = page.get_by_role("region", name="Resumen")
    expect(hoja).to_contain_text("en curso")
    expect(hoja).to_contain_text("Salchipapa")
    expect(hoja).to_contain_text("Cancelaciones (2)")
    shot(page, "l03-resumen")
    page.get_by_label("Dejar listo el resumen al cerrar cada jornada").check()
    page.get_by_label("Celular del dueño").fill("300 555 1234")
    page.get_by_label("Nombre").fill("Marta")
    page.get_by_role("button", name="Guardar").click()
    expect(page.get_by_role("link", name="Enviar por WhatsApp a 300 555 1234")).to_be_visible()
    page.get_by_text("Ver el texto que se envía").click()
    expect(page.locator("pre")).to_contain_text("Ventas: $ 30.000")
    shot(page, "l04-resumen-configurado")

    # Cierre de jornada: el resumen queda en Avisos por enviar
    turno = api("/caja/estado", {}, caja)["turno"]
    api("/caja/turno/cerrar", {"efectivo_contado": turno["resumen"]["efectivo_esperado"]}, caja)
    api("/caja/jornada/cerrar", {}, admin)
    page.goto(f"{APP}/admin/avisos")
    page.get_by_role("tab", name="Historial").click()
    fila = page.get_by_role("row", name="Resumen del día")
    expect(fila).to_contain_text("Por enviar")
    expect(fila).to_contain_text("Marta")
    shot(page, "l05-aviso-resumen")
    browser.close()

terminar()
