from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Boolean, Integer, BigInteger, Date, DateTime, ForeignKey, UniqueConstraint

ESTADOS_COMPRA = ["borrador", "solicitada", "parcial", "recibida", "cerrada", "anulada"]
FORMAS_PAGO_COMPRA = ["contado", "credito", "caja"]

# Compra formal (orden al proveedor) o rápida (plaza, tienda) (doc 23)
class CompraModel(DeRestaurante, BASE):

    __tablename__ = "compra"
    __table_args__ = (UniqueConstraint("restaurante_id", "numero", name="uq_compra_numero"),)

    numero = Column(Integer, nullable=False)
    # Sin proveedor fijo es "compra de plaza"; el nombre queda como se registró
    proveedor_id = Column(BigInteger, ForeignKey("proveedor.id", name="fk_compra_proveedor"), nullable=True, index=True)
    proveedor_nombre = Column(String(100), nullable=False)
    estado = Column(String(12), nullable=False, default="borrador", index=True)
    es_rapida = Column(Boolean, nullable=False, default=False)
    fecha = Column(Date, nullable=False)
    entrega_esperada = Column(Date, nullable=True)
    forma_pago = Column(String(10), nullable=False, default="contado")
    # Pesos con impuestos incluidos: lo pedido, lo recibido y la parte de impuestos que discrimina el proveedor
    total = Column(BigInteger, nullable=False, default=0)
    valor_recibido = Column(BigInteger, nullable=False, default=0)
    impuestos = Column(BigInteger, nullable=False, default=0)
    factura_proveedor = Column(String(40), nullable=True)
    notas = Column(String(500), nullable=True)
    creado_por = Column(BigInteger, ForeignKey("usuario.id", name="fk_compra_creado_por"), nullable=True)
    solicitada_en = Column(DateTime(timezone=True), nullable=True)
    recibida_en = Column(DateTime(timezone=True), nullable=True)
    recibida_por = Column(BigInteger, ForeignKey("usuario.id", name="fk_compra_recibida_por"), nullable=True)
    cerrada_en = Column(DateTime(timezone=True), nullable=True)
    cerrada_por = Column(BigInteger, ForeignKey("usuario.id", name="fk_compra_cerrada_por"), nullable=True)
    anulada_en = Column(DateTime(timezone=True), nullable=True)
    anulada_por = Column(BigInteger, ForeignKey("usuario.id", name="fk_compra_anulada_por"), nullable=True)
    motivo_anulacion = Column(String(200), nullable=True)
