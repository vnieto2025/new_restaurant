from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Integer, BigInteger, Numeric, ForeignKey

# Línea del documento con su impuesto ya desglosado (sale de la cuenta pagada, RN-FAC-01)
class DocumentoVentaLineaModel(DeRestaurante, BASE):

    __tablename__ = "documento_venta_linea"

    documento_id = Column(BigInteger, ForeignKey("documento_venta.id"), nullable=False, index=True)
    descripcion = Column(String(250), nullable=False)
    cantidad = Column(Integer, nullable=False)
    # Precio con impuesto incluido (ADR-021)
    precio_unitario = Column(BigInteger, nullable=False)
    descuento = Column(BigInteger, nullable=False, default=0)
    total = Column(BigInteger, nullable=False)
    base = Column(BigInteger, nullable=False)
    impuesto_id = Column(BigInteger, ForeignKey("impuesto.id"), nullable=True)
    impuesto_nombre = Column(String(60), nullable=True)
    porcentaje = Column(Numeric(6, 3), nullable=False, default=0)
    impuesto_valor = Column(BigInteger, nullable=False, default=0)
