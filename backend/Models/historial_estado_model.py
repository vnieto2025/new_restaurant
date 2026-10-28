from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, BigInteger, ForeignKey

# Cada cambio de estado de un ítem (doc 16, sección 5)
class HistorialEstadoModel(DeRestaurante, BASE):

    __tablename__ = "historial_estado"

    orden_item_id = Column(BigInteger, ForeignKey("orden_item.id"), nullable=False, index=True)
    estado_anterior = Column(String(25), nullable=True)
    estado_nuevo = Column(String(25), nullable=False)
    usuario_id = Column(BigInteger, ForeignKey("usuario.id"), nullable=True)
    dispositivo = Column(String(250), nullable=True)
    motivo = Column(String(200), nullable=True)
