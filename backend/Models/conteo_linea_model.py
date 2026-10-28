from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, BigInteger, Numeric, ForeignKey, String

class ConteoLineaModel(DeRestaurante, BASE):

    __tablename__ = "conteo_linea"

    conteo_id = Column(BigInteger, ForeignKey("conteo.id"), nullable=False, index=True)
    insumo_id = Column(BigInteger, ForeignKey("insumo.id"), nullable=False)
    # Vacío mientras no se ha contado
    contado = Column(Numeric(16, 3), nullable=True)
    # Stock del sistema al aplicar y la diferencia que se ajustó
    teorico = Column(Numeric(16, 3), nullable=True)
    diferencia = Column(Numeric(16, 3), nullable=True)
    nota = Column(String(200), nullable=True)
