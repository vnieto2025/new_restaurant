"""
Adaptador de pasarelas de pago (ADR-011, doc 20A). Pagos en línea solo conoce esta interfaz; cada pasarela
(Wompi, PayU, ePayco…) será una clase que la cumpla. Mientras no se elija se usa la simulada, que tiene su
propia página de pago de pruebas y avisa el resultado con un webhook firmado, como una real.
El sistema nunca recibe datos de tarjeta (RG-19).
"""
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass


class PasarelaNoDisponible(Exception):
    """ La pasarela no responde: el cliente puede pagar en caja (RN-PAG-04) """


@dataclass
class Notificacion:
    referencia: str
    estado: str  # aprobado | rechazado
    transaccion_id: str = None
    monto: int = None
    comision: int = None


class Pasarela:
    nombre = ""

    def __init__(self, credenciales: dict, ambiente: str):
        self.credenciales = credenciales or {}
        self.ambiente = ambiente

    def crear_sesion(self, intento: dict) -> str:
        """ Abre la sesión de pago y devuelve la URL de la página segura de la pasarela """
        raise NotImplementedError

    def verificar_firma(self, cuerpo: bytes, cabeceras: dict) -> bool:
        raise NotImplementedError

    def interpretar(self, cuerpo: bytes) -> Notificacion:
        raise NotImplementedError

    def reembolsar(self, transaccion_id: str, monto: int) -> str:
        """ Devuelve la referencia del reembolso; lanza PasarelaNoDisponible si no se pudo """
        raise NotImplementedError


class PasarelaSimulada(Pasarela):
    """ Pasarela de pruebas. Su página de pago es una pantalla de la propia aplicación donde se elige
        aprobar o rechazar. En sus credenciales, "modo" = caido simula que no responde. """

    nombre = "simulada"
    CABECERA = "x-firma"

    def crear_sesion(self, intento: dict) -> str:
        if self.credenciales.get("modo") == "caido":
            raise PasarelaNoDisponible("La pasarela de pagos no responde.")
        return f"/pasarela-simulada/{intento['referencia']}"

    def firmar(self, cuerpo: bytes) -> str:
        return hmac.new(self.credenciales.get("secreto", "").encode(), cuerpo, hashlib.sha256).hexdigest()

    def verificar_firma(self, cuerpo: bytes, cabeceras: dict) -> bool:
        firma = cabeceras.get(self.CABECERA) or ""
        return bool(self.credenciales.get("secreto")) and hmac.compare_digest(firma, self.firmar(cuerpo))

    def interpretar(self, cuerpo: bytes) -> Notificacion:
        datos = json.loads(cuerpo)
        return Notificacion(referencia=datos["referencia"], estado=datos["estado"], transaccion_id=datos.get("transaccion_id"),
                            monto=datos.get("monto"), comision=datos.get("comision"))

    # Lo que la "pasarela" envía al sistema cuando el cliente decide en su página de pruebas
    def aviso(self, referencia: str, monto: int, aprobado: bool):
        datos = {"referencia": referencia, "estado": "aprobado" if aprobado else "rechazado",
                 "transaccion_id": f"SIM-{secrets.token_hex(6).upper()}", "monto": monto,
                 # Comisión de ejemplo para la conciliación; no es la tarifa de ninguna pasarela real
                 "comision": round(monto * 0.03) if aprobado else None}
        cuerpo = json.dumps(datos, sort_keys=True).encode()
        return cuerpo, {self.CABECERA: self.firmar(cuerpo)}

    def reembolsar(self, transaccion_id: str, monto: int) -> str:
        if self.credenciales.get("modo") == "caido":
            raise PasarelaNoDisponible("La pasarela de pagos no responde.")
        return f"REEMB-{transaccion_id}-{monto}"


PASARELAS = {
    PasarelaSimulada.nombre: PasarelaSimulada,
}
MODOS_SIMULADA = ["normal", "caido"]


def obtener_pasarela(nombre: str, credenciales: dict, ambiente: str) -> Pasarela:
    clase = PASARELAS.get(nombre)
    if not clase:
        raise PasarelaNoDisponible(f"La pasarela {nombre} no está disponible.")
    return clase(credenciales, ambiente)
