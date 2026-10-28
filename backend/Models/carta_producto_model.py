from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, BigInteger, ForeignKey, UniqueConstraint

class CartaProductoModel(DeRestaurante, BASE):

    __tablename__ = "carta_producto"
    __table_args__ = (UniqueConstraint("carta_id", "producto_id", name="uq_carta_producto"),)

    carta_id = Column(BigInteger, ForeignKey("carta.id"), nullable=False, index=True)
    producto_id = Column(BigInteger, ForeignKey("producto.id"), nullable=False)
