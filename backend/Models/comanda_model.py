from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, Boolean, BigInteger, ForeignKey, DateTime

# Parte de una orden que va a un punto de producción (doc 15 y 19).
# Cada envío crea sus comandas; agregar ítems después crea una comanda de adición.
class ComandaModel(DeRestaurante, BASE):

    __tablename__ = "comanda"

    orden_id = Column(BigInteger, ForeignKey("orden.id"), nullable=False, index=True)
    punto_produccion_id = Column(BigInteger, ForeignKey("punto_produccion.id"), nullable=False, index=True)
    es_adicion = Column(Boolean, nullable=False, default=False)
    # Primera vez que la pantalla de producción la recibió (doc 17: "sin confirmar")
    recibida_en = Column(DateTime(timezone=True), nullable=True)
    impresa_en = Column(DateTime(timezone=True), nullable=True)
