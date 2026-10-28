"""Recorrido de propinas y liquidaciones: propinas de mesas y de un domicilio, borrador con horas y ajuste, aprobación,
pago con comprobante, liquidación de domiciliarios, reglas y la vista propia del mesero."""
import uuid
from playwright.sync_api import sync_playwright, expect
from comun import APP, api, contexto, login, shot, abrir_navegador, terminar


mesero = api("/login", {"usuario": "mesero.terraza", "password": "demo1234"})["token"]
caja = api("/login", {"usuario": "caja.esquina", "password": "demo1234"})["token"]
admin = api("/login", {"usuario": "admin.esquina", "password": "demo1234"})["token"]
cocina_sesion = api("/login", {"usuario": "cocina.esquina", "password": "demo1234"})
domi = api("/login", {"usuario": "domi.esquina", "password": "demo1234"})["token"]
if not api("/caja/estado", {}, caja)["turno"]:
    api("/caja/turno/abrir", {"fondo_inicial": 100000}, caja)
productos = {p["nombre"]: p["id"] for p in api("/producto/list", {"todos": True}, admin)}
mesas = {m["nombre"]: m for m in api("/mesa/list", {"incluir_externa": True}, caja)}
efectivo = next(m["id"] for m in api("/caja/estado", {}, caja)["medios"] if m["nombre"] == "Efectivo")


def cobrar(cuenta, propina):
    cuenta = api("/cuenta/ajustar", {"cuenta_id": cuenta["id"], "propina": propina}, caja)
    api("/cuenta/pagar", {"cuenta_id": cuenta["id"], "clave_idempotencia": uuid.uuid4().hex,
                          "pagos": [{"medio_pago_id": efectivo, "monto": cuenta["saldo"]}]}, caja)


for mesa, propina in (("Terraza 1", 3000), ("Terraza 2", 2000)):
    api("/orden/create", {"mesa_id": mesas[mesa]["id"], "clave_idempotencia": uuid.uuid4().hex, "items": [
        {"producto_id": productos["Papas a la francesa"], "cantidad": 2}]}, mesero)
    cobrar(api("/cuenta/abrir", {"mesa_id": mesas[mesa]["id"]}, caja), propina)

# Domicilio con propina entregado por D01
zona = next(z for z in api("/domicilio/zona/list", {}, caja) if z["nombre"] == "Centro")
orden = api("/orden/create", {"mesa_id": mesas["Para llevar"]["id"], "clave_idempotencia": uuid.uuid4().hex,
                              "cliente_nombre": "Laura Méndez", "cliente_telefono": "3125550000",
                              "items": [{"producto_id": productos["Papas a la francesa"], "cantidad": 1}],
                              "entrega": {"zona_envio_id": zona["id"], "direccion": "Calle 8 # 2-30", "barrio": "Centro"}}, caja)
cobrar(api("/cuenta/abrir", {"sesion_mesa_id": orden["sesion_mesa_id"]}, caja), 1000)
datos = api("/entrega/list", {}, caja)
entrega = next(e for e in datos["activas"] + datos["cerradas"] if e["orden_id"] == orden["id"])
d01 = next(d for d in api("/domicilio/domiciliario/list", {}, caja) if d["codigo"] == "D01")
api("/entrega/asignar", {"entrega_id": entrega["id"], "domiciliario_id": d01["id"]}, caja)
punto = next(p for p in cocina_sesion["puntos"] if p["nombre"] == "Cocina")["id"]
tarjeta = next(t for t in api("/cocina/comandas", {"punto_produccion_id": punto}, cocina_sesion["token"])["en_proceso"]
               if t["orden_id"] == orden["id"])
api("/cocina/abrir", {"comanda_id": tarjeta["id"]}, cocina_sesion["token"])
api("/cocina/despachar", {"comanda_id": tarjeta["id"]}, cocina_sesion["token"])
api("/entrega/salir", {"entrega_id": entrega["id"]}, domi)
api("/entrega/entregar", {"entrega_id": entrega["id"]}, domi)

with sync_playwright() as p:
    browser = abrir_navegador(p)

    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/liquidaciones")
    expect(page.locator(".resumen")).to_contain_text("Propinas")
    expect(page.locator(".aviso").first).to_contain_text("sin repartir")
    shot(page, "l01-periodo-abierto")

    page.get_by_role("button", name="Calcular liquidación").click()
    expect(page.get_by_text("Calculada").first).to_be_visible()
    for i in range(page.locator("input.horas").count()):
        campo = page.locator("input.horas").nth(i)
        campo.fill(str(8 - i))
        campo.press("Tab")
        page.wait_for_timeout(600)
    expect(page.locator(".aviso")).to_have_count(0)
    fila = page.locator("tr", has_text="Ana Mesera")
    fila.get_by_role("button", name="Ajuste").click()
    page.fill("#aj-valor", "2000")
    page.fill("#aj-motivo", "Cubrió turno doble el sábado")
    page.get_by_role("dialog").get_by_role("button", name="Guardar").click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    shot(page, "l02-borrador-con-horas")

    page.get_by_role("button", name="Aprobar").click()
    expect(page.locator(".cabeza-periodo")).to_contain_text("Aprobada")
    page.locator("tr", has_text="Ana Mesera").get_by_role("button", name="Pagar").click()
    page.select_option("#pg-medio", "transferencia")
    page.fill("#pg-ref", "NEQUI-4471")
    page.get_by_role("button", name="Registrar e imprimir").click()
    expect(page.locator("tr", has_text="Ana Mesera")).to_contain_text("Pagado")
    page.wait_for_function("window.__impreso === 1")
    shot(page, "l03-aprobada-y-pagada")

    page.get_by_role("tab", name="Domiciliarios").click()
    expect(page.locator("tbody").first).to_contain_text("D01", timeout=10000)
    page.get_by_role("button", name="Calcular liquidación").click()
    page.get_by_role("button", name="Aprobar").click()
    expect(page.locator(".cabeza-periodo")).to_contain_text("Aprobada")
    shot(page, "l04-domiciliarios")

    page.get_by_role("tab", name="Reglas").click()
    expect(page.locator(".reglas")).to_contain_text("abogado laboral")
    shot(page, "l05-reglas")
    page.context.close()

    page = contexto(browser, 390, 844, mobile=True)
    login(page, "mesero.terraza")
    page.goto(f"{APP}/mis-liquidaciones")
    expect(page.locator(".liquidacion")).to_contain_text("Pagado en transferencia")
    shot(page, "l06-mis-liquidaciones")
    page.context.close()

    browser.close()

terminar()
