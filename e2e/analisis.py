"""Recorrido de los reportes de la fase 2: con ventas y comandas despachadas, el administrador ve horas pico, tiempos,
clientes e inventario; también en celular y con el contador, que no ve nombres de clientes."""
import uuid
from playwright.sync_api import sync_playwright, expect
from comun import APP, api, contexto, login, shot, abrir_navegador, terminar

admin = api("/login", {"usuario": "admin.esquina", "password": "demo1234"})["token"]
caja = api("/login", {"usuario": "caja.esquina", "password": "demo1234"})["token"]
cocina = api("/login", {"usuario": "cocina.esquina", "password": "demo1234"})
if not api("/caja/estado", {}, caja)["turno"]:
    api("/caja/turno/abrir", {"fondo_inicial": 100000}, caja)
efectivo = next(m["id"] for m in api("/caja/estado", {}, caja)["medios"] if m["nombre"] == "Efectivo")
producto = next(p["id"] for p in api("/producto/list", {"todos": True}, admin) if p["nombre"] == "Papas a la francesa")
externa = next(m["id"] for m in api("/mesa/list", {"incluir_externa": True}, caja) if m["tipo"] == "externa")
punto = next(p["id"] for p in cocina["puntos"] if p["nombre"] == "Cocina")
cliente = f"Clienta {uuid.uuid4().hex[:4]}"
telefono = "3" + str(uuid.uuid4().int)[:9]

for _ in range(2):
    orden = api("/orden/create", {"mesa_id": externa, "clave_idempotencia": uuid.uuid4().hex, "cliente_nombre": cliente,
                                  "cliente_telefono": telefono, "acepta_datos": True,
                                  "items": [{"producto_id": producto, "cantidad": 2}]}, caja)
    tarjeta = next(c for c in api("/cocina/comandas", {"punto_produccion_id": punto}, cocina["token"])["en_proceso"] if c["orden_id"] == orden["id"])
    api("/cocina/abrir", {"comanda_id": tarjeta["id"]}, cocina["token"])
    api("/cocina/despachar", {"comanda_id": tarjeta["id"]}, cocina["token"])
    cuenta = api("/cuenta/abrir", {"sesion_mesa_id": orden["sesion_mesa_id"]}, caja)
    api("/cuenta/pagar", {"cuenta_id": cuenta["id"], "clave_idempotencia": uuid.uuid4().hex,
                          "pagos": [{"medio_pago_id": efectivo, "monto": cuenta["saldo"]}]}, caja)

with sync_playwright() as p:
    browser = abrir_navegador(p)
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/reportes")
    expect(page.get_by_role("heading", name="Horas pico")).to_be_visible()
    expect(page.get_by_text("Lo más fuerte:")).to_be_visible()
    expect(page.locator(".calor td[title*='cuentas']").first).to_be_visible()
    page.get_by_role("heading", name="Horas pico").scroll_into_view_if_needed()
    shot(page, "a01-horas-pico")
    expect(page.get_by_role("heading", name="Tiempos de preparación")).to_be_visible()
    expect(page.locator("section", has_text="Tiempos de preparación").get_by_role("cell", name="Cocina")).to_be_visible()
    page.get_by_role("heading", name="Tiempos de preparación").scroll_into_view_if_needed()
    shot(page, "a02-tiempos")
    expect(page.get_by_text(cliente)).to_be_visible()
    page.get_by_role("heading", name="Clientes", exact=True).scroll_into_view_if_needed()
    shot(page, "a03-clientes")
    page.get_by_role("heading", name="Inventario", exact=True).scroll_into_view_if_needed()
    expect(page.get_by_text("En el mínimo o por debajo")).to_be_visible()
    shot(page, "a04-inventario")
    page.context.close()

    page = contexto(browser, 1366, 900)
    login(page, "contador.esquina")
    page.goto(f"{APP}/admin/reportes")
    expect(page.get_by_role("heading", name="Clientes", exact=True)).to_be_visible()
    expect(page.get_by_text(cliente)).to_have_count(0)
    page.context.close()

    page = contexto(browser, 390, 844, mobile=True)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/reportes")
    page.get_by_role("heading", name="Horas pico").scroll_into_view_if_needed()
    expect(page.get_by_role("heading", name="Horas pico")).to_be_visible()
    shot(page, "a05-celular")

    browser.close()

terminar()
