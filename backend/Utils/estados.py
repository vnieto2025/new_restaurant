"""
Máquina de estados de los ítems y estado derivado de la orden (doc 16, ADR-006).
Es la única fuente de verdad sobre transiciones: cualquier otra se rechaza (RG-22).
"""
from Utils.tools import CustomException

PENDIENTE = "pendiente_aprobacion"
NUEVO = "nuevo"
EN_PROCESO = "en_proceso"
DESPACHADO = "despachado"
ENTREGADO = "entregado"
CANCELADO = "cancelado"

TRANSICIONES = {
    PENDIENTE: [NUEVO, CANCELADO],
    # nuevo -> despachado solo en puntos que saltan "en proceso" (bebidas simples)
    NUEVO: [EN_PROCESO, DESPACHADO, CANCELADO],
    EN_PROCESO: [DESPACHADO, CANCELADO],
    # despachado -> en_proceso es reabrir por error (auditado)
    DESPACHADO: [ENTREGADO, EN_PROCESO, CANCELADO],
    # entregado -> cancelado es devolución (permiso elevado)
    ENTREGADO: [CANCELADO],
    CANCELADO: [],
}

ETIQUETAS = {
    PENDIENTE: "Por aprobar",
    NUEVO: "Nuevo",
    EN_PROCESO: "En proceso",
    DESPACHADO: "Listo",
    ENTREGADO: "Entregado",
    CANCELADO: "Cancelado",
}

# Estados en los que el ítem aún ocupa a alguien (cocina o mesero)
PENDIENTES_DE_ENTREGA = [PENDIENTE, NUEVO, EN_PROCESO, DESPACHADO]


def validar_transicion(actual: str, nuevo: str):
    if nuevo not in TRANSICIONES.get(actual, []):
        raise CustomException(
            f"No se puede pasar un ítem de «{ETIQUETAS.get(actual, actual)}» a «{ETIQUETAS.get(nuevo, nuevo)}».",
            409,
        )


def estado_derivado(estados: list):
    """ Estado de la orden (o de la comanda) a partir de sus ítems (doc 16, sección 4) """
    if not estados:
        return "nueva"
    vivos = [estado for estado in estados if estado != CANCELADO]
    if not vivos:
        return "cancelada"
    if all(estado == ENTREGADO for estado in vivos):
        return "entregada"
    if all(estado in [DESPACHADO, ENTREGADO] for estado in vivos):
        return "lista"
    if all(estado == NUEVO for estado in vivos):
        return "nueva"
    if all(estado == PENDIENTE for estado in vivos):
        return PENDIENTE
    return "en_proceso"
