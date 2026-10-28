"""Recorrido de compras: compra rápida pagada de caja, orden al proveedor, recepción parcial desde la tablet de cocina,
cierre, alerta de precio, lista sugerida y proveedores."""
from playwright.sync_api import sync_playwright, expect
from comun import APP, api, contexto, login, shot, abrir_navegador, terminar


admin = api("/login", {"usuario": "admin.esquina", "password": "demo1234"})["token"]
if not api("/caja/estado", {}, admin)["turno"]:
    api("/caja/turno/abrir", {"fondo_inicial": 200000}, admin)


def insumo(nombre):
    return next(i for i in api("/insumo/list", {}, admin) if i["nombre"] == nombre)


with sync_playwright() as p:
    browser = abrir_navegador(p)

    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/compras")
    expect(page.locator("tbody")).to_contain_text("Fruver La Cosecha")
    shot(page, "c01-por-recibir")

    # Compra rápida de plaza pagada con dinero de la caja
    gastos = api("/caja/estado", {}, admin)["turno"]["resumen"]["gastos"]
    limon = insumo("Limón")["stock"]
    page.get_by_role("button", name="Compra rápida").click()
    dialogo = page.get_by_role("dialog")
    page.fill("#cp-lugar", "Plaza de mercado")
    page.select_option("#cp-pago", "caja")
    page.get_by_label("Insumo 1", exact=True).select_option(label="Limón")
    page.get_by_label("Cantidad 1", exact=True).fill("20")
    page.get_by_label("Valor pagado 1").fill("6000")
    shot(page, "c02-compra-rapida")
    dialogo.get_by_role("button", name="Registrar y sumar al inventario").click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    assert insumo("Limón")["stock"] == limon + 20
    assert api("/caja/estado", {}, admin)["turno"]["resumen"]["gastos"] == gastos + 6000

    # Orden de compra a Distribuidora Andina: la presentación habitual se llena sola
    page.get_by_role("button", name="Orden de compra").click()
    page.select_option("#cp-prov", label="Distribuidora Andina")
    page.get_by_label("Insumo 1", exact=True).select_option(label="Carne de res molida ★")
    expect(page.get_by_label("Presentación 1")).to_have_value(str(next(
        x["id"] for x in insumo("Carne de res molida")["presentaciones"] if x["nombre"] == "Paquete 1 kg")))
    page.get_by_label("Cantidad 1", exact=True).fill("5")
    page.get_by_label("Precio 1", exact=True).fill("30000")
    page.get_by_role("button", name="Agregar insumo").click()
    page.get_by_label("Insumo 2", exact=True).select_option(label="Queso mozzarella ★")
    page.get_by_label("Cantidad 2", exact=True).fill("1")
    page.get_by_label("Precio 2", exact=True).fill("78000")
    shot(page, "c03-orden")
    page.get_by_role("dialog").get_by_role("button", name="Guardar como solicitada").click()
    expect(page.get_by_role("dialog")).to_contain_text("Mensaje para el proveedor")
    expect(page.get_by_role("dialog")).to_contain_text("5 Paquete 1 kg de Carne de res molida")
    href = page.get_by_role("link", name="Enviar por WhatsApp").get_attribute("href")
    assert href.startswith("https://wa.me/573104567890?text="), href
    shot(page, "c04-orden-detalle")
    page.context.close()

    # La tablet de cocina recibe: llegaron 4 de 5 paquetes
    page = contexto(browser, 1024, 768)
    login(page, "cocina.esquina")
    page.wait_for_url(lambda url: "/produccion" in url)
    page.goto(f"{APP}/bodega?vista=recibir")
    carne = insumo("Carne de res molida")["stock"]
    page.get_by_role("button", name="Distribuidora Andina").click()
    dialogo = page.get_by_role("dialog")
    expect(dialogo).to_contain_text("Recibir compra")
    campos = dialogo.locator("input[id^='rc-llego-']")
    campos.first.fill("4")
    dialogo.locator("input[id^='rc-nov-']").first.fill("Faltó un paquete")
    shot(page, "c05-recepcion-cocina")
    dialogo.get_by_role("button", name="Confirmar recepción").click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    assert insumo("Carne de res molida")["stock"] == carne + 4000
    shot(page, "c06-bodega-recibir")
    page.context.close()

    # Administración: la compra quedó en parte; se cierra sin esperar el faltante
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/compras")
    fila = page.locator("tr", has=page.get_by_text("Distribuidora Andina", exact=True))
    expect(fila).to_contain_text("Recibida en parte")
    fila.get_by_role("button", name="Ver").click()
    expect(page.get_by_role("dialog")).to_contain_text("faltan 1")
    shot(page, "c07-detalle-parcial")
    page.get_by_role("dialog").get_by_role("button", name="Cerrar compra").click()
    page.fill("#cc-factura", "FV-1180")
    page.get_by_label("Cerrar sin esperar lo que faltó").check()
    page.get_by_role("button", name="Confirmar cierre").click()
    expect(page.get_by_role("dialog").first).to_contain_text("Cerrada")
    page.keyboard.press("Escape")

    # Otra compra rápida a Andina más cara: avisa la subida de precio
    page.get_by_role("button", name="Compra rápida").click()
    page.select_option("#cp-prov", label="Distribuidora Andina")
    page.select_option("#cp-pago", "credito")
    page.get_by_label("Insumo 1", exact=True).select_option(label="Carne de res molida ★")
    page.get_by_label("Cantidad 1", exact=True).fill("2")
    page.get_by_label("Valor pagado 1").fill("76000")
    page.get_by_role("dialog").get_by_role("button", name="Registrar y sumar al inventario").click()
    expect(page.get_by_text("subió costos")).to_be_visible()
    expect(page.locator(".alertas")).to_contain_text("Carne de res molida")
    shot(page, "c08-alerta-precio")

    page.get_by_role("tab", name="Historial").click()
    expect(page.locator("tbody")).to_contain_text("Plaza de mercado")
    shot(page, "c09-historial")
    page.get_by_role("tab", name="Qué comprar").click()
    page.wait_for_timeout(500)
    shot(page, "c10-sugerida")

    page.goto(f"{APP}/admin/proveedores")
    expect(page.locator("tbody")).to_contain_text("Distribuidora Andina")
    shot(page, "c11-proveedores")
    page.locator("tr", has=page.get_by_text("Distribuidora Andina", exact=True)).get_by_role("button", name="Ver").click()
    shot(page, "c12-proveedor-insumos")
    page.get_by_role("tab", name="Precios").click()
    expect(page.get_by_role("dialog")).to_contain_text("Carne de res molida")
    shot(page, "c13-proveedor-precios")
    page.context.close()

    # Celular
    page = contexto(browser, 390, 844, mobile=True)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/compras")
    expect(page.locator("tbody")).to_contain_text("Fruver")
    shot(page, "c14-compras-movil")
    page.get_by_role("button", name="Compra rápida").click()
    shot(page, "c15-rapida-movil")
    page.get_by_label("Insumo 1", exact=True).select_option(label="Limón")
    page.get_by_label("Cantidad 1", exact=True).fill("10")
    page.get_by_label("Insumo 1", exact=True).scroll_into_view_if_needed()
    shot(page, "c16-rapida-linea-movil")
    page.context.close()

    browser.close()

terminar()
