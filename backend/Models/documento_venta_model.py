from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Integer, BigInteger, ForeignKey, DateTime, Date, UniqueConstraint

ESTADOS_DOCUMENTO = ["pendiente", "emitida", "aceptada", "rechazada", "anulada"]

# Documento de venta (POS electrónico, factura o nota crédito). Emitido no se edita (RG-07)
class DocumentoVentaModel(DeRestaurante, BASE):

    __tablename__ = "documento_venta"
    __table_args__ = (UniqueConstraint("resolucion_id", "numero", name="uq_documento_numero"),)

    tipo = Column(String(15), nullable=False, index=True)
    cuenta_id = Column(BigInteger, ForeignKey("cuenta.id"), nullable=True, index=True)
    # La nota crédito apunta al documento que anula
    documento_origen_id = Column(BigInteger, ForeignKey("documento_venta.id"), nullable=True, index=True)
    motivo = Column(String(200), nullable=True)
    resolucion_id = Column(BigInteger, ForeignKey("resolucion.id"), nullable=False)
    prefijo = Column(String(10), nullable=False, default="")
    numero = Column(BigInteger, nullable=False)
    estado = Column(String(12), nullable=False, default="pendiente", index=True)
    jornada = Column(Date, nullable=False, index=True)
    # Receptor: consumidor final o el cliente que pidió factura a su nombre
    cliente_id = Column(BigInteger, ForeignKey("cliente.id"), nullable=True)
    receptor_nombre = Column(String(150), nullable=False)
    receptor_tipo_documento = Column(String(10), nullable=True)
    receptor_documento = Column(String(30), nullable=True)
    receptor_correo = Column(String(150), nullable=True)
    # Valores en pesos: total = base + impuestos. La propina es informativa y no hace parte (RN-FAC-03)
    base = Column(BigInteger, nullable=False)
    impuestos = Column(BigInteger, nullable=False)
    descuento = Column(BigInteger, nullable=False, default=0)
    total = Column(BigInteger, nullable=False)
    propina = Column(BigInteger, nullable=False, default=0)
    # Respuesta del proveedor
    cufe = Column(String(120), nullable=True)
    proveedor_referencia = Column(String(80), nullable=True)
    proveedor_mensaje = Column(String(500), nullable=True)
    # Cola de emisión con reintentos: la venta nunca espera al proveedor (RN-FAC-06)
    intentos = Column(Integer, nullable=False, default=0)
    proximo_intento_en = Column(DateTime(timezone=True), nullable=True, index=True)
    enviado_en = Column(DateTime(timezone=True), nullable=True)
    aceptado_en = Column(DateTime(timezone=True), nullable=True)
    creado_por = Column(BigInteger, ForeignKey("usuario.id"), nullable=True)
