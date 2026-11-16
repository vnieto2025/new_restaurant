"""Recorrido de las vistas de la carta (como en el explorador de archivos): cuadrícula, lista, fotos medianas y fotos
grandes en la venta directa de la caja y en la mesa del mesero. Cada equipo recuerda la vista elegida."""
import base64
import io
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright, expect
from comun import APP, api, contexto, login, shot, abrir_navegador, terminar

admin = api("/login", {"usuario": "admin.esquina", "password": "demo1234"})["token"]
productos = {p["nombre"]: p["id"] for p in api("/producto/list", {}, admin)}
mesa = next(m for m in api("/mesa/list", {}, admin) if m["nombre"] == "Mesa 5")


def foto(color, ancho, alto):
    lienzo = Image.new("RGB", (ancho, alto), color)
    ImageDraw.Draw(lienzo).ellipse((ancho // 2 - 100, alto // 2 - 100, ancho // 2 + 100, alto // 2 + 100), fill="white")
    salida = io.BytesIO()
    lienzo.save(salida, "JPEG")
    return base64.b64encode(salida.getvalue()).decode()


# Dos productos con foto de formas distintas (horizontal y vertical); el resto sin foto, para ver la inicial
for nombre, color, ancho, alto in [("Hamburguesa clásica", "#b5651d", 900, 500), ("Hamburguesa doble", "#8b3a1a", 500, 900)]:
    api("/producto/imagen", {"producto_id": productos[nombre], "archivo": foto(color, ancho, alto)}, admin)

with sync_playwright() as p:
    browser = abrir_navegador(p)

    # Caja: venta directa en las cuatro vistas
    page = contexto(browser, 1280, 860)
    login(page, "caja.esquina")
    page.goto(f"{APP}/caja")
    page.get_by_role("tab", name="Venta directa").click()
    page.get_by_role("tab", name="Hamburguesas").click()
    vistas = page.get_by_role("group", name="Ver productos como")
    expect(vistas.get_by_role("button", name="Cuadrícula")).to_have_attribute("aria-pressed", "true")
    shot(page, "v01-cuadricula")

    vistas.get_by_role("button", name="Lista").click()
    expect(page.locator(".productos.vista-lista")).to_be_visible()
    expect(page.locator(".producto .foto")).to_have_count(0)
    shot(page, "v02-lista")

    vistas.get_by_role("button", name="Fotos medianas").click()
    expect(page.locator(".producto", has_text="Hamburguesa clásica").locator("img")).to_be_visible()
    expect(page.locator(".producto", has_text="Hamburguesa de pollo").locator(".inicial")).to_have_text("H")
    # Sin importar la forma de la foto, los marcos y las tarjetas quedan del mismo tamaño
    marcos = [page.locator(".producto", has_text=n).locator(".foto").bounding_box()["height"]
              for n in ("Hamburguesa clásica", "Hamburguesa doble", "Hamburguesa de pollo")]
    assert max(marcos) - min(marcos) < 1, marcos
    shot(page, "v03-medianas")

    vistas.get_by_role("button", name="Fotos grandes").click()
    shot(page, "v04-grandes")
    # Con fotos también se agrega con un toque
    page.locator(".producto", has_text="Hamburguesa clásica").click()
    page.get_by_role("dialog").get_by_role("button", name="Medio").click()
    page.get_by_role("dialog").get_by_role("button", name="Agregar").click()
    expect(page.locator(".cart .linea", has_text="Hamburguesa clásica")).to_be_visible()

    # Se recuerda en este equipo
    page.reload()
    page.get_by_role("tab", name="Venta directa").click()
    expect(page.get_by_role("group", name="Ver productos como").get_by_role("button", name="Fotos grandes")).to_have_attribute("aria-pressed", "true")
    page.context.close()

    # Mesero en el celular: fotos medianas
    page = contexto(browser, 390, 844, mobile=True)
    login(page, "mesero.salon")
    page.goto(f"{APP}/mesas/{mesa['id']}")
    page.get_by_role("tab", name="Hamburguesas").click()
    page.get_by_role("group", name="Ver productos como").get_by_role("button", name="Fotos medianas").click()
    expect(page.locator(".producto", has_text="Hamburguesa doble").locator("img")).to_be_visible()
    shot(page, "v05-mesero-celular")
    browser.close()

terminar()
