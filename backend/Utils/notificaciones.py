"""
Avisos al cliente por WhatsApp sobre sus propias órdenes (doc 31B). Los eventos de la operación llaman a
notificar(), que solo deja el aviso registrado: en modo manual espera que alguien lo envíe con el enlace,
en modo automático lo envía la cola. Una falla aquí nunca detiene la orden (RN-NOT-01).
"""
import logging
import re
from datetime import timedelta
from Utils.tools import now, clean_text
from Utils.telefono import normalizar_telefono

log = logging.getLogger("notificaciones")

EVENTOS = {
    "orden_recibida": {
        "nombre": "Confirmación de orden", "defecto": False,
        "plantilla": "Hola {nombre}, recibimos tu orden {numero} en {restaurante}. Te avisaremos cuando esté lista.",
    },
    "orden_lista": {
        "nombre": "Lista para recoger", "defecto": True,
        "plantilla": "Hola {nombre}, tu orden {numero} en {restaurante} está lista para recoger.",
    },
    "domicilio_salio": {
        "nombre": "Salió a domicilio", "defecto": True,
        "plantilla": "Hola {nombre}, tu orden {numero} de {restaurante} ya va en camino.",
    },
    "entrega_fallida": {
        "nombre": "Entrega fallida", "defecto": True,
        "plantilla": "Hola {nombre}, no pudimos entregar tu orden {numero}. Escríbenos para coordinar.",
    },
}
VARIABLES = ["nombre", "numero", "restaurante", "direccion"]
LIMITE_DIARIO = 5


def plantilla_valida(texto: str):
    """ Solo variables conocidas: un error de escritura no debe romper el envío """
    usadas = set(re.findall(r"\{(\w*)\}", texto))
    return not (usadas - set(VARIABLES)) and texto.count("{") == texto.count("}")


def evento_activo(config, evento: str):
    eventos = (config.eventos if config else None) or {}
    return eventos.get(evento, EVENTOS[evento]["defecto"])


def plantilla_de(config, evento: str):
    plantillas = (config.plantillas if config else None) or {}
    return plantillas.get(evento) or EVENTOS[evento]["plantilla"]


def armar(plantilla: str, valores: dict):
    return plantilla.format_map({k: valores.get(k) or "" for k in VARIABLES}).strip()


def notificar(db, ctx, evento: str, orden, entrega=None):
    """ Registra el aviso de un evento de una orden. Devuelve True si quedó en la cola automática.
        Va en un punto de guardado propio: si algo falla, la operación sigue como si no hubiera aviso. """
    try:
        with db.begin_nested():
            return _notificar(db, ctx, evento, orden, entrega)
    except Exception as error:  # noqa: BLE001
        log.exception("Aviso %s de la orden %s: %s", evento, getattr(orden, "id", None), error)
        return False


def _notificar(db, ctx, evento, orden, entrega):
    from Querys.base import Querys
    from Models.notificacion_config_model import NotificacionConfigModel
    from Models.notificacion_model import NotificacionModel
    from Models.cliente_model import ClienteModel
    from Models.restaurante_model import RestauranteModel

    querys = Querys(db, ctx)
    config = querys.scoped(NotificacionConfigModel).first()
    if not evento_activo(config, evento):
        return False
    # Un mismo evento de una orden se avisa una vez (una comanda reabierta no repite "lista")
    if querys.scoped(NotificacionModel).filter(NotificacionModel.orden_id == orden.id, NotificacionModel.evento == evento,
                                               NotificacionModel.estado != "descartada").first():
        return False

    restaurante = db.get(RestauranteModel, orden.restaurante_id)
    cliente = db.get(ClienteModel, orden.cliente_id) if orden.cliente_id else None
    nombre = (entrega.cliente_nombre if entrega else None) or orden.cliente_nombre or (cliente.nombre if cliente else "")
    crudo = (entrega.telefono if entrega else None) or orden.cliente_telefono
    modo = config.modo if config else "manual"
    texto = armar(plantilla_de(config, evento), {
        "nombre": (nombre or "").split(" ")[0] if nombre else "", "numero": f"#{orden.numero:03d}",
        "restaurante": restaurante.nombre, "direccion": entrega.direccion if entrega else "",
    })
    fila = {"evento": evento, "orden_id": orden.id, "cliente_id": cliente.id if cliente else None,
            "nombre": clean_text(nombre)[:100] if nombre else None, "mensaje": texto, "modo": modo}

    motivo = None
    try:
        telefono = normalizar_telefono(crudo)
    except Exception:  # noqa: BLE001
        telefono = None
    if not telefono:
        motivo = "Sin teléfono válido"  # RN-NOT-05
    elif cliente and cliente.acepta_avisos is False:
        motivo = "El cliente pidió no recibir avisos"
    else:
        inicio = now() - timedelta(hours=24)
        enviados = querys.scoped(NotificacionModel).filter(
            NotificacionModel.telefono == telefono, NotificacionModel.creado_en >= inicio,
            NotificacionModel.estado.notin_(["omitida", "descartada"])).count()
        if enviados >= (config.limite_diario if config else LIMITE_DIARIO):
            motivo = "Límite diario de avisos para este teléfono"
    if motivo:
        guardar(db, querys, {**fila, "telefono": telefono, "estado": "omitida", "error": motivo})
        return False
    estado = "pendiente" if modo == "automatico" else "manual"
    guardar(db, querys, {**fila, "telefono": telefono, "estado": estado})
    return estado == "pendiente"


# Sin Querys.insert_data: su rollback deshace la transacción completa y aquí solo debe caer el aviso
def guardar(db, querys, fila: dict):
    from Models.notificacion_model import NotificacionModel
    db.add(NotificacionModel(querys._with_tenant(NotificacionModel, fila)))
    db.flush()
