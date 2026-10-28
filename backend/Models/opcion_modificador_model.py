from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Boolean, Integer, BigInteger, ForeignKey

class OpcionModificadorModel(DeRestaurante, BASE):

    __tablename__ = "opcion_modificador"

    grupo_id = Column(BigInteger, ForeignKey("grupo_modificador.id"), nullable=False, index=True)
    nombre = Column(String(60), nullable=False)
    # Valor que se suma al precio del producto; puede ser 0, nunca negativo (RN-PRO-04)
    precio_extra = Column(BigInteger, nullable=False, default=0)
    orden = Column(Integer, nullable=False, default=0)
    activo = Column(Boolean, nullable=False, default=True)
