"""
Adaptador de WhatsApp para el envío automático (ADR-011, doc 31B opción A).
Las notificaciones solo conocen esta interfaz; cada proveedor autorizado de la API oficial es una clase
que la cumple. Mientras no se elija proveedor se usa el simulado. Nunca herramientas no oficiales (opción C).
"""
import hashlib
from dataclasses import dataclass


class ProveedorNoDisponible(Exception):
    """ Falla temporal (red, caída del proveedor): el aviso se reintenta más tarde """


@dataclass
class Resultado:
    # enviada: el proveedor la aceptó | rechazada: no se puede enviar (número inválido, plantilla no aprobada)
    estado: str
    mensaje: str = ""
    referencia: str = None


class ProveedorMensajes:
    nombre = ""

    def __init__(self, credenciales: dict, remitente: str = None):
        self.credenciales = credenciales or {}
        self.remitente = remitente

    def enviar(self, telefono: str, texto: str, evento: str) -> Resultado:
        raise NotImplementedError


class ProveedorSimulado(ProveedorMensajes):
    """ Proveedor de pruebas. En sus credenciales, "modo" decide qué responde: aceptar (por defecto),
        rechazar o caido. """

    nombre = "simulado"

    def enviar(self, telefono: str, texto: str, evento: str) -> Resultado:
        modo = self.credenciales.get("modo", "aceptar")
        if modo == "caido":
            raise ProveedorNoDisponible("El proveedor de WhatsApp no responde.")
        if modo == "rechazar":
            return Resultado("rechazada", "Rechazo simulado: la plantilla no está aprobada.")
        if not telefono or len(telefono) < 11:
            return Resultado("rechazada", "El número no tiene WhatsApp.")
        referencia = hashlib.sha1(f"{telefono}|{evento}|{texto}".encode()).hexdigest()[:20]
        return Resultado("enviada", "Mensaje enviado (simulado).", referencia=f"SIM-{referencia}")


PROVEEDORES = {
    ProveedorSimulado.nombre: ProveedorSimulado,
}
MODOS_SIMULADO = ["aceptar", "rechazar", "caido"]


def obtener_proveedor(nombre: str, credenciales: dict, remitente: str = None) -> ProveedorMensajes:
    clase = PROVEEDORES.get(nombre)
    if not clase:
        raise ProveedorNoDisponible(f"El proveedor {nombre} no está disponible.")
    return clase(credenciales, remitente)
