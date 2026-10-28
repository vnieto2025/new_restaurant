"""Recorrido de pagos en línea: el cliente paga la mesa desde el QR con propina en la pasarela simulada, un pedido
para llevar recibe el enlace de pago desde caja, un rechazo y la conciliación en administración."""
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
api("/orden/create", {"mesa_id": mesas["Terraza 2"]["id"], "clave_idempotencia": uuid.uuid4().hex, "items": [
    {"producto_id": productos["Limonada natural"], "cantidad": 2}, {"producto_id": productos["Papas a la francesa"], "cantidad": 1}]},
    mesero)
token_qr = next(q for q in api("/qr/list", {}, admin) if q["mesa"] == "Terraza 2")["url"].rsplit("/", 1)[1]

with sync_playwright() as p:
    browser = abrir_navegador(p)

    # Cliente en la mesa: desde la carta del QR paga con propina sugerida
    page = contexto(browser, 390, 844, mobile=True)
    page.goto(f"{APP}/q/{token_qr}")
    page.get_by_role("link", name="Pagar la cuenta").click()
    expect(page.locator(".totales")).to_contain_text("Por pagar")
    page.get_by_role("button", name="10 %").click()
    shot(page, "p01-pagar-mesa")
    page.get_by_role("button", name="Pagar").click()
    page.wait_for_url(lambda url: "/pasarela-simulada/" in url)
    expect(page.locator(".monto")).to_be_visible()
    shot(page, "p02-pasarela-simulada")
    page.get_by_role("button", name="Aprobar pago").click()
    expect(page.get_by_text("Pago aprobado")).to_be_visible(timeout=10000)
    shot(page, "p03-pago-aprobado")
    page.context.close()

    pagada = next(c for c in api("/cuenta/list", {"estado": "pagada"}, caja) if c["mesa"] == "Terraza 2")
    assert pagada["propina"] > 0, pagada

    # Para llevar: caja envía el enlace; el primer intento se rechaza y el segundo se aprueba
    orden = api("/orden/create", {"mesa_id": mesas["Para llevar"]["id"], "clave_idempotencia": uuid.uuid4().hex,
                                  "cliente_nombre": "Valentina Ruiz", "cliente_telefono": "3104445566",
                                  "items": [{"producto_id": productos["Limonada natural"], "cantidad": 1}]}, caja)
    page = contexto(browser, 1366, 900)
    login(page, "caja.esquina")
    page.goto(f"{APP}/caja")
    page.get_by_role("button", name="Valentina Ruiz").first.click()
    page.get_by_role("button", name="Enlace de pago").click()
    dialogo = page.get_by_role("dialog")
    expect(dialogo).to_contain_text("Por pagar")
    enlace = page.locator("#enlace-pago").input_value()
    assert enlace.endswith(f"/pagar?seguimiento={orden['token_seguimiento']}"), enlace
    href = dialogo.get_by_role("link", name="Enviar por WhatsApp").get_attribute("href")
    assert href.startswith("https://wa.me/573104445566?text=Hola%20Valentina"), href
    shot(page, "p04-enlace-de-pago")
    page.context.close()

    page = contexto(browser, 390, 844, mobile=True)
    page.goto(enlace)
    page.get_by_role("button", name="Pagar").click()
    page.get_by_role("button", name="Rechazar pago").click()
    expect(page.get_by_text("El pago no fue aprobado")).to_be_visible(timeout=10000)
    shot(page, "p05-pago-rechazado")
    page.get_by_role("link", name="Intentar de nuevo").click()
    page.get_by_role("button", name="Pagar").click()
    page.get_by_role("button", name="Aprobar pago").click()
    expect(page.get_by_text("Pago aprobado")).to_be_visible(timeout=10000)
    page.context.close()

    # Administración: pagos y conciliación
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/pagos-linea")
    expect(page.locator("tbody")).to_contain_text("Rechazado")
    fila = page.locator("tr", has_text="Valentina Ruiz").filter(has_text="Aprobado")
    fila.get_by_role("button", name="Conciliar").click()
    page.fill("#cn-com", "250")
    page.get_by_role("dialog").get_by_role("button", name="Guardar").click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    shot(page, "p06-conciliacion")
    page.get_by_role("tab", name="Pasarela").click()
    shot(page, "p07-config-pasarela")
    page.context.close()

    browser.close()

terminar()
