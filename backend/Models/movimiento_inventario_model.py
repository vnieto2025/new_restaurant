from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, BigInteger, Numeric, ForeignKey

TIPOS_MOVIMIENTO = ["entrada", "compra", "anulacion_compra", "consumo", "reverso_consumo", "merma", "ajuste", "produccion",
                    "devolucion"]

# Todo cambio de stock (doc 22, sección 3). No se edita ni se borra
class MovimientoInventarioModel(DeRestaurante, BASE):

    __tablename__ = "movimiento_inventario"

    insumo_id = Column(BigInteger, ForeignKey("insumo.id"), nullable=False, index=True)
    tipo = Column(String(20), nullable=False, index=True)
    # Con signo: positivo entra, negativo sale
    cantidad = Column(Numeric(16, 3), nullable=False)
    costo_unitario = Column(Numeric(16, 4), nullable=False, default=0)
    costo_total = Column(BigInteger, nullable=False, default=0)
    stock_resultante = Column(Numeric(16, 3), nullable=False)
    motivo = Column(String(200), nullable=True)
    orden_item_id = Column(BigInteger, ForeignKey("orden_item.id"), nullable=True, index=True)
    conteo_id = Column(BigInteger, ForeignKey("conteo.id"), nullable=True)
    # Compra u otro documento que lo originó (módulo de compras)
    referencia = Column(String(60), nullable=True)
    compra_id = Column(BigInteger, ForeignKey("compra.id", name="fk_movimiento_inventario_compra"), nullable=True, index=True)
    usuario_id = Column(BigInteger, ForeignKey("usuario.id"), nullable=True)
