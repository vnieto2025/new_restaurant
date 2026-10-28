"""Recorrido del paso 10: panadería con plan Gestión vende en caja sin el módulo de pedidos, cancela una venta,
el administrador ve su plan en mora, y soporte gestiona plan, mensualidad y pagos del servicio."""
from playwright.sync_api import sync_playwright, expect
from comun import APP, OUT, contexto, login, shot, abrir_navegador, terminar


with sync_playwright() as p:
    browser = abrir_navegador(p)

    # Caja de la panadería: entra directo a la venta directa
    page = contexto(browser, 1366, 900)
    login(page, "caja.trigo")
    page.goto(f"{APP}/caja")
    page.wait_for_timeout(1000)
    if page.get_by_role("button", name="Abrir turno").count():
        page.get_by_role("button", name="Abrir turno").click()
    expect(page.get_by_role("tab", name="Venta directa")).to_have_attribute("aria-selected", "true")
    expect(page.get_by_role("tab", name="Turno y jornada")).to_be_visible()
    page.get_by_role("button", name="Pan de bono").first.click()
    page.get_by_role("button", name="Pan de bono").first.click()
    page.get_by_role("button", name="Pan de bono").first.click()
    page.get_by_role("tab", name="Bebidas").click()
    page.get_by_role("button", name="Café con leche").first.click()
    shot(page, "v01-venta-directa")
    page.get_by_role("button", name="Cobrar", exact=True).click()
    try:
        expect(page.locator(".cobro .cabeza h2")).to_have_text("Venta directa")
    except AssertionError:
        page.screenshot(path=str(OUT / "fallo.png"))
        raise
    page.locator(".medios").get_by_role("button", name="Efectivo").click()
    page.get_by_role("button", name="Cobrar $").click()
    expect(page.locator(".sello-ok")).to_be_visible()
    shot(page, "v02-venta-cobrada")

    # Una venta que no se cobra se cancela y el producto vuelve
    page.get_by_role("tab", name="Venta directa").click()
    page.get_by_role("button", name="Croissant").first.click()
    page.fill("#vd-nombre", "Señora del 302")
    page.get_by_role("button", name="Cobrar", exact=True).click()
    expect(page.locator(".cobro .cabeza h2")).to_have_text("Señora del 302")
    page.locator(".cobro").get_by_role("button", name="Cancelar venta").click()
    dialogo = page.get_by_role("dialog")
    dialogo.get_by_role("button", name="El cliente se arrepintió").click()
    shot(page, "v03-cancelar-venta")
    dialogo.get_by_role("button", name="Cancelar venta").click()
    expect(page.locator(".cobro")).to_have_count(0)
    expect(page.locator(".lista")).to_contain_text("No hay nada por cobrar")
    page.context.close()

    # Administración de la panadería: sin mesas ni QR en el menú, aviso de mora y su plan
    page = contexto(browser, 1366, 900)
    login(page, "trigo")
    page.goto(f"{APP}/admin/productos")
    expect(page.locator(".aviso-cuenta")).to_contain_text("pago del servicio está pendiente")
    menu = page.locator("nav[aria-label='Administración']")
    expect(menu).not_to_contain_text("Mesas")
    page.get_by_role("link", name="Ver mi plan").click()
    expect(page.locator(".grande").first).to_have_text("Gestión")
    shot(page, "v04-mi-plan")
    page.context.close()

    # Soporte: plan del contrato, mensualidad y pago del servicio
    page = contexto(browser, 1366, 900)
    login(page, "soporte", "Soporte12345")
    page.goto(f"{APP}/plataforma")
    fila = page.locator("tr", has_text="Dulce Trigo")
    expect(fila).to_contain_text("En mora")
    shot(page, "v05-plataforma")
    fila.get_by_role("button", name="Contrato").click()
    dialogo = page.get_by_role("dialog")
    dialogo.get_by_role("checkbox", name="Facturación electrónica").check()
    expect(dialogo.locator("legend").first).to_contain_text("Gestión")
    shot(page, "v06-contrato-plan")
    dialogo.get_by_role("checkbox", name="Facturación electrónica").uncheck()
    dialogo.get_by_role("button", name="Guardar contrato").click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    page.locator("tr", has_text="Dulce Trigo").get_by_role("button", name="Pagos").click()
    dialogo = page.get_by_role("dialog")
    dialogo.locator("#p-ref").fill("BANCOLOMBIA-5521")
    dialogo.locator("#p-fact").fill("FS-0001")
    dialogo.get_by_role("button", name="Registrar pago").click()
    expect(dialogo.locator("tbody")).to_contain_text("FS-0001")
    expect(dialogo).to_contain_text("Al día")
    shot(page, "v07-pago-servicio")
    page.context.close()

    # Con pedidos, la caja también tiene venta directa
    page = contexto(browser, 1366, 900)
    login(page, "caja.esquina")
    page.goto(f"{APP}/caja")
    expect(page.get_by_role("tab", name="Por cobrar")).to_have_attribute("aria-selected", "true")
    expect(page.get_by_role("tab", name="Venta directa")).to_be_visible()
    page.context.close()

    browser.close()

terminar()
