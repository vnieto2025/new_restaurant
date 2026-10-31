"""Recorrido del contador: entra directo a administración, ve solo lo de consulta, abre reportes y documentos, descarga
datos y no tiene acceso a clientes ni a la configuración."""
from playwright.sync_api import sync_playwright, expect
from comun import APP, OUT, contexto, login, shot, abrir_navegador, terminar

with sync_playwright() as p:
    browser = abrir_navegador(p)
    page = contexto(browser, 1366, 900)
    login(page, "contador.esquina")
    page.wait_for_url("**/admin**")
    menu = page.get_by_role("navigation", name="Administración")
    for visible in ["Reportes", "Exportar datos", "Auditoría", "Compras", "Facturación"]:
        expect(menu.get_by_role("link", name=visible, exact=True)).to_be_visible()
    for oculto in ["Productos", "Personal", "Clientes", "Configuración", "Zonas"]:
        expect(menu.get_by_role("link", name=oculto, exact=True)).to_have_count(0)
    shot(page, "c01-inicio-contador")

    menu.get_by_role("link", name="Reportes", exact=True).click()
    expect(page.get_by_role("heading", name="Reportes")).to_be_visible()
    shot(page, "c02-reportes")

    menu.get_by_role("link", name="Facturación", exact=True).click()
    expect(page.get_by_role("heading", name="Facturación")).to_be_visible()
    shot(page, "c03-facturacion")

    menu.get_by_role("link", name="Compras", exact=True).click()
    expect(page.get_by_role("heading", name="Compras")).to_be_visible()
    expect(page.get_by_role("button", name="Compra rápida")).to_have_count(0)
    shot(page, "c04-compras")

    menu.get_by_role("link", name="Exportar datos", exact=True).click()
    expect(page.get_by_text("Horas trabajadas")).to_be_visible()
    expect(page.get_by_text("Contacto y autorizaciones")).to_have_count(0)
    with page.expect_download() as descarga:
        page.get_by_role("button", name="Descargar Productos en CSV").click()
    descarga.value.save_as(OUT / "productos.csv")
    shot(page, "c05-exportar")

    # Una pantalla sin permiso devuelve al inicio
    page.goto(f"{APP}/admin/clientes")
    page.wait_for_url(lambda url: "/admin/clientes" not in url)

    browser.close()

terminar()
