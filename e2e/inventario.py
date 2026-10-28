"""Recorrido de inventario: consumo al producir, existencias, entrada por presentación, recetas y márgenes,
merma y conteo desde la tablet de cocina."""
import uuid
from playwright.sync_api import sync_playwright, expect
from comun import APP, api, contexto, login, shot, abrir_navegador, terminar


caja = api("/login", {"usuario": "caja.esquina", "password": "demo1234"})["token"]
admin = api("/login", {"usuario": "admin.esquina", "password": "demo1234"})["token"]
cocina_sesion = api("/login", {"usuario": "cocina.esquina", "password": "demo1234"})
cocina = cocina_sesion["token"]

insumos = {i["nombre"]: i for i in api("/insumo/list", {}, admin)}
carne_antes = insumos["Carne de res molida"]["stock"]
productos = {p["nombre"]: p["id"] for p in api("/producto/list", {"todos": True}, admin)}
grupos = api("/modificador/list", {}, admin)
medio = next(o["id"] for g in grupos if g["nombre"] == "Término de la carne" for o in g["opciones"] if o["nombre"] == "Medio")
externa = next(m for m in api("/mesa/list", {"incluir_externa": True}, caja) if m["nombre"] == "Para llevar")
orden = api("/orden/create", {"mesa_id": externa["id"], "clave_idempotencia": uuid.uuid4().hex, "cliente_nombre": "Inventario",
                              "items": [{"producto_id": productos["Hamburguesa clásica"], "cantidad": 2, "modificadores": [medio]}]}, caja)
punto = next(p for p in cocina_sesion["puntos"] if p["nombre"] == "Cocina")
tarjeta = next(c for c in api("/cocina/comandas", {"punto_produccion_id": punto["id"]}, cocina)["en_proceso"] if c["orden_id"] == orden["id"])
api("/cocina/abrir", {"comanda_id": tarjeta["id"]}, cocina)
carne_despues = next(i for i in api("/insumo/list", {}, admin) if i["nombre"] == "Carne de res molida")["stock"]
assert carne_antes - carne_despues == 315, (carne_antes, carne_despues)

with sync_playwright() as p:
    browser = abrir_navegador(p)

    # Administración: existencias y entrada por presentación
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/inventario")
    expect(page.locator("tbody")).to_contain_text("Carne de res molida")
    shot(page, "i01-existencias")
    papa_antes = next(i for i in api("/insumo/list", {}, admin) if i["nombre"] == "Papa")["stock"]
    fila = page.locator("tr", has=page.get_by_text("Papa", exact=True))
    fila.get_by_role("button", name="Entrada").click()
    page.fill("#mv-cant", "1")
    page.select_option("#mv-pres", label="Bulto 25 kg")
    page.fill("#mv-costo", "80000")
    shot(page, "i02-entrada-bulto")
    page.get_by_role("dialog").get_by_role("button", name="Registrar").click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    papa = next(i for i in api("/insumo/list", {}, admin) if i["nombre"] == "Papa")
    assert papa["stock"] == papa_antes + 25000, (papa_antes, papa["stock"])
    page.get_by_role("tab", name="Movimientos").click()
    expect(page.locator("tbody")).to_contain_text("Consumo por venta")
    shot(page, "i03-movimientos")

    # Recetas y márgenes
    page.goto(f"{APP}/admin/recetas")
    expect(page.locator("tbody")).to_contain_text("Hamburguesa clásica")
    shot(page, "i04-costos")
    page.locator("tr", has=page.get_by_text("Hamburguesa clásica", exact=True)).get_by_role("button").click()
    expect(page.get_by_role("dialog")).to_contain_text("Margen")
    shot(page, "i05-receta")
    page.get_by_role("dialog").get_by_role("button", name="Cancelar").click()
    page.get_by_role("tab", name="Modificadores").click()
    expect(page.get_by_text("Queso extra", exact=True)).to_be_visible()
    shot(page, "i06-modificadores")
    page.context.close()

    # Tablet de cocina: entra directo a producción; inventario desde el menú
    page = contexto(browser, 1024, 768)
    login(page, "cocina.esquina")
    page.wait_for_url(lambda url: "/produccion" in url)
    tomate_antes = next(i for i in api("/insumo/list", {}, admin) if i["nombre"] == "Tomate")["stock"]
    page.goto(f"{APP}/bodega")
    page.get_by_role("button", name="Tomate").click()
    page.get_by_role("button", name="Se dañó").click()
    page.fill("#mv-cant", "200")
    shot(page, "i07-merma")
    page.get_by_role("dialog").get_by_role("button", name="Registrar").click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    tomate = next(i for i in api("/insumo/list", {}, admin) if i["nombre"] == "Tomate")["stock"]
    assert tomate == tomate_antes - 200, (tomate_antes, tomate)
    page.get_by_role("tab", name="Conteos").click()
    page.get_by_role("button", name="Nuevo conteo").click()
    page.select_option("#ct-cat", "Verduras")
    page.get_by_role("button", name="Empezar").click()
    page.get_by_label("Contado de Limón").fill("45")
    page.get_by_label("Nota de Limón").fill("Cinco dañados")
    page.get_by_role("button", name="Guardar").click()
    shot(page, "i08-conteo-cocina")
    expect(page.get_by_role("button", name="Aplicar al inventario")).to_have_count(0)
    page.context.close()

    # El administrador aplica el conteo
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/bodega?vista=conteos")
    page.get_by_role("button", name="Conteo de Verduras").click()
    page.get_by_role("button", name="Aplicar al inventario").click()
    expect(page.locator("main.contenido")).to_contain_text("Aplicado")
    shot(page, "i09-conteo-aplicado")
    page.context.close()

    # Celular
    page = contexto(browser, 390, 844, mobile=True)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/recetas")
    expect(page.locator("tbody")).to_contain_text("Hamburguesa")
    shot(page, "i10-recetas-movil")
    page.goto(f"{APP}/bodega")
    shot(page, "i11-bodega-movil")
    page.context.close()

    browser.close()

terminar()
