"""Recorrido del logo y las billeteras: el administrador sube el logo (un logo vertical se rechaza con el tamaño sugerido)
y agrega Nequi con su QR; el logo sale en el menú y en el seguimiento del cliente; las billeteras salen en el seguimiento,
en el cobro de la caja, en el mostrador y en la precuenta impresa. Soporte también puede subir el logo."""
import uuid
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright, expect
from comun import APP, OUT, api, contexto, login, shot, abrir_navegador, terminar


def png(nombre, ancho, alto, texto):
    lienzo = Image.new("RGB", (ancho, alto), "white")
    dibujo = ImageDraw.Draw(lienzo)
    dibujo.rectangle((10, 10, ancho - 10, alto - 10), outline="#5a2a4d", width=8)
    dibujo.text((30, alto // 2 - 10), texto, fill="#5a2a4d")
    ruta = OUT / nombre
    lienzo.save(ruta)
    return str(ruta)


LOGO = png("logo.png", 1200, 400, "LA ESQUINA")
VERTICAL = png("vertical.png", 400, 600, "VERTICAL")
QR = png("qr.png", 500, 500, "QR NEQUI")

caja_token = api("/login", {"usuario": "caja.esquina", "password": "demo1234"})["token"]
admin = api("/login", {"usuario": "admin.esquina", "password": "demo1234"})["token"]
token_rapido = next(q for q in api("/qr/list", {}, admin) if q["tipo"] == "rapido")["url"].rsplit("/", 1)[1]

with sync_playwright() as p:
    browser = abrir_navegador(p)

    # Administrador: logo y billetera
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/restaurante")
    expect(page.get_by_text("Tamaño sugerido: 600 × 200 px")).to_be_visible()
    page.locator(".logo-editor input[type=file]").set_input_files(VERTICAL)
    expect(page.get_by_role("alert")).to_contain_text("debe ser horizontal")
    page.locator(".logo-editor input[type=file]").set_input_files(LOGO)
    expect(page.get_by_text("Logo guardado.")).to_be_visible()
    expect(page.locator(".logo-editor .marco img")).to_be_visible()
    page.get_by_role("button", name="Agregar billetera").click()
    dialogo = page.get_by_role("dialog")
    dialogo.get_by_label("Nombre", exact=True).fill("Nequi")
    dialogo.get_by_label("Teléfono de la billetera").fill("300 123 4567")
    dialogo.get_by_label("A nombre de").fill("La Esquina SAS")
    dialogo.locator("input[type=file]").set_input_files(QR)
    shot(page, "b01-billetera-form")
    dialogo.get_by_role("button", name="Guardar").click()
    expect(page.get_by_text("Billetera guardada.")).to_be_visible()
    page.locator(".billeteras-editor").scroll_into_view_if_needed()
    shot(page, "b02-configuracion")
    # El logo sale en el menú de administración
    page.goto(f"{APP}/admin")
    expect(page.locator(".menu .logo")).to_be_visible()
    page.context.close()

    # Cliente: pide para llevar y en el seguimiento ve el logo y cómo pagar por billetera
    productos = {pr["nombre"]: pr["id"] for c in api("/publico/qr", {"token": token_rapido})["categorias"] for pr in c["productos"]}
    pedido = api("/publico/orden/create", {"token": token_rapido, "clave_idempotencia": uuid.uuid4().hex, "cliente_nombre": "Cliente billetera",
                                           "items": [{"producto_id": productos["Gaseosa 400 ml"], "cantidad": 1}]})
    cel = contexto(browser, 390, 844, mobile=True)
    cel.goto(f"{APP}/pedido/{pedido['seguimiento']}")
    expect(cel.locator(".cabecera .logo")).to_be_visible()
    billeteras = cel.get_by_role("region", name="También puedes pagar por billetera")
    expect(billeteras).to_contain_text("Nequi")
    expect(billeteras).to_contain_text("300 123 4567")
    expect(billeteras.get_by_role("img", name="Código QR de Nequi")).to_be_visible()
    shot(cel, "b03-seguimiento")
    cel.context.close()

    # Caja: el cobro muestra las billeteras y la precuenta las imprime
    api("/caja/turno/abrir", {"fondo_inicial": 100000}, caja_token)
    page = contexto(browser, 1280, 860)
    login(page, "caja.esquina")
    page.goto(f"{APP}/caja")
    page.get_by_role("tab", name="Por cobrar").click()
    page.get_by_role("button", name="Cliente billetera").first.click()
    page.get_by_role("button", name="Billeteras").click()
    expect(page.get_by_role("dialog")).to_contain_text("300 123 4567")
    shot(page, "b04-caja-billeteras")
    page.get_by_role("dialog").get_by_role("button", name="Cerrar").click()
    page.get_by_role("button", name="Imprimir precuenta").click()
    tirilla = page.locator(".print-root")
    expect(tirilla).to_contain_text("También puedes pagar por billetera")
    expect(tirilla).to_contain_text("Nequi")
    expect(tirilla.locator("img.logo")).to_have_count(1)
    page.emulate_media(media="print")
    tirilla.screenshot(path=str(OUT / "b05-precuenta.png"))
    page.context.close()

    # Mostrador: botón para mostrárselas al cliente
    page = contexto(browser, 1280, 860)
    login(page, "caja.esquina")
    page.goto(f"{APP}/mostrador")
    page.get_by_role("button", name="Billeteras").click()
    expect(page.get_by_role("dialog")).to_contain_text("Nequi")
    page.context.close()

    # Soporte: también puede subir el logo de un restaurante
    page = contexto(browser, 1366, 900)
    login(page, "soporte", "Soporte12345")
    page.get_by_role("row", name="Napoli Norte").get_by_role("button", name="Logo").click()
    page.get_by_role("dialog").locator("input[type=file]").set_input_files(LOGO)
    expect(page.get_by_text("Logo guardado.")).to_be_visible()
    shot(page, "b06-soporte-logo")
    browser.close()

terminar(esperados=("status of 400",))
