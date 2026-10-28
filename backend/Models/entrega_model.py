from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Integer, BigInteger, Numeric, Boolean, DateTime, ForeignKey, UniqueConstraint

ESTADOS_ENTREGA = ["pendiente_asignacion", "asignada", "en_camino", "entregada", "fallida"]
DECISIONES_FALLO = ["reintento", "cancelacion", "perdida"]

# Entrega a domicilio ligada a la orden; no reemplaza los estados de la orden (doc 15B, sección 4)
class EntregaModel(DeRestaurante, BASE):

    __tablename__ = "entrega"
    __table_args__ = (UniqueConstraint("orden_id", name="uq_entrega_orden"),)

    orden_id = Column(BigInteger, ForeignKey("orden.id", name="fk_entrega_orden"), nullable=False)
    sesion_mesa_id = Column(BigInteger, ForeignKey("sesion_mesa.id", name="fk_entrega_sesion"), nullable=False, index=True)
    zona_envio_id = Column(BigInteger, ForeignKey("zona_envio.id", name="fk_entrega_zona_envio"), nullable=False)
    # Datos de entrega copiados al pedir (RN-DOM-01)
    cliente_nombre = Column(String(100), nullable=False)
    telefono = Column(String(30), nullable=False)
    direccion = Column(String(200), nullable=False)
    barrio = Column(String(80), nullable=True)
    indicaciones = Column(String(250), nullable=True)
    # Tarifa cobrada al cliente con su impuesto, y pago reconocido al domiciliario, al momento de pedir
    tarifa = Column(BigInteger, nullable=False, default=0)
    impuesto_id = Column(BigInteger, ForeignKey("impuesto.id", name="fk_entrega_impuesto"), nullable=True)
    impuesto_porcentaje = Column(Numeric(6, 3), nullable=True)
    pago_domiciliario = Column(BigInteger, nullable=False, default=0)
    estado = Column(String(25), nullable=False, default="pendiente_asignacion", index=True)
    domiciliario_id = Column(BigInteger, ForeignKey("domiciliario.id", name="fk_entrega_domiciliario"), nullable=True, index=True)
    intentos = Column(Integer, nullable=False, default=0)
    # Lo que el domiciliario debía cobrar al salir (saldo de la cuenta)
    monto_a_cobrar = Column(BigInteger, nullable=False, default=0)
    contra_entrega = Column(Boolean, nullable=False, default=False)
    # Tiempos para métricas (RN-DOM-05)
    asignada_en = Column(DateTime(timezone=True), nullable=True)
    salida_en = Column(DateTime(timezone=True), nullable=True)
    entregada_en = Column(DateTime(timezone=True), nullable=True)
    fallida_en = Column(DateTime(timezone=True), nullable=True)
    motivo_fallo = Column(String(200), nullable=True)
    decision = Column(String(15), nullable=True)
    # Liquidación que pagó esta entrega al domiciliario (RN-PRP-06)
    liquidacion_id = Column(BigInteger, ForeignKey("liquidacion.id", name="fk_entrega_liquidacion"), nullable=True, index=True)
    rendicion_id = Column(BigInteger, ForeignKey("rendicion.id", name="fk_entrega_rendicion"), nullable=True, index=True)
