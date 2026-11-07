"""Recorrido del restaurante de práctica: el administrador lo crea desde la puesta en marcha; el mesero entra,
toma una orden con la franja de práctica a la vista; el restaurante real no la ve; se reinicia y el mesero vuelve al real."""
from playwright.sync_api import sync_playwright, expect
from comun import APP, api, contexto, login, shot, abrir_navegador, terminar

admin = api("/login", {"usuario": "admin.esquina", "password": "demo1234"})["token"]
ordenes_reales = len(api("/orden/list", {"vista": "jornada"}, admin))

with sync_playwright() as p:
    browser = abrir_navegador(p)

    # Administrador: crea la práctica
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/puesta-en-marcha")
    panel = page.get_by_role("region", name="Restaurante de práctica")
    expect(panel).to_contain_text("Allí no hay facturación electrónica ni pagos en línea")
    panel.get_by_role("button", name="Crear restaurante de práctica").click()
    expect(panel).to_contain_text("La Esquina Centro · Práctica")
    expect(panel).to_contain_text("0 órdenes de práctica")
    panel.scroll_into_view_if_needed()
    shot(page, "p01-creada")

    # Mesero: entra a la práctica desde el inicio y toma una orden
    mesero = contexto(browser, 1180, 820)
    login(mesero, "mesero.terraza")
    mesero.goto(f"{APP}/?menu=1")
    mesero.get_by_role("button", name="Entrar a la práctica").click()
    franja = mesero.get_by_role("status").filter(has_text="Modo práctica")
    expect(franja).to_be_visible()
    shot(mesero, "p02-inicio-practica")
    mesero.goto(f"{APP}/mesas")
    expect(franja).to_be_visible()
    mesero.get_by_role("button", name="Terraza 2").click()
    mesero.wait_for_url("**/mesas/**")
    mesero.get_by_role("tab", name="Perros y papas").click()
    mesero.get_by_role("button", name="Papas a la francesa").click()
    mesero.get_by_role("dialog").get_by_role("button", name="Agregar").click()
    mesero.get_by_role("button", name="Enviar a cocina").click()
    mesero.get_by_role("tab", name="En la mesa").click()
    expect(mesero.get_by_text("1 × Papas a la francesa")).to_be_visible()
    shot(mesero, "p03-orden-practica")

    # El restaurante real no la ve; la práctica sí
    assert len(api("/orden/list", {"vista": "jornada"}, admin)) == ordenes_reales
    page.reload()
    expect(panel).to_contain_text("1 orden de práctica")

    # Reiniciar desde el real deja la práctica vacía
    panel.get_by_role("button", name="Reiniciar práctica").click()
    page.get_by_role("dialog").get_by_role("button", name="Reiniciar").click()
    expect(page.get_by_text("Práctica reiniciada.")).to_be_visible()
    expect(panel).to_contain_text("0 órdenes de práctica")
    shot(page, "p04-reiniciada")

    # El mesero vuelve al real con la franja
    franja.get_by_role("button", name="Volver a La Esquina Centro").click()
    expect(mesero.get_by_text("De vuelta en La Esquina Centro.")).to_be_visible()
    expect(franja).to_have_count(0)
    shot(mesero, "p05-de-vuelta")
    browser.close()

terminar()
