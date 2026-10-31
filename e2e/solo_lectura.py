"""Recorrido de los estados del contrato: soporte suspende a La Esquina; el administrador consulta y descarga, pero no
puede registrar cambios; el mesero ve sus mesas; el QR no recibe pedidos. Al cancelar solo queda descargar. Reactivar
devuelve todo con sus datos."""
from playwright.sync_api import sync_playwright, expect
from comun import APP, OUT, api, contexto, login, shot, abrir_navegador, terminar


soporte = api("/login", {"usuario": "soporte", "password": "Soporte12345"})["token"]
admin = api("/login", {"usuario": "admin.esquina", "password": "demo1234"})
restaurante_id = admin["restaurante"]["id"]
modulos = [m for m in admin["modulos"] if m != "base"]
token_qr = next(q for q in api("/qr/list", {}, admin["token"]) if q["mesa"] == "Mesa 5")["url"].rsplit("/", 1)[1]


def contrato(estado):
    api("/plataforma/contrato/update", {"restaurante_id": restaurante_id, "estado": estado, "modulos": modulos}, soporte)


try:
    with sync_playwright() as p:
        browser = abrir_navegador(p)
        contrato("suspendido")

        # Administrador: ve el aviso y su información
        page = contexto(browser, 1366, 900)
        login(page, "admin.esquina")
        page.goto(f"{APP}/admin/productos")
        expect(page.get_by_role("status").filter(has_text="Solo lectura")).to_be_visible()
        expect(page.get_by_text("Hamburguesa clásica")).to_be_visible()
        shot(page, "l01-admin-suspendido")

        # Intentar un cambio responde con la explicación, no con un error genérico
        page.goto(f"{APP}/admin/zonas")
        page.get_by_role("button", name="Crear zona").click()
        dialogo = page.get_by_role("dialog")
        dialogo.locator("input").first.fill("Zona nueva")
        dialogo.get_by_role("button", name="Guardar").click()
        expect(page.get_by_role("alert").filter(has_text="está suspendido")).to_be_visible()
        shot(page, "l02-cambio-rechazado")

        # Descargar sigue funcionando
        page.goto(f"{APP}/admin/exportar")
        with page.expect_download() as descarga:
            page.get_by_role("button", name="Descargar Productos en Excel").click()
        assert descarga.value.suggested_filename == "productos.xlsx"
        page.context.close()

        # Mesero en el celular: ve sus mesas con el aviso
        page = contexto(browser, 390, 844, mobile=True)
        login(page, "mesero.salon")
        expect(page.get_by_text("Solo lectura.")).to_be_visible()
        shot(page, "l03-mesero-suspendido")
        page.context.close()

        # Cliente: el QR no ofrece la carta
        page = contexto(browser, 390, 844, mobile=True)
        page.goto(f"{APP}/q/{token_qr}")
        expect(page.get_by_text("no está recibiendo pedidos")).to_be_visible()
        shot(page, "l04-qr-suspendido")
        page.context.close()

        # Cancelado: el administrador solo llega a la pantalla de descargas
        contrato("cancelado")
        page = contexto(browser, 1366, 900)
        login(page, "admin.esquina")
        page.wait_for_url("**/admin/exportar")
        expect(page.get_by_text("Contrato cancelado.")).to_be_visible()
        expect(page.get_by_text("Disponible hasta el")).to_be_visible()
        expect(page.get_by_role("link", name="Productos")).to_have_count(0)
        shot(page, "l05-cancelado-exportar")
        with page.expect_download() as descarga:
            page.get_by_role("button", name="Descargar Productos en CSV").click()
        descarga.value.save_as(OUT / "productos.csv")
        assert "Hamburguesa clásica" in (OUT / "productos.csv").read_text(encoding="utf-8-sig")
        page.goto(f"{APP}/caja")
        page.wait_for_url("**/admin/exportar")
        page.context.close()

        # El mesero ya no puede entrar
        page = contexto(browser, 1280, 860)
        page.goto(f"{APP}/login")
        page.fill("#usuario", "mesero.salon")
        page.fill("#password", "demo1234")
        page.click("button[type=submit]")
        expect(page.get_by_text("está cancelado")).to_be_visible()
        shot(page, "l06-mesero-cancelado")
        page.context.close()

        # Reactivar: vuelve a operar sin perder datos
        contrato("activo")
        page = contexto(browser, 1366, 900)
        login(page, "admin.esquina")
        page.goto(f"{APP}/admin/productos")
        expect(page.get_by_text("Hamburguesa clásica")).to_be_visible()
        expect(page.get_by_text("Solo lectura.")).to_have_count(0)
        shot(page, "l07-reactivado")

        browser.close()
finally:
    contrato("activo")

# Los rechazos de este recorrido son el resultado esperado de estar suspendido o cancelado
terminar(esperados=("status of 403",))
