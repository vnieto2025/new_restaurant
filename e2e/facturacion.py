"""Recorrido de facturación: cobro con factura a nombre, tirilla con desglose, administración de documentos, numeración e impuestos."""
import time
import uuid
from playwright.sync_api import sync_playwright, expect
from comun import APP, OUT, api, contexto, login, shot, abrir_navegador, terminar

# Reutiliza los ayudantes de e2e.py sin ejecutar su recorrido

caja_token = api("/login", {"usuario": "caja.esquina", "password": "demo1234"})["token"]
admin_token = api("/login", {"usuario": "admin.esquina", "password": "demo1234"})["token"]
if not api("/caja/estado", token=caja_token)["turno"]:
    api("/caja/turno/abrir", {"fondo_inicial": 100000}, caja_token)
productos = {p["nombre"]: p["id"] for p in api("/producto/list", {"todos": True}, admin_token)}
externa = next(m for m in api("/mesa/list", {"incluir_externa": True}, caja_token) if m["nombre"] == "Para llevar")
cliente = f"Factura {int(time.time()) % 10000}"
api("/orden/create", {"mesa_id": externa["id"], "clave_idempotencia": uuid.uuid4().hex, "cliente_nombre": cliente,
                      "items": [{"producto_id": productos["Limonada natural"], "cantidad": 2},
                                {"producto_id": productos["Salchipapa"], "cantidad": 1}]}, caja_token)

with sync_playwright() as p:
    browser = abrir_navegador(p)

    # Caja: cobro con factura a nombre del cliente
    page = contexto(browser, 1366, 900)
    login(page, "caja.esquina")
    page.goto(f"{APP}/caja")
    page.get_by_role("button", name=cliente).click()
    page.get_by_text("Factura a nombre del cliente").click()
    page.select_option("#fr-tipo", "NIT")
    page.fill("#fr-doc", "900123456-7")
    page.fill("#fr-nombre", "Comercial Andes SAS")
    page.fill("#fr-correo", "compras@andes.co")
    page.locator(".medios").get_by_role("button", name="Efectivo").click()
    shot(page, "f01-cobro-con-factura")
    page.get_by_role("button", name="Cobrar").click()
    expect(page.locator(".historial").filter(has_text="Documento de venta")).to_contain_text("Factura electrónica FE", timeout=8000)
    page.wait_for_timeout(2500)  # la cola de emisión envía en segundo plano
    page.get_by_role("tab", name="Cobradas hoy").click()
    page.get_by_role("tab", name="Por cobrar").click()
    shot(page, "f02-cobrada-con-documento")
    page.context.close()

    # Tirilla del comprobante con desglose (vista de impresión)
    page = contexto(browser, 420, 1100)
    login(page, "caja.esquina")
    page.goto(f"{APP}/caja")
    page.get_by_role("tab", name="Cobradas hoy").click()
    page.get_by_role("button", name="Ver").first.click()
    page.get_by_role("button", name="Imprimir comprobante").click()
    page.emulate_media(media="print")
    page.wait_for_timeout(500)
    page.screenshot(path=str(OUT / "f03-tirilla.png"), full_page=True)
    texto = page.locator(".print-root").inner_text()
    assert "Comercial Andes SAS" in texto and "Impuesto al consumo" in texto and "Resolución" in texto, texto
    page.context.close()

    # Administración: documentos, detalle, numeración, ventas por impuesto, proveedor
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/facturacion")
    expect(page.locator("tbody tr").first).to_be_visible()
    shot(page, "f04-documentos")
    page.get_by_role("button", name="Ver").first.click()
    expect(page.get_by_role("dialog")).to_contain_text("CUFE")
    shot(page, "f05-detalle-documento")
    page.keyboard.press("Escape")
    page.get_by_role("tab", name="Numeración").click()
    expect(page.locator("tbody")).to_contain_text("POSE")
    shot(page, "f06-numeracion")
    page.get_by_role("tab", name="Ventas por impuesto").click()
    expect(page.locator("tfoot")).to_contain_text("Total")
    shot(page, "f07-por-impuesto")
    page.get_by_role("tab", name="Proveedor").click()
    expect(page.locator("#c-modo")).to_be_visible()
    shot(page, "f08-proveedor")
    page.goto(f"{APP}/admin/impuestos")
    expect(page.locator("tbody")).to_contain_text("Impuesto al consumo")
    shot(page, "f09-impuestos")
    page.goto(f"{APP}/admin/productos")
    page.get_by_role("button", name="Editar").first.click()
    expect(page.locator("#p-impuesto")).to_be_visible()
    shot(page, "f10-producto-impuesto")
    page.context.close()

    # Celular
    page = contexto(browser, 390, 844, mobile=True)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/facturacion")
    expect(page.locator("tbody tr").first).to_be_visible()
    shot(page, "f11-facturacion-movil")
    page.context.close()

    browser.close()

terminar()
