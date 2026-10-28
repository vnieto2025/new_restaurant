from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, BigInteger, ForeignKey, DateTime

# Conteo físico (doc 22, sección 5): se cuenta, se compara con el teórico y se aplican ajustes
class ConteoModel(DeRestaurante, BASE):

    __tablename__ = "conteo"

    nombre = Column(String(80), nullable=False)
    # abierto, aplicado, descartado
    estado = Column(String(12), nullable=False, default="abierto", index=True)
    creado_por = Column(BigInteger, ForeignKey("usuario.id"), nullable=True)
    aplicado_en = Column(DateTime(timezone=True), nullable=True)
    aplicado_por = Column(BigInteger, ForeignKey("usuario.id"), nullable=True)
