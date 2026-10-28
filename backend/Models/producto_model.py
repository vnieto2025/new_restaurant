from Config.db import BASE
from Models.base import DeRestaurante, BorradoLogico
from sqlalchemy import Column, String, Boolean, Integer, BigInteger, ForeignKey, Text, UniqueConstraint

class ProductoModel(DeRestaurante, BorradoLogico, BASE):

    __tablename__ = "producto"
    __table_args__ = (UniqueConstraint("restaurante_id", "nombre", name="uq_producto_nombre"),)

    categoria_id = Column(BigInteger, ForeignKey("categoria.id"), nullable=False, index=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    # Precio final de carta, con impuesto incluido, en pesos enteros (RG-03, ADR-010)
    precio = Column(BigInteger, nullable=False)
    punto_produccion_id = Column(BigInteger, ForeignKey("punto_produccion.id"), nullable=True)
    # Vacío = el de la categoría o, si tampoco tiene, el impuesto por defecto
    impuesto_id = Column(BigInteger, ForeignKey("impuesto.id"), nullable=True)
    orden = Column(Integer, nullable=False, default=0)
    agotado = Column(Boolean, nullable=False, default=False)
    activo = Column(Boolean, nullable=False, default=True)
