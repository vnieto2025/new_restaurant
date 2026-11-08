"""
Códigos de un solo uso por tiempo (TOTP, RFC 6238) para la verificación en dos pasos (ADR-054).
Compatibles con Google Authenticator, Microsoft Authenticator, Authy y similares: 6 dígitos cada 30 segundos.
"""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

PASO = 30
DIGITOS = 6
# Se acepta el código anterior y el siguiente: el reloj del celular puede ir unos segundos corrido
TOLERANCIA = 1
# Códigos de respaldo: para entrar si se pierde el celular. Sin letras que se confundan (0/O, 1/I/L)
ALFABETO_RESPALDO = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def nuevo_secreto() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def uri(secreto: str, cuenta: str, emisor: str) -> str:
    """ Lo que lee la aplicación del celular al escanear el QR """
    etiqueta = quote(f"{emisor}:{cuenta}", safe=":@")
    return f"otpauth://totp/{etiqueta}?secret={secreto}&issuer={quote(emisor)}&digits={DIGITOS}&period={PASO}"


def codigo(secreto: str, paso: int) -> str:
    llave = base64.b32decode(secreto + "=" * (-len(secreto) % 8))
    resumen = hmac.new(llave, struct.pack(">Q", paso), hashlib.sha1).digest()
    desfase = resumen[-1] & 0x0F
    numero = struct.unpack(">I", resumen[desfase:desfase + 4])[0] & 0x7FFFFFFF
    return str(numero % 10 ** DIGITOS).zfill(DIGITOS)


def paso_actual(momento: float = None) -> int:
    return int((momento if momento is not None else time.time()) // PASO)


def verificar(secreto: str, valor: str, ultimo_paso: int = None, momento: float = None):
    """ Devuelve el paso del código si es válido, o None. Un código ya usado (paso <= ultimo_paso) no
        vuelve a servir: quien lo vea por encima del hombro no puede reutilizarlo. """
    valor = "".join(c for c in str(valor or "") if c.isdigit())
    if len(valor) != DIGITOS:
        return None
    actual = paso_actual(momento)
    for paso in range(actual - TOLERANCIA, actual + TOLERANCIA + 1):
        if ultimo_paso is not None and paso <= ultimo_paso:
            continue
        if hmac.compare_digest(codigo(secreto, paso), valor):
            return paso
    return None


def codigos_respaldo(cantidad: int = 10) -> list:
    return ["".join(secrets.choice(ALFABETO_RESPALDO) for _ in range(8)) for _ in range(cantidad)]


def normalizar_respaldo(valor: str) -> str:
    return "".join(c for c in str(valor or "").upper() if c.isalnum())


def huella_respaldo(valor: str) -> str:
    return hashlib.sha256(normalizar_respaldo(valor).encode()).hexdigest()
