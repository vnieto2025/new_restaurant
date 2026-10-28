from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Integer, BigInteger, Text, DateTime, ForeignKey

ESTADOS_AVISO = ["pendiente", "manual", "enviada", "fallida", "omitida", "descartada"]

# Cada aviso con destinatario, momento, plantilla y resultado (RN-NOT-03)
class NotificacionModel(DeRestaurante, BASE):

    __tablename__ = "notificacion"

    evento = Column(String(30), nullable=False)
    canal = Column(String(15), nullable=False, default="whatsapp")
    orden_id = Column(BigInteger, ForeignKey("orden.id", name="fk_notificacion_orden"), nullable=True, index=True)
    cliente_id = Column(BigInteger, ForeignKey("cliente.id", name="fk_notificacion_cliente"), nullable=True)
    nombre = Column(String(100), nullable=True)
    # Dígitos con indicativo de país; vacío si el teléfono no era válido
    telefono = Column(String(20), nullable=True, index=True)
    mensaje = Column(Text, nullable=False)
    modo = Column(String(12), nullable=False)
    # pendiente: en cola automática | manual: espera que alguien la envíe | enviada | fallida
    # omitida: no se podía enviar (sin teléfono, sin permiso, límite) | descartada: alguien decidió no enviarla
    estado = Column(String(12), nullable=False, index=True)
    intentos = Column(Integer, nullable=False, default=0)
    proximo_intento_en = Column(DateTime(timezone=True), nullable=True)
    error = Column(String(200), nullable=True)
    referencia = Column(String(80), nullable=True)
    enviada_en = Column(DateTime(timezone=True), nullable=True)
    enviada_por = Column(BigInteger, ForeignKey("usuario.id", name="fk_notificacion_usuario"), nullable=True)
