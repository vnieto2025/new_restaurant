from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, Numeric, Date, BigInteger, ForeignKey

# Porcentaje de un impuesto desde una fecha. Un cambio de tasa es una fila nueva, no una edición (RN-FIS-01)
class ImpuestoTarifaModel(DeRestaurante, BASE):

    __tablename__ = "impuesto_tarifa"

    impuesto_id = Column(BigInteger, ForeignKey("impuesto.id"), nullable=False, index=True)
    porcentaje = Column(Numeric(6, 3), nullable=False)
    vigente_desde = Column(Date, nullable=False)
    vigente_hasta = Column(Date, nullable=True)
    creado_por = Column(BigInteger, ForeignKey("usuario.id"), nullable=True)
