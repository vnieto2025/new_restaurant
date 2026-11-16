"""
Logo del restaurante y billeteras para pagar (ADR-060): el logo es horizontal y lo sube el administrador o soporte;
las billeteras (nombre, teléfono, titular y QR) son informativas y llegan a la sesión del personal y al cliente.
"""
import base64
import io
import segno
from PIL import Image
from conftest import login, find
from Utils.imagenes import MEDIA_DIR


def imagen(ancho, alto, formato="PNG"):
    salida = io.BytesIO()
    Image.new("RGBA", (ancho, alto), (200, 30, 30, 255)).save(salida, formato)
    return base64.b64encode(salida.getvalue()).decode()


def qr_png(texto):
    salida = io.BytesIO()
    segno.make(texto, error="m").save(salida, kind="png", scale=6, border=4)
    return base64.b64encode(salida.getvalue()).decode()


def test_logo_horizontal_desde_el_restaurante_y_desde_soporte(client, esquina):
    admin, _ = esquina["admin.esquina"]
    mesero, _ = esquina["mesero.salon"]
    vertical = admin.post("/restaurante/logo", {"archivo": imagen(300, 400)})
    assert vertical.status_code == 400 and "600 × 200" in vertical.json()["message"]
    assert mesero.post("/restaurante/logo", {"archivo": imagen(600, 200)}).status_code == 403

    logo = admin.data("/restaurante/logo", {"archivo": imagen(1200, 400)})["logo"]
    assert "la-esquina-centro/logo/" in logo and (MEDIA_DIR / logo).exists()
    assert admin.data("/restaurante/get")["logo"] == logo
    assert admin.data("/auth/sesion")["restaurante"]["logo"] == logo

    # Soporte le pone el logo a otro restaurante desde la consola
    soporte, _ = login(client, "soporte", "Soporte12345")
    napoli = find(soporte.data("/plataforma/empresa/list"), nombre_comercial="Pizzería Napoli")["restaurantes"][0]
    otro = soporte.data("/plataforma/restaurante/logo", {"restaurante_id": napoli["id"], "archivo": imagen(600, 200)})["logo"]
    assert "napoli-norte/logo/" in otro

    admin.data("/restaurante/logo/quitar")
    assert admin.data("/restaurante/get")["logo"] is None and not (MEDIA_DIR / logo).exists()


def test_billeteras_informativas(esquina):
    admin, _ = esquina["admin.esquina"]
    caja, _ = esquina["caja.esquina"]
    assert "teléfono de la billetera" in admin.post("/billetera/save", {"nombre": "Nequi"}).json()["message"]
    assert caja.post("/billetera/save", {"nombre": "Nequi", "telefono": "3001234567"}).status_code == 403

    nequi = admin.data("/billetera/save", {"nombre": "Nequi", "telefono": "300 123 4567", "titular": "La Esquina SAS",
                                           "qr_archivo": qr_png("https://nequi.example/pagar/esquina")})
    assert nequi["telefono"] == "300 123 4567" and nequi["qr"].endswith(".webp")
    # El QR se guarda sin pérdida: sigue nítido para leerse
    assert (MEDIA_DIR / nequi["qr"]).exists()
    davi = admin.data("/billetera/save", {"nombre": "Daviplata", "telefono": "3109876543", "orden": 2})

    # El personal la tiene en su sesión (cobro y tirillas)
    en_sesion = caja.data("/auth/sesion")["restaurante"]["billeteras"]
    assert [b["nombre"] for b in en_sesion] == ["Nequi", "Daviplata"] and en_sesion[0]["titular"] == "La Esquina SAS"

    # Desactivada no se muestra; eliminada desaparece con su QR
    admin.data("/billetera/save", {"billetera_id": davi["id"], "nombre": "Daviplata", "telefono": "3109876543", "activo": False})
    assert [b["nombre"] for b in caja.data("/auth/sesion")["restaurante"]["billeteras"]] == ["Nequi"]
    admin.data("/billetera/delete", {"billetera_id": nequi["id"]})
    assert not (MEDIA_DIR / nequi["qr"]).exists()
    admin.data("/billetera/delete", {"billetera_id": davi["id"]})
    assert admin.data("/billetera/list") == []
