"""Recorrido de avisos por WhatsApp: aviso manual de orden lista en mostrador, aviso de domicilio en camino,
configuración en modo automático con el simulador y envío de la cola en segundo plano."""
import time
import uuid
from playwright.sync_api import sync_playwright, expect
from comun import APP, api, contexto, login, shot, abrir_navegador, terminar


caja = api("/login", {"usuario": "caja.esquina", "password": "demo1234"})["token"]
admin = api("/login", {"usuario": "admin.esquina", "password": "demo1234"})["token"]
cocina = api("/login", {"usuario": "cocina.esquina", "password": "demo1234"})
externa = next(m for m in api("/mesa/list", {"incluir_externa": True}, caja) if m["tipo"] == "externa")
papas = next(p["id"] for p in api("/producto/list", {"todos": True}, admin) if p["nombre"] == "Papas a la francesa")
punto = next(p for p in cocina["puntos"] if p["nombre"] == "Cocina")


def celular():
    return "31" + str(uuid.uuid4().int)[:8]


def pedir(nombre, telefono, **extra):
    return api("/orden/create", {"mesa_id": externa["id"], "clave_idempotencia": uuid.uuid4().hex, "cliente_nombre": nombre,
                                 "cliente_telefono": telefono, "items": [{"producto_id": papas, "cantidad": 1}], **extra}, caja)


def despachar(orden):
    tarjeta = next(c for c in api("/cocina/comandas", {"punto_produccion_id": punto["id"]}, cocina["token"])["en_proceso"]
                   if c["orden_id"] == orden["id"])
    api("/cocina/abrir", {"comanda_id": tarjeta["id"]}, cocina["token"])
    api("/cocina/despachar", {"comanda_id": tarjeta["id"]}, cocina["token"])


with sync_playwright() as p:
    browser = abrir_navegador(p)

    # Mostrador: la orden queda lista y aparece el aviso para enviar con un toque
    telefono = celular()
    orden = pedir("Camila Rojas", telefono)
    page = contexto(browser, 1280, 860)
    page.context.route("https://wa.me/**", lambda ruta: ruta.abort())
    login(page, "caja.esquina")
    page.goto(f"{APP}/mostrador")
    despachar(orden)
    expect(page.get_by_role("tab", name="Pedidos")).to_contain_text("por avisar", timeout=20000)
    page.get_by_role("tab", name="Pedidos").click()
    avisos = page.locator("section.avisos")
    expect(avisos).to_contain_text("Camila Rojas")
    expect(avisos).to_contain_text("está lista para recoger")
    shot(page, "w01-mostrador-avisar")
    enlace = avisos.get_by_role("link", name="Enviar por WhatsApp")
    assert enlace.get_attribute("href").startswith(f"https://wa.me/57{telefono}?text=Hola%20Camila")
    with page.context.expect_page():
        enlace.click()
    expect(page.locator("section.avisos")).to_have_count(0)
    enviada = next(a for a in api("/notificacion/list", {}, admin) if a["orden_id"] == orden["id"])
    assert enviada["estado"] == "enviada", enviada
    page.context.close()

    # Domicilio en camino: el aviso aparece en la pantalla de domicilios
    centro = next(z for z in api("/domicilio/zona/list", {}, caja) if z["nombre"] == "Centro")
    domicilio = pedir("Mateo Díaz", celular(), entrega={"zona_envio_id": centro["id"], "direccion": "Calle 9 # 8-7"})
    despachar(domicilio)
    entrega = next(e for e in api("/entrega/list", {}, caja)["activas"] if e["orden_id"] == domicilio["id"])
    d02 = next(d for d in api("/domicilio/domiciliario/list", {}, caja) if d["codigo"] == "D02")
    api("/entrega/asignar", {"entrega_id": entrega["id"], "domiciliario_id": d02["id"]}, caja)
    api("/entrega/salir", {"entrega_id": entrega["id"]}, caja)
    page = contexto(browser, 390, 844, mobile=True)
    login(page, "caja.esquina")
    page.goto(f"{APP}/entregas")
    expect(page.locator("section.avisos")).to_contain_text("ya va en camino")
    shot(page, "w02-domicilio-aviso-movil")
    page.context.close()

    # Configuración: confirmación activa, texto propio y envío automático con el simulador
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/avisos")
    shot(page, "w03-config-manual")
    page.get_by_text("Automático", exact=True).click()
    page.select_option("#av-cred", "aceptar")
    page.get_by_label("Confirmación de orden").check()
    page.fill("#pl-orden_recibida", "Hola {nombre}, recibimos tu orden {numero}. Te escribimos cuando esté lista.")
    expect(page.locator(".config")).to_contain_text("Hola Ana, recibimos tu orden #012")
    shot(page, "w04-config-automatico")
    page.get_by_role("button", name="Guardar", exact=True).click()
    expect(page.get_by_text("Avisos guardados.")).to_be_visible()

    automatica = pedir("Sara Gómez", celular())
    estado = None
    for _ in range(40):
        aviso = next((a for a in api("/notificacion/list", {}, admin) if a["orden_id"] == automatica["id"]), None)
        estado = aviso and aviso["estado"]
        if estado == "enviada":
            break
        time.sleep(0.5)
    assert estado == "enviada", estado
    page.get_by_role("tab", name="Historial").click()
    expect(page.locator("tbody")).to_contain_text("Confirmación de orden")
    shot(page, "w05-historial")
    page.context.close()

    browser.close()

# Deja la demo en modo manual, como viene por defecto
config = api("/notificacion/config/get", {}, admin)
api("/notificacion/config/save", {"modo": "manual", "proveedor": "simulado", "limite_diario": 5, "plantillas": {},
                                  "eventos": {e["codigo"]: e["codigo"] != "orden_recibida" for e in config["eventos"]}}, admin)
terminar()
