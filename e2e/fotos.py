"""Recorrido de fotos y alérgenos: el administrador sube una foto pesada de cámara a un producto nuevo y a uno existente,
se comprime, queda en la carpeta del restaurante y el cliente la ve en la carta con sus alérgenos."""
import uuid
from PIL import Image
from playwright.sync_api import sync_playwright, expect
from comun import APP, API, OUT, api, contexto, login, shot, abrir_navegador, terminar

marca = uuid.uuid4().hex[:4]
nuevo = f"Bandeja {marca}"
token = api("/login", {"usuario": "admin.esquina", "password": "demo1234"})["token"]
qr = next(q for q in api("/qr/list", {}, token) if q["mesa"] == "Terraza 1")["url"].rsplit("/", 1)[1]

# Como una foto de cámara: grande y sin zonas planas
pesada = OUT / "camara.jpg"
Image.effect_noise((4000, 3000), 35).convert("RGB").save(pesada, "JPEG", quality=92)
assert pesada.stat().st_size > 2_000_000

with sync_playwright() as p:
    browser = abrir_navegador(p)
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/productos")

    # Producto nuevo con foto y alérgenos
    page.get_by_role("button", name="Crear producto").click()
    dialogo = page.get_by_role("dialog")
    dialogo.locator("#p-nombre").fill(nuevo)
    dialogo.locator("#p-precio").fill("32000")
    dialogo.locator("#p-alergenos").fill("Huevo, lácteos")
    dialogo.get_by_label("Foto del producto").set_input_files(pesada)
    expect(dialogo.locator(".foto-vista")).to_be_visible()
    shot(page, "f01-formulario")
    dialogo.get_by_role("button", name="Guardar").click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    fila = page.get_by_role("row", name=nuevo)
    expect(fila.locator("img")).to_be_visible()
    shot(page, "f02-lista")

    producto = next(x for x in api("/producto/list", {"todos": True}, token) if x["nombre"] == nuevo)
    assert producto["imagen"].startswith("restaurantes/") and "la-esquina-centro/productos/" in producto["imagen"], producto["imagen"]
    respuesta = page.request.get(f"{API}/media/{producto['imagen']}")
    assert respuesta.ok and respuesta.headers["content-type"] == "image/webp"
    peso = len(respuesta.body())
    print(f"foto de {pesada.stat().st_size // 1024} KB guardada en {peso // 1024} KB")
    assert peso < 700_000

    # Un archivo que no es imagen no entra
    falso = OUT / "falso.txt"
    falso.write_text("hola")
    fila.get_by_role("button", name="Editar").click()
    dialogo.get_by_label("Foto del producto").set_input_files(falso)
    expect(dialogo.get_by_role("alert")).to_contain_text("JPG, PNG o WebP")
    dialogo.get_by_role("button", name="Cancelar").click()
    page.context.close()

    # El cliente la ve en la carta
    cel = contexto(browser, 390, 844, mobile=True)
    cel.goto(f"{APP}/q/{qr}")
    tarjeta = cel.locator(".producto", has_text=nuevo)
    tarjeta.scroll_into_view_if_needed()
    expect(tarjeta.locator("img.foto")).to_be_visible()
    expect(tarjeta).to_contain_text("Contiene: Huevo, lácteos")
    cel.wait_for_function("document.querySelector('img.foto') && [...document.querySelectorAll('img.foto')].every(i => i.complete && i.naturalWidth > 0)")
    shot(cel, "f03-carta")
    browser.close()

terminar()
