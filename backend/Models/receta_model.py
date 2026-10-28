from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, BigInteger, Numeric, ForeignKey, UniqueConstraint, CheckConstraint

# Receta de un producto o de una preparación (doc 14, sección 2)
class RecetaModel(DeRestaurante, BASE):

    __tablename__ = "receta"
    __table_args__ = (
        UniqueConstraint("producto_id", name="uq_receta_producto"),
        UniqueConstraint("insumo_id", name="uq_receta_insumo"),
        CheckConstraint("(producto_id IS NULL) <> (insumo_id IS NULL)", name="ck_receta_destino"),
    )

    producto_id = Column(BigInteger, ForeignKey("producto.id"), nullable=True)
    # Preparación que produce esta receta
    insumo_id = Column(BigInteger, ForeignKey("insumo.id"), nullable=True)
    # Porciones del producto, o cantidad (en unidad base) de la preparación que resulta
    rendimiento = Column(Numeric(16, 3), nullable=False, default=1)
    actualizado_por = Column(BigInteger, ForeignKey("usuario.id"), nullable=True)
