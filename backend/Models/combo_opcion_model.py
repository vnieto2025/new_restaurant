from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, Integer, BigInteger, ForeignKey, UniqueConstraint

# Producto que se puede elegir en un componente; con una sola opción el componente es fijo
class ComboOpcionModel(DeRestaurante, BASE):

    __tablename__ = "combo_opcion"
    __table_args__ = (UniqueConstraint("componente_id", "producto_id", name="uq_combo_opcion"),)

    componente_id = Column(BigInteger, ForeignKey("combo_componente.id", name="fk_combo_opcion_componente"), nullable=False, index=True)
    producto_id = Column(BigInteger, ForeignKey("producto.id", name="fk_combo_opcion_producto"), nullable=False)
    # Lo que suma al precio del combo elegir esta opción: "gaseosa grande +2.000"
    precio_extra = Column(Integer, nullable=False, default=0)
    orden = Column(Integer, nullable=False, default=0)
