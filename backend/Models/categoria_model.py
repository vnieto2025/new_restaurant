from Config.db import BASE
from Models.base import DeRestaurante, BorradoLogico
from sqlalchemy import Column, String, Boolean, Integer, BigInteger, ForeignKey, UniqueConstraint

class CategoriaModel(DeRestaurante, BorradoLogico, BASE):

    __tablename__ = "categoria"
    __table_args__ = (UniqueConstraint("restaurante_id", "nombre", name="uq_categoria_nombre"),)

    nombre = Column(String(60), nullable=False)
    orden = Column(Integer, nullable=False, default=0)
    # Destino de los productos que no tienen punto propio (doc 19, sección 3)
    punto_produccion_id = Column(BigInteger, ForeignKey("punto_produccion.id"), nullable=True)
    impuesto_id = Column(BigInteger, ForeignKey("impuesto.id"), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
