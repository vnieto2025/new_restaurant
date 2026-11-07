"""Recorrido de combos: el administrador revisa un combo; el mesero lo pide en la tablet eligiendo bebida y término;
cocina ve de qué combo es cada parte; caja cobra una sola línea; el cliente lo arma desde la carta del celular."""
import uuid
from playwright.sync_api import sync_playwright, expect
from comun import APP, api, contexto, login, shot, abrir_navegador, terminar

COMBO = "Combo clásico"
admin = api("/login", {"usuario": "admin.esquina", "password": "demo1234"})["token"]
mesa = next(m for m in api("/mesa/list", {}, admin) if m["nombre"] == "Terraza 2")
qr = next(q for q in api("/qr/list", {}, admin) if q["mesa"] == "Terraza 1")["url"].rsplit("/", 1)[1]
cliente = f"Combo {uuid.uuid4().hex[:4]}"

with sync_playwright() as p:
    browser = abrir_navegador(p)

    # Administración: el combo con sus partes
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/productos")
    fila = page.get_by_role("row", name=COMBO)
    expect(fila).to_contain_text("Combo")
    fila.get_by_role("button", name="Editar").click()
    dialogo = page.get_by_role("dialog")
    expect(dialogo.get_by_label("Tipo")).to_have_value("combo")
    expect(dialogo.get_by_text("Qué trae el combo")).to_be_visible()
    dialogo.get_by_text("Qué trae el combo").scroll_into_view_if_needed()
    shot(page, "k01-editor")
    dialogo.get_by_role("button", name="Cancelar").click()
    page.context.close()

    # Tablet del mesero: arma el combo
    page = contexto(browser, 1180, 820)
    login(page, "mesero.terraza")
    page.goto(f"{APP}/mesas/{mesa['id']}")
    page.get_by_role("tab", name="Combos").click()
    page.get_by_role("button", name=COMBO).click()
    dialogo = page.get_by_role("dialog")
    expect(dialogo.get_by_role("button", name="Falta: término de la carne de hamburguesa clásica")).to_be_disabled()
    dialogo.get_by_role("group", name="Término de la carne de Hamburguesa clásica").get_by_role("button", name="Tres cuartos").click()
    expect(dialogo.get_by_role("button", name="Falta: bebida")).to_be_disabled()
    dialogo.get_by_role("button", name="Limonada natural").click()
    expect(dialogo.get_by_role("button", name="Agregar · $ 27.500")).to_be_enabled()
    shot(page, "k02-armar-combo")
    dialogo.get_by_role("button", name="Agregar · $ 27.500").click()
    expect(page.get_by_text("Limonada natural")).to_be_visible()
    page.get_by_role("button", name="Enviar a cocina").click()
    page.get_by_role("tab", name="En la mesa").click()
    expect(page.get_by_text("↳ 1 × Papas a la francesa")).to_be_visible()
    shot(page, "k03-en-la-mesa")
    page.context.close()

    # Cocina: cada parte dice de qué combo es
    page = contexto(browser, 1280, 800)
    login(page, "cocina.esquina")
    punto = next(x["id"] for x in api("/login", {"usuario": "cocina.esquina", "password": "demo1234"})["puntos"] if x["nombre"] == "Cocina")
    page.goto(f"{APP}/produccion/{punto}")
    tarjeta = page.locator("article", has_text="Terraza 2").first
    expect(tarjeta).to_contain_text("Del Combo clásico")
    expect(tarjeta).to_contain_text("Hamburguesa clásica")
    shot(page, "k04-cocina")
    page.context.close()

    # Caja: una sola línea con su detalle
    page = contexto(browser, 1280, 860)
    login(page, "caja.esquina")
    page.goto(f"{APP}/caja")
    if page.get_by_label("Base en efectivo").count():
        page.get_by_label("Base en efectivo").fill("100000")
        page.get_by_role("button", name="Abrir turno").click()
    page.get_by_role("button", name="Terraza 2").first.click()
    cobro = page.locator(".cobro")
    expect(cobro).to_contain_text(COMBO)
    expect(cobro).to_contain_text("Papas a la francesa")
    expect(cobro.get_by_text("$ 27.500").first).to_be_visible()
    shot(page, "k05-caja")
    page.context.close()

    # Cliente en la carta del celular
    cel = contexto(browser, 390, 844, mobile=True)
    cel.goto(f"{APP}/q/{qr}")
    cel.get_by_role("button", name="Combos").click()
    cel.get_by_label(f"Agregar {COMBO}").click()
    dialogo = cel.get_by_role("dialog")
    dialogo.get_by_role("button", name="Gaseosa 400 ml").click()
    dialogo.get_by_role("group", name="Término de la carne de Hamburguesa clásica").get_by_role("button", name="Medio").click()
    shot(cel, "k06-carta-combo")
    dialogo.get_by_role("button", name="Agregar · $ 26.000").click()
    cel.get_by_text("Ver pedido (1)").click()
    expect(cel.locator(".lineas")).to_contain_text("Gaseosa 400 ml")
    cel.get_by_role("button", name="Enviar pedido").click()
    cel.wait_for_url("**/pedido/**")
    expect(cel.get_by_text(COMBO)).to_be_visible()
    shot(cel, "k07-seguimiento")
    browser.close()

terminar()
