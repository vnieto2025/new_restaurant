"""Recorrido del domicilio pedido por el cliente en la web: el administrador ve el enlace y el QR, el cliente pide desde
el celular (zona, dirección, pedido mínimo, pago en línea), quien despacha confirma o rechaza en Entregas, el cliente
sigue su pedido y paga cuando lo confirman. Al final se pausa el enlace."""
import uuid
from playwright.sync_api import sync_playwright, expect
from comun import APP, api, contexto, login, shot, abrir_navegador, terminar


admin_token = api("/login", {"usuario": "admin.esquina", "password": "demo1234"})["token"]
caja_token = api("/login", {"usuario": "caja.esquina", "password": "demo1234"})["token"]
web = api("/domicilio/web/get", {}, admin_token)
token = web["url"].rsplit("/", 1)[1]
cliente = f"Mariana {uuid.uuid4().hex[:4]}"
telefono = "31" + str(uuid.uuid4().int)[:8]

with sync_playwright() as p:
    browser = abrir_navegador(p)

    # Administración: enlace, QR y configuración
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/domicilios")
    seccion = page.locator("section", has_text="Pedidos por la web")
    expect(seccion).to_contain_text("Recibiendo pedidos")
    expect(seccion.locator(".web-qr svg")).to_be_visible()
    shot(page, "w01-admin-enlace")
    seccion.get_by_role("button", name="Configurar").click()
    expect(page.get_by_role("dialog")).to_contain_text("Confirmar cada pedido")
    shot(page, "w02-admin-configurar")
    page.get_by_role("dialog").get_by_role("button", name="Cancelar").click()
    page.context.close()

    # Cliente en el celular: carta de domicilio con el aviso del restaurante
    cel = contexto(browser, 390, 844, mobile=True)
    cel.goto(f"{APP}/q/{token}")
    expect(cel.get_by_text("Domicilios", exact=True)).to_be_visible()
    expect(cel.get_by_text("Tiempo estimado")).to_be_visible()
    # "Pagar la cuenta" es de las mesas; el domicilio se paga desde su seguimiento
    expect(cel.get_by_role("link", name="Pagar la cuenta")).to_have_count(0)
    shot(cel, "w03-carta-domicilio")
    cel.get_by_label("Agregar Limonada natural").click()
    cel.get_by_label("Agregar Limonada natural").click()
    cel.get_by_text("Ver pedido (2)").click()
    # Sin datos no se envía
    cel.get_by_role("button", name="Pedir domicilio").click()
    expect(cel.get_by_role("alert")).to_contain_text("nombre")
    # Norte tiene pedido mínimo: el cliente ve cuánto le falta
    cel.locator("#zona-envio").select_option(label="Norte · domicilio $ 5.000")
    expect(cel.locator(".aviso-minimo")).to_contain_text("pedido mínimo de Norte")
    shot(cel, "w04-pedido-minimo")
    cel.locator("#zona-envio").select_option(label="Centro · domicilio $ 3.000")
    expect(cel.locator(".aviso-minimo")).to_have_count(0)
    cel.fill("#direccion", "Calle 10 # 5-21 apto 302")
    cel.fill("#barrio", "Centro")
    cel.fill("#indicaciones", "Edificio blanco, citófono 302")
    cel.fill("#nombre", cliente)
    cel.fill("#telefono", telefono)
    cel.locator(".aviso-datos").get_by_text("Acepto").click()
    cel.get_by_text("En línea, con tarjeta").click()
    expect(cel.get_by_text("Podrás pagar cuando el restaurante confirme")).to_be_visible()
    expect(cel.locator(".total")).to_contain_text("$")
    shot(cel, "w05-datos-entrega")
    cel.get_by_role("button", name="Pedir domicilio").click()
    cel.wait_for_url("**/pedido/**")
    expect(cel.get_by_text("El restaurante confirmará tu pedido")).to_be_visible()
    expect(cel.get_by_text("Calle 10 # 5-21")).to_be_visible()
    expect(cel.get_by_role("link", name="Pagar en línea")).to_have_count(0)
    shot(cel, "w06-seguimiento-por-confirmar")

    # Quien despacha lo ve primero, marcado como web y por confirmar
    page = contexto(browser, 1280, 860)
    login(page, "caja.esquina")
    page.goto(f"{APP}/entregas")
    tarjeta = page.locator("article", has_text=cliente)
    expect(tarjeta).to_contain_text("Por confirmar")
    expect(tarjeta).to_contain_text("Web")
    expect(tarjeta).to_contain_text("Pagará en línea")
    expect(tarjeta.locator("select")).to_have_count(0)
    shot(page, "w07-entregas-por-confirmar")
    tarjeta.get_by_role("button", name="Confirmar y enviar a cocina").click()
    expect(page.get_by_text("confirmado y enviado a cocina")).to_be_visible()
    expect(tarjeta).to_contain_text("En cocina")
    expect(tarjeta.locator("select")).to_have_count(1)
    shot(page, "w08-entregas-confirmado")

    # El cliente ve el cambio solo y ya puede pagar en línea, con el domicilio incluido
    expect(cel.get_by_text("La cocina ya recibió tu pedido")).to_be_visible(timeout=15000)
    cel.get_by_role("link", name="Pagar en línea").click()
    cel.wait_for_url("**/pagar**")
    expect(cel.get_by_text("Domicilio")).to_be_visible()
    shot(cel, "w09-pagar-con-domicilio")

    # Otro pedido web que el restaurante rechaza: el cliente ve el motivo y no se cobra
    segundo = api("/publico/orden/create", {
        "token": token, "clave_idempotencia": uuid.uuid4().hex, "cliente_nombre": "Pedido lejano",
        "cliente_telefono": "3" + str(uuid.uuid4().int)[:9], "acepta_datos": True,
        "items": [{"producto_id": next(pr["id"] for c in api("/publico/qr", {"token": token})["categorias"]
                                       for pr in c["productos"] if pr["nombre"] == "Limonada natural"), "cantidad": 1}],
        "entrega": {"zona_envio_id": next(z["id"] for z in api("/publico/qr", {"token": token})["domicilio"]["zonas"]
                                          if z["nombre"] == "Sur"), "direccion": "Vereda El Alto, finca 3"}})
    tarjeta = page.locator("article", has_text="Pedido lejano")
    expect(tarjeta).to_contain_text("Por confirmar", timeout=15000)
    tarjeta.get_by_role("button", name="Rechazar").click()
    page.get_by_role("dialog").get_by_role("button", name="Dirección fuera de cobertura").click()
    shot(page, "w10-rechazar")
    page.get_by_role("dialog").get_by_role("button", name="Rechazar pedido").click()
    expect(page.get_by_text("rechazado. No se cobra")).to_be_visible()
    expect(page.locator("article", has_text="Pedido lejano")).to_have_count(0)
    page.context.close()

    cel.goto(f"{APP}/pedido/{segundo['seguimiento']}")
    expect(cel.get_by_text("Tu pedido fue cancelado")).to_be_visible()
    expect(cel.get_by_text("Dirección fuera de cobertura")).to_be_visible()
    shot(cel, "w11-seguimiento-rechazado")

    # Al volver, la carta recuerda los datos de entrega en el celular
    cel.goto(f"{APP}/q/{token}")
    cel.get_by_label("Agregar Limonada natural").click()
    cel.get_by_text("Ver pedido (1)").click()
    expect(cel.locator("#direccion")).to_have_value("Calle 10 # 5-21 apto 302")
    expect(cel.locator("#nombre")).to_have_value(cliente)
    cel.context.close()

    # Carta de domicilio en computador
    page = contexto(browser, 1280, 860)
    page.goto(f"{APP}/q/{token}")
    page.get_by_label("Agregar Limonada natural").click()
    page.get_by_text("Ver pedido (1)").click()
    shot(page, "w12-carta-escritorio")
    page.context.close()

    # Pausar: el enlace muestra que no se reciben domicilios
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/domicilios")
    page.locator("section", has_text="Pedidos por la web").get_by_role("button", name="Pausar").click()
    expect(page.get_by_text("Pedidos por la web pausados")).to_be_visible()
    shot(page, "w13-admin-pausado")
    cel = contexto(browser, 390, 844, mobile=True)
    cel.goto(f"{APP}/q/{token}")
    expect(cel.get_by_text("no está recibiendo domicilios")).to_be_visible()
    shot(cel, "w14-carta-pausada")
    page.locator("section", has_text="Pedidos por la web").get_by_role("button", name="Activar").click()
    expect(page.get_by_text("Pedidos por la web activos")).to_be_visible()

    browser.close()

terminar()
