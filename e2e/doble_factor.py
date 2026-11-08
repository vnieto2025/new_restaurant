"""Recorrido de la verificación en dos pasos: el administrador la activa desde Mi cuenta escaneando (aquí, leyendo)
la clave, guarda sus códigos de respaldo y vuelve a entrar con código; el dueño la ve en Personal y la exige a los
administradores, y él mismo queda llevado a activarla."""
import base64
import hashlib
import hmac
import struct
import time
from playwright.sync_api import sync_playwright, expect
from comun import APP, contexto, login, shot, abrir_navegador, terminar


def codigo(secreto, desplazamiento=0):
    """ Lo mismo que calcula la aplicación del celular (RFC 6238) """
    secreto = secreto.replace(" ", "")
    llave = base64.b32decode(secreto + "=" * (-len(secreto) % 8))
    resumen = hmac.new(llave, struct.pack(">Q", int(time.time() // 30) + desplazamiento), hashlib.sha1).digest()
    desfase = resumen[-1] & 0x0F
    return str((struct.unpack(">I", resumen[desfase:desfase + 4])[0] & 0x7FFFFFFF) % 1_000_000).zfill(6)


with sync_playwright() as p:
    browser = abrir_navegador(p)

    # El administrador ve la recomendación en Hoy y la activa
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin")
    page.get_by_role("status").filter(has_text="Protege tu cuenta").get_by_role("link", name="Activarla").click()
    page.wait_for_url("**/cuenta")
    page.get_by_label("Para empezar, escribe tu clave").fill("demo1234")
    page.get_by_role("button", name="Activar verificación").click()
    expect(page.locator(".qr svg")).to_be_visible()
    secreto = page.locator("code.secreto").inner_text()
    shot(page, "v01-qr")
    page.get_by_label("Escribe el código de 6 números").fill(codigo(secreto))
    page.get_by_role("button", name="Activar", exact=True).click()
    expect(page.get_by_role("heading", name="Guarda tus códigos de respaldo")).to_be_visible()
    expect(page.locator(".codigos li")).to_have_count(10)
    shot(page, "v02-respaldo")
    page.get_by_role("button", name="Ya los guardé").click()
    expect(page.get_by_text("te quedan 10 códigos de respaldo")).to_be_visible()
    page.context.close()

    # Vuelve a entrar: la clave sola ya no alcanza
    page = contexto(browser, 1366, 900)
    page.goto(f"{APP}/login")
    page.fill("#usuario", "admin.esquina")
    page.fill("#password", "demo1234")
    page.click("button[type=submit]")
    expect(page.get_by_label("Código de verificación")).to_be_visible()
    shot(page, "v03-pide-codigo")
    page.get_by_label("Código de verificación").fill("000000")
    page.get_by_role("button", name="Verificar").click()
    expect(page.get_by_role("alert")).to_contain_text("no es correcto")
    page.get_by_label("Código de verificación").fill(codigo(secreto, 1))
    page.get_by_role("button", name="Verificar").click()
    page.wait_for_url(lambda url: "/login" not in url)
    page.context.close()

    # El dueño la ve en Personal y la exige a los administradores
    page = contexto(browser, 1366, 900)
    login(page, "esquina")
    page.goto(f"{APP}/admin/usuarios")
    expect(page.get_by_role("row", name="admin.esquina")).to_contain_text("Activa")
    page.get_by_label("Exigirla a los administradores de la empresa y de los restaurantes").check()
    expect(page.get_by_text("Los administradores deberán activarla para usar el sistema.")).to_be_visible()
    # Él tampoco la tiene: queda llevado a activarla, sin acceso a lo demás
    page.wait_for_url("**/cuenta")
    expect(page.get_by_role("alert")).to_contain_text("Tu empresa exige la verificación en dos pasos")
    shot(page, "v04-exigida")
    page.goto(f"{APP}/admin/productos")
    page.wait_for_url("**/cuenta")
    browser.close()

terminar(esperados=("status of 400", "status of 403"))
