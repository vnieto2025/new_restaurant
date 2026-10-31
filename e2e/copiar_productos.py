"""Recorrido de duplicar y copiar: el administrador duplica un plato y ajusta la copia; el dueño de una cadena pasa una
categoría filtrada a su otra sede y la encuentra allá, y la opción no aparece para quien no administra la empresa."""
import uuid
from playwright.sync_api import sync_playwright, expect
from comun import APP, api, contexto, login, shot, abrir_navegador, terminar

marca = uuid.uuid4().hex[:6]
dueno = f"dueno.{marca}"
soporte = api("/login", {"usuario": "soporte", "password": "Soporte12345"})["token"]
empresa = api("/plataforma/empresa/create", {
    "nombre_comercial": f"Cadena {marca}", "modulos": ["pedidos"], "estado_contrato": "activo",
    "admin": {"usuario": dueno, "nombre": "Dueña", "password": "clave12345"}, "restaurante": {"nombre": f"Norte {marca}"}}, soporte)
api("/plataforma/restaurante/create", {"empresa_id": empresa["id"], "modulos": ["pedidos"], "estado_contrato": "activo",
                                       "restaurante": {"nombre": f"Sur {marca}"}}, soporte)
token = api("/login", {"usuario": dueno, "password": "clave12345"})["token"]
sopas = api("/categoria/create", {"nombre": "Sopas"}, token)
bebidas = api("/categoria/create", {"nombre": "Bebidas"}, token)
api("/producto/create", {"categoria_id": sopas["id"], "nombre": "Ajiaco", "precio": 25000}, token)
api("/producto/create", {"categoria_id": bebidas["id"], "nombre": "Avena", "precio": 6000}, token)

with sync_playwright() as p:
    browser = abrir_navegador(p)

    # Duplicar abre la copia para ajustarla
    page = contexto(browser, 1366, 900)
    login(page, "admin.esquina")
    page.goto(f"{APP}/admin/productos")
    page.get_by_role("button", name="Duplicar Limonada natural").click()
    dialogo = page.get_by_role("dialog")
    expect(dialogo).to_contain_text("Editar Limonada natural (copia)")
    shot(page, "p01-duplicado")
    dialogo.get_by_role("button", name="Cancelar").click()
    expect(page.get_by_role("cell", name="Limonada natural (copia)", exact=True)).to_be_visible()
    # Quien administra un solo restaurante no copia entre sedes
    expect(page.get_by_role("button", name="Copiar a otra sede")).to_have_count(0)
    shot(page, "p02-lista")
    page.context.close()

    # La dueña pasa solo las sopas a la otra sede
    page = contexto(browser, 1366, 900)
    login(page, dueno, "clave12345")
    page.goto(f"{APP}/admin/productos")
    page.get_by_label("Categoría").select_option(label="Sopas")
    page.get_by_role("button", name="Copiar a otra sede").click()
    dialogo = page.get_by_role("dialog")
    expect(dialogo).to_contain_text("1")
    expect(dialogo).to_contain_text("no se toca")
    shot(page, "p03-copiar")
    dialogo.get_by_role("button", name="Copiar", exact=True).click()
    expect(page.get_by_text("Copiados: 1")).to_be_visible()

    # Allá está la sopa y no la bebida
    otra = next(r for r in api("/login", {"usuario": dueno, "password": "clave12345"})["restaurantes"] if r["nombre"].startswith("Sur"))
    alla = api("/login", {"usuario": dueno, "password": "clave12345", "restaurante_id": otra["id"]})["token"]
    nombres = [x["nombre"] for x in api("/producto/list", {"todos": True}, alla)]
    assert nombres == ["Ajiaco"], nombres
    browser.close()

terminar()
