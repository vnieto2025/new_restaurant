from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Boolean, Integer, BigInteger, ForeignKey, DateTime, Date, UniqueConstraint

ESTADOS_CUENTA = ["abierta", "pagada", "anulada"]

# Lo que se cobra: todas las órdenes de una sesión de mesa (doc 20; ADR-027)
class CuentaModel(DeRestaurante, BASE):

    __tablename__ = "cuenta"
    __table_args__ = (UniqueConstraint("sesion_mesa_id", name="uq_cuenta_sesion"),)

    sesion_mesa_id = Column(BigInteger, ForeignKey("sesion_mesa.id"), nullable=False)
    mesa_id = Column(BigInteger, ForeignKey("mesa.id"), nullable=False, index=True)
    zona_id = Column(BigInteger, ForeignKey("zona.id"), nullable=False)
    # Consecutivo del comprobante, por restaurante; se asigna al pagar
    numero = Column(Integer, nullable=True)
    estado = Column(String(10), nullable=False, default="abierta", index=True)
    # El mesero o el cliente pidió la cuenta
    solicitada = Column(Boolean, nullable=False, default=False)
    solicitada_en = Column(DateTime(timezone=True), nullable=True)
    # Valores en pesos. La propina va aparte de la venta (doc 20, sección 5)
    subtotal = Column(BigInteger, nullable=False, default=0)
    descuento = Column(BigInteger, nullable=False, default=0)
    descuento_motivo = Column(String(200), nullable=True)
    propina = Column(BigInteger, nullable=False, default=0)
    # Tarifa de domicilio, concepto aparte de los ítems (doc 15B, sección 5)
    envio = Column(BigInteger, nullable=False, default=0, server_default="0")
    # Cupones (doc 25A): lo que descuentan sobre los ítems y sobre el domicilio
    descuento_cupon = Column(BigInteger, nullable=False, default=0, server_default="0")
    descuento_envio = Column(BigInteger, nullable=False, default=0, server_default="0")
    # Cliente identificado al cobrar: para cupones personales y el cupón de la próxima visita
    cliente_id = Column(BigInteger, ForeignKey("cliente.id", name="fk_cuenta_cliente"), nullable=True)
    total = Column(BigInteger, nullable=False, default=0)
    # Liquidación que repartió su propina: no se vuelve a liquidar (doc 26A)
    liquidacion_propina_id = Column(BigInteger, ForeignKey("liquidacion.id", name="fk_cuenta_liquidacion"), nullable=True, index=True)
    pagado = Column(BigInteger, nullable=False, default=0)
    # Jornada en que se pagó: con ella se arman los reportes de ventas (doc 26)
    jornada = Column(Date, nullable=True, index=True)
    pagada_en = Column(DateTime(timezone=True), nullable=True)
    turno_caja_id = Column(BigInteger, ForeignKey("turno_caja.id"), nullable=True)
    cobrada_por = Column(BigInteger, ForeignKey("usuario.id"), nullable=True)
    anulada_en = Column(DateTime(timezone=True), nullable=True)
    anulada_por = Column(BigInteger, ForeignKey("usuario.id"), nullable=True)
    anulada_motivo = Column(String(200), nullable=True)
