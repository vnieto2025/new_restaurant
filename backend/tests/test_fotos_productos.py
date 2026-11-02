"""
Fotos y alérgenos de los productos (docs 11 y 12): compresión, carpeta por restaurante, validaciones,
reemplazo y borrado, copias independientes y lo que ve el cliente en la carta.
"""
import base64
import io
import os
from PIL import Image
from conftest import Api, find, login, qr_token
from Utils import imagenes


def foto(ancho=3000, alto=2000, formato="JPEG", **extra):
    # Ruido: una foto real no se comprime como un color plano
    imagen = Image.effect_noise((ancho, alto), 40).convert("RGB")
    salida = io.BytesIO()
    imagen.save(salida, formato, **extra)
    return salida.getvalue()


def b64(contenido):
    return base64.b64encode(contenido).decode()


def producto_de(api, nombre):
    return find(api.data("/producto/list", {"todos": True}), nombre=nombre)


def test_comprime_redimensiona_y_quita_metadatos():
    original = foto(quality=95)
    resultado = imagenes.comprimir(original)
    imagen = Image.open(io.BytesIO(resultado))
    assert imagen.format == "WEBP" and max(imagen.size) == imagenes.LADO_MAXIMO
    assert len(resultado) < len(original) / 5
    assert len(resultado) <= imagenes.PESO_OBJETIVO * 3  # el ruido es el peor caso

    # La ubicación que guarda la cámara no se publica en la carta
    exif = Image.Exif()
    exif[0x010F] = "Camara secreta"
    con_datos = io.BytesIO()
    Image.new("RGB", (200, 100), "red").save(con_datos, "JPEG", exif=exif)
    assert not Image.open(io.BytesIO(imagenes.comprimir(con_datos.getvalue()))).getexif()

    # La orientación de la cámara se aplica: una foto de celular no queda de lado
    girada = Image.Exif()
    girada[0x0112] = 6
    vertical = io.BytesIO()
    Image.new("RGB", (200, 100), "red").save(vertical, "JPEG", exif=girada)
    assert Image.open(io.BytesIO(imagenes.comprimir(vertical.getvalue()))).size == (100, 200)


def test_foto_en_la_carpeta_del_restaurante_y_en_la_carta(client, esquina):
    admin, sesion = esquina["admin.esquina"]
    producto = producto_de(admin, "Perro sencillo")
    respuesta = admin.data("/producto/imagen", {"producto_id": producto["id"], "archivo": b64(foto(800, 600))})
    id_restaurante = sesion["restaurante"]["id"]
    assert respuesta["imagen"].startswith(f"restaurantes/{id_restaurante}-la-esquina-centro/productos/")
    assert respuesta["imagen"].endswith(".webp")
    assert (imagenes.MEDIA_DIR / respuesta["imagen"]).exists()

    # Se sirve sin sesión: la carta es pública. Queda en caché y no se interpreta como otra cosa
    servida = client.get(f"/media/{respuesta['imagen']}")
    assert servida.status_code == 200 and servida.headers["content-type"] == "image/webp"
    assert "immutable" in servida.headers["cache-control"] and servida.headers["x-content-type-options"] == "nosniff"

    # Alérgenos y foto llegan al cliente
    admin.data("/producto/update", {**{k: producto[k] for k in ("categoria_id", "nombre", "precio")}, "producto_id": producto["id"],
                                    "alergenos": "Gluten, lácteos"})
    carta = Api(client).data("/publico/qr", {"token": qr_token(admin, "Mesa 7")})
    en_carta = next(p for c in carta["categorias"] for p in c["productos"] if p["id"] == producto["id"])
    assert en_carta["imagen"] == respuesta["imagen"] and en_carta["alergenos"] == "Gluten, lácteos"

    # Editar sin mandar alérgenos no los borra
    admin.data("/producto/update", {**{k: producto[k] for k in ("categoria_id", "nombre", "precio")}, "producto_id": producto["id"]})
    assert producto_de(admin, "Perro sencillo")["alergenos"] == "Gluten, lácteos"

    # Reemplazar borra la anterior; quitar borra el archivo
    otra = admin.data("/producto/imagen", {"producto_id": producto["id"], "archivo": b64(foto(400, 300))})
    assert otra["imagen"] != respuesta["imagen"] and not (imagenes.MEDIA_DIR / respuesta["imagen"]).exists()
    admin.data("/producto/imagen/quitar", {"producto_id": producto["id"]})
    assert not (imagenes.MEDIA_DIR / otra["imagen"]).exists() and producto_de(admin, "Perro sencillo")["imagen"] is None


