"""Recorrido del reparto por zona: el Salón manda el pedido entero a la Cocina (salchipapa y limonada juntas); el Bar no
recibe nada. El administrador ve y cambia el reparto en Zonas."""
from playwright.sync_api import sync_playwright, expect
from comun import APP, api, contexto, login, shot, abrir_navegador, terminar

admin = api("/login", {"usuario": "admin.esquina", "password": "demo1234"})["token"]
mesa = next(m for m in api("/mesa/list", {}, admin) if m["nombre"] == "Mesa 2")
puntos = {x["nombre"]: x["id"] for x in api("/punto_produccion/list", {}, admin)}

with sync_playwright() as p:
    browser = abrir_navegador(p)

    # Administrador: cada zona dice cómo reparte
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/zonas")
    expect(page.get_by_role("row", name="Salón")).to_contain_text("Todo el pedido a su punto")
    expect(page.get_by_role("row", name="Terraza")).to_contain_text("Cada producto a su punto")
    page.get_by_role("row", name="Salón").get_by_role("button", name="Editar").click()
    expect(page.get_by_label("Cómo se reparte un pedido")).to_have_value("zona")
    shot(page, "r01-zona")
    page.context.close()

    # Mesero del Salón: salchipapa y limonada en el mismo pedido
    page = contexto(browser, 1180, 820)
    login(page, "mesero.salon")
    page.goto(f"{APP}/mesas/{mesa['id']}")
    for categoria, producto in [("Perros y papas", "Salchipapa"), ("Bebidas", "Limonada natural")]:
        page.get_by_role("tab", name=categoria).click()
        page.get_by_role("button", name=producto).click()
        # Con adicionales se abre su ventana: se agrega sin elegir ninguno
        page.wait_for_timeout(300)
        dialogo = page.get_by_role("dialog")
        if dialogo.count():
            dialogo.get_by_role("button", name="Agregar").click()
    page.get_by_role("button", name="Enviar a cocina").click()
    page.get_by_role("tab", name="En la mesa").click()
    expect(page.get_by_text("1 × Limonada natural")).to_be_visible()
    page.context.close()

    # Cocina: llegan las dos en una sola comanda
    page = contexto(browser, 1280, 800)
    login(page, "cocina.esquina")
    page.goto(f"{APP}/produccion/{puntos['Cocina']}")
    tarjeta = page.locator("article", has_text="Mesa 2")
    expect(tarjeta).to_have_count(1)
    expect(tarjeta).to_contain_text("Salchipapa")
    expect(tarjeta).to_contain_text("Limonada natural")
    shot(page, "r02-cocina")
    page.context.close()

    # Bar: no le llegó nada de la Mesa 2
    page = contexto(browser, 1280, 800)
    login(page, "bar.esquina")
    page.goto(f"{APP}/produccion/{puntos['Bar']}")
    expect(page.get_by_text("Sin comandas pendientes")).to_be_visible()
    expect(page.locator("article", has_text="Mesa 2")).to_have_count(0)
    shot(page, "r03-bar")
    browser.close()

terminar()
