"""Recorrido del asistente de configuración inicial: una empresa recién creada ve el aviso, avanza por los pasos (crea
mesas e importa la carta desde ahí mismo), el ensayo se habilita al final y, al confirmarlo, el aviso desaparece."""
import uuid
from openpyxl import Workbook
from playwright.sync_api import sync_playwright, expect
from comun import APP, OUT, api, contexto, login, shot, abrir_navegador, terminar

marca = uuid.uuid4().hex[:6]
usuario = f"dueno.{marca}"
soporte = api("/login", {"usuario": "soporte", "password": "Soporte12345"})["token"]
api("/plataforma/empresa/create", {
    "nombre_comercial": f"Fonda {marca}", "modulos": ["pedidos", "caja"], "estado_contrato": "activo",
    "admin": {"usuario": usuario, "nombre": "Dueña Fonda", "password": "clave12345"},
    "restaurante": {"nombre": f"Fonda {marca}"}}, soporte)

libro = Workbook()
libro.active.append(["Producto", "Categoría", "Precio"])
libro.active.append(["Bandeja paisa", "Platos fuertes", 32000])
carta = OUT / "carta.xlsx"
libro.save(carta)

with sync_playwright() as p:
    browser = abrir_navegador(p)
    page = contexto(browser, 1366, 900)
    login(page, usuario, "clave12345")

    # El aviso lleva al asistente
    page.goto(f"{APP}/admin")
    page.locator(".aviso-marcha").get_by_role("link", name="Continuar").click()
    expect(page.get_by_role("heading", name="Puesta en marcha")).to_be_visible()
    pasos = page.locator(".paso")
    expect(pasos.filter(has_text="Cocina y bar")).to_contain_text("Hecho")
    expect(page.get_by_role("button", name="Ya hicimos el ensayo")).to_be_disabled()
    shot(page, "m01-asistente")

    # Datos: por su pantalla normal
    pasos.filter(has_text="Datos del restaurante").get_by_role("link", name="Abrir").click()
    page.fill("#r-dir", "Calle 45 # 12-30")
    page.fill("#r-tel", "3005556677")
    page.get_by_role("button", name="Guardar").first.click()
    expect(page.get_by_text("Configuración guardada")).to_be_visible()
    page.goto(f"{APP}/admin/puesta-en-marcha")

    # Mesas desde aquí mismo
    pasos.filter(has_text="Zonas y mesas").get_by_role("button", name="Crear mesas").click()
    dialogo = page.get_by_role("dialog")
    dialogo.locator("#lote-hasta").fill("6")
    expect(dialogo).to_contain_text("«Mesa 6»")
    shot(page, "m02-crear-mesas")
    dialogo.get_by_role("button", name="Crear", exact=True).click()
    expect(page.get_by_text("6 mesas en la zona")).to_be_visible()
    expect(pasos.filter(has_text="Zonas y mesas")).to_contain_text("Hecho")

    # Carta desde aquí mismo
    pasos.filter(has_text="Carta").get_by_role("button", name="Importar productos").click()
    dialogo.get_by_label("Archivo de productos").set_input_files(carta)
    dialogo.get_by_role("button", name="Importar 1 producto").click()
    expect(pasos.filter(has_text="Carta")).to_contain_text("Hecho")

    # Personal: creado por API, se refleja al volver
    token = api("/login", {"usuario": usuario, "password": "clave12345"})["token"]
    zona = next(z for z in api("/zona/list", {}, token) if z["nombre"] == "Salón")
    api("/usuario/create", {"usuario": f"mesero.{marca}", "nombre": "Mesero", "password": "clave12345", "roles": ["mesero"], "zonas": [zona["id"]]}, token)
    page.reload()
    expect(pasos.filter(has_text="Personal")).to_contain_text("Hecho")

    # QR: confirmación manual; con eso se habilita el ensayo
    pasos.filter(has_text="Códigos QR").get_by_role("button", name="Ya los imprimí").click()
    expect(pasos.filter(has_text="Códigos QR")).to_contain_text("Dueña Fonda")
    ensayo = page.get_by_role("button", name="Ya hicimos el ensayo")
    expect(ensayo).to_be_enabled()
    expect(page.get_by_text("mínimo un día antes")).to_be_visible()
    shot(page, "m03-listo-para-ensayo")
    ensayo.click()
    expect(page.get_by_text("¡Listo para abrir!")).to_be_visible()
    expect(page.locator(".aviso-marcha")).to_have_count(0)
    shot(page, "m04-listo")
    page.context.close()

    # El mesero no ve nada de esto; en celular se lee bien
    page = contexto(browser, 390, 844, mobile=True)
    login(page, f"mesero.{marca}", "clave12345")
    expect(page.locator(".aviso-marcha")).to_have_count(0)
    page.context.close()
    page = contexto(browser, 390, 844, mobile=True)
    login(page, "napoli")
    page.goto(f"{APP}/admin/puesta-en-marcha")
    expect(page.get_by_role("heading", name="Puesta en marcha")).to_be_visible()
    shot(page, "m05-celular")

    browser.close()

terminar()
