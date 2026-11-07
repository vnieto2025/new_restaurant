"""Recorrido de agotados sugeridos: se acaban el pan de perro y la papa; la pantalla de cocina sugiere agotar
los platos que los usan; el administrador ve en Hoy lo que se está acabando y, al llegar el pan, vuelve a ofrecer el perro."""
from playwright.sync_api import sync_playwright, expect
from comun import APP, api, contexto, login, shot, abrir_navegador, terminar

admin = api("/login", {"usuario": "admin.esquina", "password": "demo1234"})["token"]
insumos = {i["nombre"]: i for i in api("/insumo/list", {}, admin)}


def ajustar(nombre, existencia):
    api("/inventario/ajuste", {"insumo_id": insumos[nombre]["id"], "existencia_real": existencia, "motivo": "Conteo de la tarde"}, admin)


# Pan de perro en cero, papa para menos de una porción de papas y agua para 3
ajustar("Pan de perro", 0)
ajustar("Papa", 200)
ajustar("Agua sin gas", 3)

with sync_playwright() as p:
    browser = abrir_navegador(p)

    # Cocina: sugerencias de su punto
    page = contexto(browser, 1280, 800)
    login(page, "cocina.esquina")
    punto = next(x["id"] for x in api("/login", {"usuario": "cocina.esquina", "password": "demo1234"})["puntos"] if x["nombre"] == "Cocina")
    page.goto(f"{APP}/produccion/{punto}")
    avisos = page.get_by_role("region", name="Sugerencias de agotados")
    expect(avisos).to_contain_text("Se acabó con qué prepararlos")
    expect(avisos).to_contain_text("Pan de perro: quedan 0 und y cada uno lleva 1 und")
    expect(avisos).to_contain_text("También deja sin Combo clásico")
    # El agua es del bar: no aparece en la cocina
    expect(avisos).not_to_contain_text("Agua sin gas")
    shot(page, "a01-cocina-sugiere")
    avisos.get_by_role("button", name="Todavía hay Salchipapa").click()
    expect(avisos).not_to_contain_text("Salchipapa")
    avisos.get_by_role("button", name="Marcar agotado Perro sencillo").click()
    expect(page.get_by_text("Perro sencillo agotado en todas las cartas.")).to_be_visible()
    expect(avisos).not_to_contain_text("Perro sencillo")
    shot(page, "a02-cocina-marcado")
    page.context.close()

    # Mesero: el perro ya no se puede pedir
    page = contexto(browser, 1180, 820)
    login(page, "mesero.salon")
    mesa = next(m for m in api("/mesa/list", {}, admin) if m["nombre"] == "Mesa 1")
    page.goto(f"{APP}/mesas/{mesa['id']}")
    page.get_by_role("tab", name="Perros y papas").click()
    expect(page.get_by_role("button", name="Perro sencillo")).to_contain_text("Agotado")
    shot(page, "a03-mesero-agotado")
    page.context.close()

    # Administrador en Hoy: lo que se acaba en todo el restaurante
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin")
    avisos = page.get_by_role("region", name="Sugerencias de agotados")
    expect(avisos).to_contain_text("Papas a la francesa")
    expect(avisos).to_contain_text("Agua sin gas: quedan para 3")
    avisos.scroll_into_view_if_needed()
    shot(page, "a04-hoy")

    # Llegó el pan: se sugiere volver a ofrecer el perro
    api("/inventario/entrada", {"insumo_id": insumos["Pan de perro"]["id"], "cantidad": 20, "costo_unitario": 700}, admin)
    page.reload()
    expect(avisos).to_contain_text("Agotados que ya se pueden preparar")
    avisos.scroll_into_view_if_needed()
    shot(page, "a05-volver-a-ofrecer")
    avisos.get_by_role("button", name="Volver a ofrecer Perro sencillo").click()
    expect(page.get_by_text("Perro sencillo disponible de nuevo.")).to_be_visible()
    expect(avisos).not_to_contain_text("Agotados que ya se pueden preparar")
    browser.close()

terminar()
