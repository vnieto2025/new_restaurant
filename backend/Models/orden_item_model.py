from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Integer, BigInteger, ForeignKey, Text, Numeric, Boolean

ESTADOS_ITEM = ["pendiente_aprobacion", "nuevo", "en_proceso", "despachado", "entregado", "cancelado"]

# Ítem de la orden. Es también el ítem de la comanda: el estado vive aquí (ADR-006)
class OrdenItemModel(DeRestaurante, BASE):

    __tablename__ = "orden_item"

    orden_id = Column(BigInteger, ForeignKey("orden.id"), nullable=False, index=True)
    producto_id = Column(BigInteger, ForeignKey("producto.id"), nullable=False)
    # Instantánea del producto al crear la orden (RG-13)
    nombre_producto = Column(String(100), nullable=False)
    precio_unitario = Column(BigInteger, nullable=False)
    cantidad = Column(Integer, nullable=False)
    total = Column(BigInteger, nullable=False)
    # Impuesto vigente al pedir; el documento de venta lo desglosa del precio (ADR-021)
    impuesto_id = Column(BigInteger, ForeignKey("impuesto.id"), nullable=True)
    impuesto_porcentaje = Column(Numeric(6, 3), nullable=True)
    # El inventario se descontó al pasar a en_proceso (ADR-013); si luego se cancela, es merma
    inventario_descontado = Column(Boolean, nullable=False, default=False, server_default="false")
    nota = Column(Text, nullable=True)
    # Destino resuelto al crear el ítem; vacío = despacho directo (doc 19, sección 3)
    punto_produccion_id = Column(BigInteger, ForeignKey("punto_produccion.id"), nullable=True)
    comanda_id = Column(BigInteger, ForeignKey("comanda.id"), nullable=True, index=True)
    # Clave de idempotencia del envío que creó el ítem: un reintento no lo duplica (RG-20)
    lote = Column(String(80), nullable=False, index=True)
    estado = Column(String(25), nullable=False, index=True)
    motivo_cancelacion = Column(String(200), nullable=True)
    # cancelacion o perdida: se distinguen por el motivo (doc 15, sección 6)
    tipo_cancelacion = Column(String(15), nullable=True)
