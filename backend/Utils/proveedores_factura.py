"""
Adaptador de facturación electrónica (ADR-011, doc 21A sección 4).
Facturación y caja solo conocen esta interfaz; cada proveedor tecnológico es una clase que la cumple.
Mientras no se elija proveedor se usa el simulado, que responde como lo haría uno real.
"""
import hashlib
from dataclasses import dataclass


class ProveedorNoDisponible(Exception):
    """ Falla temporal (red, caída del proveedor): el documento se reintenta más tarde """


@dataclass
class Resultado:
    # aceptada: validada por la autoridad | emitida: recibida, la validación llega después | rechazada: con errores
    estado: str
    mensaje: str = ""
    cufe: str = None
    referencia: str = None


class ProveedorFacturacion:
    nombre = ""

    def __init__(self, credenciales: dict, ambiente: str):
        self.credenciales = credenciales or {}
        self.ambiente = ambiente

    def emitir(self, documento: dict) -> Resultado:
        raise NotImplementedError


class ProveedorSimulado(ProveedorFacturacion):
    """ Proveedor de pruebas. En sus credenciales, "modo" decide qué responde:
        aceptar (por defecto), rechazar o caido. """

    nombre = "simulado"

    def emitir(self, documento: dict) -> Resultado:
        modo = self.credenciales.get("modo", "aceptar")
        if modo == "caido":
            raise ProveedorNoDisponible("El proveedor de facturación no responde.")
        if modo == "rechazar":
            return Resultado("rechazada", "Rechazo simulado: revisa los datos del documento.")

        receptor = documento["receptor"]
        if documento["tipo"] == "factura" and not receptor.get("documento"):
            return Resultado("rechazada", "La factura necesita el documento de identidad del cliente.")
        if documento["tipo"] == "nota_credito" and not documento.get("referencia"):
            return Resultado("rechazada", "La nota crédito debe referenciar el documento que corrige.")
        if sum(l["base"] + l["impuesto_valor"] for l in documento["lineas"]) != documento["total"]:
            return Resultado("rechazada", "La suma de las líneas no coincide con el total.")

        # Código único como lo calcula un proveedor real: huella de los datos del documento
        huella = "|".join(str(v) for v in (documento["emisor"]["nit"], documento["numero_completo"],
                                            documento["fecha"], documento["total"], documento["impuestos"]))
        cufe = hashlib.sha384(huella.encode()).hexdigest()
        return Resultado("aceptada", "Documento validado (simulado).", cufe=cufe,
                         referencia=f"SIM-{documento['numero_completo']}")


PROVEEDORES = {
    ProveedorSimulado.nombre: ProveedorSimulado,
}


def obtener_proveedor(nombre: str, credenciales: dict, ambiente: str) -> ProveedorFacturacion:
    clase = PROVEEDORES.get(nombre)
    if not clase:
        raise ProveedorNoDisponible(f"El proveedor {nombre} no está disponible.")
    return clase(credenciales, ambiente)
