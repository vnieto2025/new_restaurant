from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Integer, BigInteger, ForeignKey, DateTime, Date, Text, UniqueConstraint

CANALES = ["tablet", "qr_mesa", "qr_rapido", "mostrador", "domicilio"]

# Solicitud de productos de un cliente por cualquier canal (doc 15)
class OrdenModel(DeRestaurante, BASE):

    __tablename__ = "orden"
    __table_args__ = (
        # Un reintento con la misma clave devuelve la orden original (RG-20)
        UniqueConstraint("restaurante_id", "clave_idempotencia", name="uq_orden_idempotencia"),
        UniqueConstraint("restaurante_id", "jornada", "numero", name="uq_orden_numero"),
    )

    numero = Column(Integer, nullable=False)
    jornada = Column(Date, nullable=False, index=True)
    canal = Column(String(15), nullable=False)
    zona_id = Column(BigInteger, ForeignKey("zona.id"), nullable=False, index=True)
    mesa_id = Column(BigInteger, ForeignKey("mesa.id"), nullable=False, index=True)
    sesion_mesa_id = Column(BigInteger, ForeignKey("sesion_mesa.id"), nullable=False, index=True)
    # Responsable de la atención; vacío en órdenes de QR hasta que un mesero las aprueba
    mesero_id = Column(BigInteger, ForeignKey("usuario.id"), nullable=True)
    # Quien la registró en el sistema; vacío si la creó el cliente desde el QR
    creado_por = Column(BigInteger, ForeignKey("usuario.id"), nullable=True)
    # Cliente registrado (opcional); nombre y teléfono se copian igual para la operación del día
    cliente_id = Column(BigInteger, ForeignKey("cliente.id"), nullable=True, index=True)
    cliente_nombre = Column(String(100), nullable=True)
    cliente_telefono = Column(String(30), nullable=True)
    notas = Column(Text, nullable=True)
    clave_idempotencia = Column(String(80), nullable=False)
    # Token opaco para que el cliente siga su orden sin exponer el id (RN-API-04)
    token_seguimiento = Column(String(64), nullable=False, unique=True)
    moneda = Column(String(3), nullable=False, default="COP")
    # Suma de los ítems no cancelados, en pesos
    total = Column(BigInteger, nullable=False, default=0)
    aprobada_por = Column(BigInteger, ForeignKey("usuario.id"), nullable=True)
    aprobada_en = Column(DateTime(timezone=True), nullable=True)
