from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, BigInteger, Numeric, ForeignKey

# Ítem de una compra en la unidad de compra; el factor la convierte a la unidad base (RN-COM-04)
class CompraLineaModel(DeRestaurante, BASE):

    __tablename__ = "compra_linea"

    compra_id = Column(BigInteger, ForeignKey("compra.id", name="fk_compra_linea_compra"), nullable=False, index=True)
    insumo_id = Column(BigInteger, ForeignKey("insumo.id", name="fk_compra_linea_insumo"), nullable=False, index=True)
    presentacion_id = Column(BigInteger, ForeignKey("insumo_presentacion.id", name="fk_compra_linea_presentacion",
                                                    ondelete="SET NULL"), nullable=True)
    # Copia de la presentación al comprar: si luego cambia, la compra no cambia
    presentacion_nombre = Column(String(60), nullable=True)
    factor = Column(Numeric(16, 3), nullable=False, default=1)
    cantidad = Column(Numeric(16, 3), nullable=False)
    cantidad_recibida = Column(Numeric(16, 3), nullable=False, default=0)
    # Precio por unidad de compra con impuestos incluidos
    precio_unitario = Column(Numeric(16, 4), nullable=False)
    impuesto_porcentaje = Column(Numeric(5, 2), nullable=False, default=0)
    total = Column(BigInteger, nullable=False, default=0)
    novedad = Column(String(200), nullable=True)
