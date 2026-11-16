"""Recorrido de la cuenta sencilla en un restaurante sin caja (Pizzería Napoli): el mesero imprime para el cliente la
cuenta de la mesa con el IVA incluido y la propina sugerida; la cocina también la imprime desde la comanda."""
import uuid
from playwright.sync_api import sync_playwright, expect
from comun import APP, api, contexto, login, shot, abrir_navegador, terminar

duena = api("/login", {"usuario": "napoli", "password": "demo1234"})["token"]
if not api("/impuesto/list", {}, duena):
    api("/impuesto/create", {"nombre": "IVA", "tipo": "iva", "porcentaje": 19}, duena)
mesero = api("/login", {"usuario": "mesero.napoli", "password": "demo1234"})["token"]
mesa = next(m for m in api("/mesa/list", {}, mesero) if m["nombre"] == "Mesa 3")
pizzas = {p["nombre"]: p["id"] for p in api("/producto/list", {}, duena)}
api("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": uuid.uuid4().hex, "items": [
    {"producto_id": pizzas["Pizza margarita"], "cantidad": 2}, {"producto_id": pizzas["Pizza napolitana"], "cantidad": 1}]}, mesero)

with sync_playwright() as p:
    browser = abrir_navegador(p)

    # Mesero: imprime la cuenta de la mesa
    page = contexto(browser, 1180, 820)
    login(page, "mesero.napoli")
    page.goto(f"{APP}/mesas/{mesa['id']}")
    page.get_by_role("tab", name="En la mesa").click()
    page.get_by_role("button", name="Imprimir cuenta ($ 100.000)").click()
    tirilla = page.locator(".print-root")
    expect(tirilla).to_contain_text("Cuenta")
    expect(tirilla).to_contain_text("2 x Pizza margarita")
    expect(tirilla).to_contain_text("IVA 19 %")
    expect(tirilla).to_contain_text("Propina sugerida 10 %")
    expect(tirilla).to_contain_text("Total con propina sugerida")
    expect(tirilla).to_contain_text("Documento no válido como factura")
    page.wait_for_function("window.__impreso >= 1")
    shot(page, "c01-mesa")
    # Vista de impresión: lo que sale en papel
    page.emulate_media(media="print")
    tirilla.screenshot(path=str(__import__("comun").OUT / "c02-tirilla.png"))
    page.context.close()

    # Cocina: la misma cuenta desde la comanda
    page = contexto(browser, 1280, 800)
    login(page, "cocina.napoli")
    page.wait_for_url("**/produccion/**")
    tarjeta = page.locator("article", has_text="Mesa 3").first
    tarjeta.get_by_role("button", name="Cuenta").click()
    expect(page.locator(".print-root")).to_contain_text("IVA 19 %")
    page.wait_for_function("window.__impreso >= 1")
    shot(page, "c03-cocina")
    browser.close()

terminar()
