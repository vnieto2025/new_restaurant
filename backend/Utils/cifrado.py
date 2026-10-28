"""
Cifrado de secretos guardados en la base (credenciales del proveedor de facturación, RN-FIS-03).
La llave sale de CREDENCIALES_KEY o, si no existe, de MY_SECRET_KEY: cambiarla obliga a volver
a escribir las credenciales.
"""
import base64
import hashlib
import json
import os
from cryptography.fernet import Fernet, InvalidToken


def _fernet():
    secreto = os.getenv("CREDENCIALES_KEY") or os.getenv("MY_SECRET_KEY") or ""
    if not secreto:
        raise RuntimeError("Falta CREDENCIALES_KEY o MY_SECRET_KEY para cifrar credenciales.")
    llave = base64.urlsafe_b64encode(hashlib.sha256(secreto.encode()).digest())
    return Fernet(llave)


def cifrar(datos: dict) -> str:
    return _fernet().encrypt(json.dumps(datos).encode()).decode()


def descifrar(texto: str) -> dict:
    if not texto:
        return {}
    try:
        return json.loads(_fernet().decrypt(texto.encode()))
    except InvalidToken:
        return {}
