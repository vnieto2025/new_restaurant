"""Recorrido de clientes: mostrador reconoce por celular, carta QR con aviso, ficha en administración."""
import sys
import time
from playwright.sync_api import sync_playwright, expect
from comun import APP, contexto, login, shot, abrir_navegador, terminar

# Reutiliza los ayudantes de e2e.py sin ejecutar su recorrido

telefono = f"31{int(time.time()) % 100000000:08d}"

with sync_playwright() as p:
    browser = abrir_navegador(p)

    # Mostrador: cliente nuevo con autorización
    page = contexto(browser, 1280, 800)
    login(page, "caja.esquina")
    page.goto(f"{APP}/mostrador")
    page.get_by_text("Bebidas", exact=True).click()
    page.get_by_role("button", name="Limonada natural").first.click()
    page.fill("#cap-tel", telefono)
    page.fill("#cap-nombre", "Cliente Prueba")
    page.get_by_text("acepta que lo registremos").click()
    shot(page, "c01-mostrador-nuevo")
    page.get_by_role("button", name="Enviar a cocina").click()
    page.wait_for_timeout(1200)

    # Segunda orden: lo reconoce
    page.get_by_text("Bebidas", exact=True).click()
    page.get_by_role("button", name="Limonada natural").first.click()
    page.fill("#cap-tel", telefono)
    expect(page.locator(".reconocido")).to_contain_text("Cliente Prueba", timeout=4000)
    expect(page.locator("#cap-nombre")).to_have_value("Cliente Prueba")
    shot(page, "c02-mostrador-reconoce")
    page.context.close()

    # Administración: ficha del cliente
    page = contexto(browser, 1280, 800)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/clientes")
    page.fill("input[type=search]", telefono)
    page.get_by_role("button", name="Buscar").click()
    page.get_by_role("button", name="Ver ficha").first.click()
    expect(page.get_by_role("dialog")).to_contain_text("Limonada natural")
    shot(page, "c03-ficha")
    page.get_by_role("button", name="Agregar dirección").click()
    page.fill("#d-dir", "Calle 10 # 5-20")
    page.fill("#d-barrio", "Centro")
    page.get_by_role("dialog").last.get_by_role("button", name="Guardar").click()
    expect(page.get_by_role("dialog").first).to_contain_text("Calle 10 # 5-20")
    page.context.close()

    # Restaurante: aviso de datos
    page = contexto(browser, 1280, 800)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/restaurante")
    expect(page.locator("#r-aviso")).to_be_visible()
    shot(page, "c04-config-aviso")
    page.context.close()

    # Celular: lista de clientes
    page = contexto(browser, 390, 844, mobile=True)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/clientes")
    shot(page, "c05-clientes-movil")
    page.context.close()

    browser.close()

terminar()
