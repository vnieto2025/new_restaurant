from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, BigInteger, ForeignKey

TIPOS_MOVIMIENTO = ["gasto", "retiro", "aporte"]

# Entradas y salidas de efectivo que no son ventas (doc 20, sección 7)
class MovimientoCajaModel(DeRestaurante, BASE):

    __tablename__ = "movimiento_caja"

    turno_caja_id = Column(BigInteger, ForeignKey("turno_caja.id"), nullable=False, index=True)
    tipo = Column(String(10), nullable=False)
    monto = Column(BigInteger, nullable=False)
    concepto = Column(String(200), nullable=False)
    usuario_id = Column(BigInteger, ForeignKey("usuario.id"), nullable=True)