def test_rechaza_lo_que_no_es_foto(esquina, napoli):
    admin, _ = esquina["admin.esquina"]
    producto = producto_de(admin, "Agua sin gas")
    subir = lambda contenido: admin.post("/producto/imagen", {"producto_id": producto["id"], "archivo": contenido})  # noqa: E731
    assert subir(b64(b"<script>alert(1)</script>")).status_code == 400
    assert subir("no es base64!").status_code == 400
    assert "6 MB" in subir("A" * (9 * 1024 * 1024)).json()["message"]
    gif = io.BytesIO()
    Image.new("RGB", (10, 10)).save(gif, "GIF")
    assert "JPG" in subir(b64(gif.getvalue())).json()["message"]
    assert producto_de(admin, "Agua sin gas")["imagen"] is None

    # Permisos y otra empresa
    caja, _ = esquina["caja.esquina"]
    assert caja.post("/producto/imagen", {"producto_id": producto["id"], "archivo": b64(foto(50, 50))}).status_code == 403
    pizzeria, _ = napoli["napoli"]
    assert pizzeria.post("/producto/imagen", {"producto_id": producto["id"], "archivo": b64(foto(50, 50))}).status_code == 404


def test_nadie_sale_de_la_carpeta(client):
    (imagenes.MEDIA_DIR.parent / "secreto.txt").write_text("x")
    try:
        assert client.get("/media/../secreto.txt").status_code == 404
        assert client.get("/media/%2e%2e/secreto.txt").status_code == 404
        assert client.get("/media/restaurantes/").status_code == 404  # sin listado de carpetas
    finally:
        os.remove(imagenes.MEDIA_DIR.parent / "secreto.txt")
    assert imagenes.ruta_segura("../../secreto.txt") is None


def test_duplicar_y_copiar_tienen_su_propia_foto(client, esquina):
    admin, _ = esquina["admin.esquina"]
    producto = producto_de(admin, "Cerveza nacional")
    original = admin.data("/producto/imagen", {"producto_id": producto["id"], "archivo": b64(foto(300, 300))})["imagen"]
    copia = admin.data("/producto/duplicar", {"producto_id": producto["id"]}, expect=201)
    assert copia["imagen"] and copia["imagen"] != original
    admin.data("/producto/imagen/quitar", {"producto_id": producto["id"]})
    assert (imagenes.MEDIA_DIR / copia["imagen"]).exists()

    soporte, _ = login(client, "soporte", "Soporte12345")
    empresa = soporte.data("/plataforma/empresa/create", {
        "nombre_comercial": "Cadena Fotos", "modulos": ["pedidos"], "estado_contrato": "activo",
        "admin": {"usuario": "dueno.fotos", "nombre": "Dueño", "password": "clave12345"}, "restaurante": {"nombre": "Sede A"}}, expect=201)
    b = soporte.data("/plataforma/restaurante/create", {"empresa_id": empresa["id"], "modulos": ["pedidos"], "estado_contrato": "activo",
                                                        "restaurante": {"nombre": "Sede B"}}, expect=201)
    dueno, _ = login(client, "dueno.fotos", "clave12345")
    categoria = dueno.data("/categoria/create", {"nombre": "Platos"}, expect=201)
    plato = dueno.data("/producto/create", {"categoria_id": categoria["id"], "nombre": "Sancocho", "precio": 20000, "alergenos": "Apio"}, expect=201)
    dueno.data("/producto/imagen", {"producto_id": plato["id"], "archivo": b64(foto(300, 300))})
    dueno.data("/producto/copiar", {"restaurante_id": b["id"], "productos": [plato["id"]]})
    dueno_b, _ = login(client, "dueno.fotos", "clave12345", restaurante_id=b["id"])
    alla = find(dueno_b.data("/producto/list", {"todos": True}), nombre="Sancocho")
    assert alla["alergenos"] == "Apio" and alla["imagen"].startswith(f"restaurantes/{b['id']}-sede-b/productos/")
