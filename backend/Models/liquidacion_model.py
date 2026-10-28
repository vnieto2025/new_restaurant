from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, BigInteger, ForeignKey, Date, DateTime, JSON, UniqueConstraint

TIPOS_LIQUIDACION = ["propinas", "domiciliarios"]
# La que sigue acumulando ("abierta") no se guarda: es la vista previa del periodo actual (doc 26A, sección 4)
ESTADOS_LIQUIDACION = ["calculada", "aprobada", "pagada"]

# Liquidación de un periodo: reparto de propinas o pago a domiciliarios
class LiquidacionModel(DeRestaurante, BASE):

    __tablename__ = "liquidacion"
    __table_args__ = (UniqueConstraint("restaurante_id", "tipo", "desde", name="uq_liquidacion_periodo"),)

    tipo = Column(String(15), nullable=False)
    desde = Column(Date, nullable=False)
    hasta = Column(Date, nullable=False)
    estado = Column(String(10), nullable=False, default="calculada", index=True)
    # Copia de las reglas con que se calculó: cambiar la regla aplica a periodos nuevos (RN-PRP-02)
    reglas = Column(JSON, nullable=False)
    # Lo que se liquida: cuentas, entregas y rendiciones incluidas; se marcan al aprobar (RN-PRP-06)
    insumos = Column(JSON, nullable=False)
    # Totales por zona, por mesero de origen, retención, sin repartir y avisos
    resumen = Column(JSON, nullable=True)
    total = Column(BigInteger, nullable=False, default=0)
    calculada_en = Column(DateTime(timezone=True), nullable=True)
    calculada_por = Column(BigInteger, ForeignKey("usuario.id", name="fk_liquidacion_calculada_por"), nullable=True)
    aprobada_en = Column(DateTime(timezone=True), nullable=True)
    aprobada_por = Column(BigInteger, ForeignKey("usuario.id", name="fk_liquidacion_aprobada_por"), nullable=True)
    pagada_en = Column(DateTime(timezone=True), nullable=True)
