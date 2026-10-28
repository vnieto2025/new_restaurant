from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Integer, Text, JSON, UniqueConstraint

MODOS_AVISO = ["manual", "automatico"]

# Cómo avisa el restaurante a sus clientes por WhatsApp (doc 31B): enlace con el mensaje escrito
# que alguien envía (opción B) o envío automático por un proveedor de la API oficial (opción A)
class NotificacionConfigModel(DeRestaurante, BASE):

    __tablename__ = "notificacion_config"
    __table_args__ = (UniqueConstraint("restaurante_id", name="uq_notificacion_config"),)

    modo = Column(String(12), nullable=False, default="manual")
    proveedor = Column(String(30), nullable=False, default="simulado")
    # Nunca se devuelven al cliente después de guardarlas
    credenciales = Column(Text, nullable=True)
    numero_remitente = Column(String(20), nullable=True)
    # Qué eventos se avisan y con qué texto (RN-NOT-04); lo que falta toma el valor por defecto
    eventos = Column(JSON, nullable=True)
    plantillas = Column(JSON, nullable=True)
    # Máximo de avisos por teléfono en el día, para evitar abusos
    limite_diario = Column(Integer, nullable=False, default=5)
