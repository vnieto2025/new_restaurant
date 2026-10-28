"""Recorrido de domicilios: mostrador toma el domicilio, cocina despacha, se asigna D01, el domiciliario sale y entrega
desde el celular, caja recibe el efectivo con faltante, cobro en caja con domicilio y configuración."""
import uuid
from playwright.sync_api import sync_playwright, expect
from comun import APP, api, contexto, login, shot, elegir_opciones, abrir_navegador, terminar


caja_token = api("/login", {"usuario": "caja.esquina", "password": "demo1234"})["token"]
cocina_sesion = api("/login", {"usuario": "cocina.esquina", "password": "demo1234"})
if not api("/caja/estado", {}, caja_token)["turno"]:
    api("/caja/turno/abrir", {"fondo_inicial": 100000}, caja_token)
cliente = f"Lucía {uuid.uuid4().hex[:4]}"
telefono = "31" + uuid.uuid4().int.__str__()[:8]


def despachar(numero_texto):
    orden = next(o for o in api("/orden/list", {}, caja_token) if o["numero_texto"] == numero_texto)
    punto = next(p for p in cocina_sesion["puntos"] if p["nombre"] == "Cocina")
    tarjeta = next(c for c in api("/cocina/comandas", {"punto_produccion_id": punto["id"]}, cocina_sesion["token"])["en_proceso"]
                   if c["orden_id"] == orden["id"])
    api("/cocina/abrir", {"comanda_id": tarjeta["id"]}, cocina_sesion["token"])
    api("/cocina/despachar", {"comanda_id": tarjeta["id"]}, cocina_sesion["token"])
    return orden


with sync_playwright() as p:
    browser = abrir_navegador(p)

    # Mostrador: domicilio con barrio que sugiere la zona
    page = contexto(browser, 1280, 860)
    login(page, "caja.esquina")
    page.goto(f"{APP}/mostrador")
    page.get_by_role("radio", name="Domicilio").click()
    page.get_by_text("Perros y papas", exact=True).click()
    for _ in range(2):
        page.get_by_role("button", name="Papas a la francesa").first.click()
        if page.get_by_role("dialog").count():
            elegir_opciones(page, [])
    page.fill("#cap-tel", telefono)
    page.fill("#cap-nombre", cliente)
    page.get_by_text("acepta que lo registremos").click()
    page.fill("#en-dir", "Carrera 7 # 12-40 casa 3")
    page.fill("#en-barrio", "Candelaria")
    page.get_by_role("button", name="¿Zona Centro?").click()
    expect(page.locator("#en-zona")).not_to_have_value("")
    page.fill("#en-ind", "Reja verde, timbre de abajo")
    expect(page.locator(".total-envio")).to_contain_text("Total con domicilio")
    shot(page, "d01-mostrador-domicilio")
    page.get_by_role("button", name="Enviar a cocina").click()
    expect(page.get_by_text("enviado a cocina")).to_be_visible()
    orden = next(o for o in api("/orden/list", {}, caja_token) if o["cliente_nombre"] == cliente)
    assert orden["canal"] == "domicilio"
    page.get_by_role("tab", name="Pedidos").click()
    shot(page, "d02-mostrador-pedidos")

    # Entregas: aún en cocina; se asigna D01
    page.goto(f"{APP}/entregas")
    tarjeta = page.locator("article", has_text=cliente)
    expect(tarjeta).to_contain_text("En cocina")
    tarjeta.locator("select").select_option(label="D01 · Julián Moto")
    tarjeta.get_by_role("button", name="Asignar").click()
    expect(tarjeta).to_contain_text("D01 · Julián Moto")
    despachar(orden["numero_texto"])
    expect(tarjeta).to_contain_text("Lista para salir", timeout=20000)
    shot(page, "d03-entregas-lista")
    page.context.close()

    # Domiciliario en el celular: entra directo a sus entregas
    page = contexto(browser, 390, 844, mobile=True)
    login(page, "domi.esquina")
    page.wait_for_url(lambda url: "/entregas" in url)
    tarjeta = page.locator("article", has_text=cliente)
    expect(tarjeta).to_contain_text("Cobrar")
    shot(page, "d04-domiciliario-por-salir")
    tarjeta.get_by_role("button", name="Salió").click()
    page.get_by_role("tab", name="En camino").click()
    tarjeta = page.locator("article", has_text=cliente)
    expect(tarjeta).to_contain_text("En camino")
    shot(page, "d05-domiciliario-en-camino")
    tarjeta.get_by_role("button", name="Entregada").click()
    page.get_by_role("tab", name="Cerradas hoy").click()
    expect(page.locator("article", has_text=cliente)).to_contain_text("Cobró")
    shot(page, "d06-domiciliario-entregada")
    page.context.close()

    # Caja recibe el efectivo con 500 de menos
    page = contexto(browser, 1280, 860)
    login(page, "caja.esquina")
    antes = api("/caja/estado", {}, caja_token)["turno"]["resumen"]
    page.goto(f"{APP}/entregas")
    page.get_by_role("tab", name="Efectivo").click()
    grupo = page.locator("article", has_text="Julián Moto")
    esperado = next(g for g in api("/entrega/por_rendir", {}, caja_token)["pendientes"] if g["codigo"] == "D01")["esperado"]
    grupo.get_by_role("button", name="Recibir efectivo").click()
    page.fill("#rd-monto", str(esperado - 500))
    expect(page.get_by_role("dialog")).to_contain_text("Faltan")
    shot(page, "d07-rendicion")
    page.get_by_role("button", name="Registrar y cobrar").click()
    expect(page.get_by_text("faltante")).to_be_visible()
    expect(page.get_by_text("Nadie tiene efectivo por rendir")).to_be_visible()
    shot(page, "d08-rendiciones")
    despues = api("/caja/estado", {}, caja_token)["turno"]["resumen"]
    assert despues["faltantes_domiciliarios"] == antes["faltantes_domiciliarios"] + 500
    assert despues["efectivo_esperado"] == antes["efectivo_esperado"] + esperado - 500

    # Otro domicilio pagado en caja antes de salir: el cobro muestra el domicilio
    otro = api("/orden/create", {"mesa_id": next(m for m in api("/mesa/list", {"incluir_externa": True}, caja_token)
                                                 if m["tipo"] == "externa")["id"],
                                 "clave_idempotencia": uuid.uuid4().hex, "cliente_nombre": "Pago anticipado",
                                 "cliente_telefono": "3001234567",
                                 "items": [{"producto_id": orden["items"][0]["producto_id"], "cantidad": 3}],
                                 "entrega": {"zona_envio_id": next(z["id"] for z in api("/domicilio/zona/list", {}, caja_token)
                                                                   if z["nombre"] == "Norte"),
                                             "direccion": "Calle 80 # 20-10"}}, caja_token)
    page.goto(f"{APP}/caja")
    page.get_by_role("button", name="Pago anticipado").first.click()
    expect(page.locator(".totales")).to_contain_text("Domicilio")
    shot(page, "d09-cobro-con-domicilio")
    page.context.close()

    # Configuración
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/domicilios")
    expect(page.locator("tbody").first).to_contain_text("Centro")
    shot(page, "d10-config-domicilios")
    page.context.close()

    # Mostrador en celular con domicilio
    page = contexto(browser, 390, 844, mobile=True)
    login(page, "caja.esquina")
    page.goto(f"{APP}/mostrador")
    page.get_by_role("radio", name="Domicilio").click()
    page.locator("#en-dir").scroll_into_view_if_needed()
    shot(page, "d11-mostrador-movil")
    page.context.close()

    browser.close()

terminar()
