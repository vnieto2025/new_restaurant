import io
import os
import re
import secrets
import shutil
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError
from Utils.tools import CustomException, normalize_text

# Dónde quedan las fotos; en Docker es un volumen propio, que entra en los respaldos
MEDIA_DIR = Path(os.getenv("MEDIA_DIR") or Path(__file__).resolve().parent.parent / "media")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

MAX_ARCHIVO = 6 * 1024 * 1024
FORMATOS = {"JPEG", "PNG", "WEBP"}
# Una imagen pequeña en bytes puede pedir gigas de memoria al abrirse: se rechaza antes de decodificarla
MAX_PIXELES = 40_000_000
LADO_MAXIMO = 1000
PESO_OBJETIVO = 150 * 1024
CALIDADES = [80, 70, 60, 50]


def comprimir(contenido: bytes):
    """ Valida que sea una foto de verdad y la deja en WebP, liviana para el celular de quien mira la carta.
        Volver a generarla descarta lo que traía el archivo original, como la ubicación GPS. """
    if len(contenido) > MAX_ARCHIVO:
        raise CustomException("La foto pesa más de 6 MB.")
    try:
        imagen = Image.open(io.BytesIO(contenido))
        if imagen.format not in FORMATOS:
            raise CustomException("La foto debe ser JPG, PNG o WebP.")
        if imagen.width * imagen.height > MAX_PIXELES:
            raise CustomException("La foto es demasiado grande.")
        # La cámara guarda la orientación aparte: sin esto, algunas fotos quedarían de lado
        imagen = ImageOps.exif_transpose(imagen)
        imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
        imagen = imagen.convert("RGBA" if imagen.mode in ("RGBA", "LA", "P") else "RGB")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise CustomException("El archivo no es una imagen válida.")
    resultado = b""
    for calidad in CALIDADES:
        salida = io.BytesIO()
        imagen.save(salida, "WEBP", quality=calidad, method=6)
        resultado = salida.getvalue()
        if len(resultado) <= PESO_OBJETIVO:
            break
    return resultado


def carpeta_de(restaurante, tipo="productos"):
    """ Carpeta del restaurante: el número la hace única y el nombre deja reconocerla a simple vista.
        Si el restaurante cambia de nombre las fotos siguen ahí: la ruta completa está guardada en cada producto. """
    slug = re.sub(r"[^a-z0-9]+", "-", normalize_text(restaurante.nombre)).strip("-")[:40] or "restaurante"
    return f"restaurantes/{restaurante.id}-{slug}/{tipo}"


def guardar(contenido: bytes, restaurante, tipo="productos"):
    relativa = f"{carpeta_de(restaurante, tipo)}/{secrets.token_urlsafe(16)}.webp"
    destino = MEDIA_DIR / relativa
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    return relativa


def copiar(relativa, restaurante, tipo="productos"):
    """ Copia propia para otro producto o sede: borrar una foto no debe dejar a otro producto sin la suya """
    origen = ruta_segura(relativa)
    if not origen or not origen.exists():
        return None
    nueva = f"{carpeta_de(restaurante, tipo)}/{secrets.token_urlsafe(16)}.webp"
    (MEDIA_DIR / nueva).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(origen, MEDIA_DIR / nueva)
    return nueva


def borrar(relativa):
    archivo = ruta_segura(relativa)
    if archivo:
        archivo.unlink(missing_ok=True)


def ruta_segura(relativa):
    if not relativa:
        return None
    archivo = (MEDIA_DIR / relativa).resolve()
    return archivo if archivo.is_relative_to(MEDIA_DIR.resolve()) else None
