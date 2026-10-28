from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, Boolean, BigInteger, Numeric, DateTime, ForeignKey, UniqueConstraint

# Qué insumo vende cada proveedor, en qué presentación y a qué precio la última vez (doc 24, sección 2).
# El histórico de precios sale de las líneas de compra, que no se editan (RN-PRV-02)
class ProveedorInsumoModel(DeRestaurante, BASE):

    __tablename__ = "proveedor_insumo"
    __table_args__ = (UniqueConstraint("proveedor_id", "insumo_id", name="uq_proveedor_insumo"),)

    proveedor_id = Column(BigInteger, ForeignKey("proveedor.id", name="fk_proveedor_insumo_proveedor"), nullable=False, index=True)
    insumo_id = Column(BigInteger, ForeignKey("insumo.id", name="fk_proveedor_insumo_insumo"), nullable=False, index=True)
    presentacion_id = Column(BigInteger, ForeignKey("insumo_presentacion.id", name="fk_proveedor_insumo_presentacion",
                                                    ondelete="SET NULL"), nullable=True)
    preferido = Column(Boolean, nullable=False, default=False)
    # Precio de la presentación y costo por unidad base en la última compra recibida
    ultimo_precio = Column(Numeric(16, 4), nullable=True)
    ultimo_costo_unitario = Column(Numeric(16, 4), nullable=True)
    ultima_compra_en = Column(DateTime(timezone=True), nullable=True)
