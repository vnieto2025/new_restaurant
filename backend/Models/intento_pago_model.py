from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, BigInteger, DateTime, Date, ForeignKey, UniqueConstraint

ESTADOS_INTENTO = ["pendiente", "aprobado", "rechazado", "expirado", "reembolsado", "parcial"]

# Intento de pago en línea con monto fijo (RN-PAG-02). Su resultado solo lo decide la notificación
# firmada de la pasarela, nunca el navegador del cliente (RN-PAG-01)
class IntentoPagoModel(DeRestaurante, BASE):

    __tablename__ = "intento_pago"
    __table_args__ = (
        UniqueConstraint("referencia", name="uq_intento_pago_referencia"),
        UniqueConstraint("token", name="uq_intento_pago_token"),
        UniqueConstraint("restaurante_id", "clave_idempotencia", name="uq_intento_pago_clave"),
    )

    cuenta_id = Column(BigInteger, ForeignKey("cuenta.id", name="fk_intento_pago_cuenta"), nullable=False, index=True)
    # Referencia que viaja a la pasarela y token opaco para que el cliente consulte su pago
    referencia = Column(String(40), nullable=False)
    token = Column(String(64), nullable=False)
    clave_idempotencia = Column(String(80), nullable=False)
    pasarela = Column(String(30), nullable=False)
    # Pesos: lo que se cobra (saldo + propina) congelado al crear el intento
    monto = Column(BigInteger, nullable=False)
    propina = Column(BigInteger, nullable=False, default=0)
    estado = Column(String(12), nullable=False, default="pendiente", index=True)
    origen = Column(String(10), nullable=False)
    url_pago = Column(String(300), nullable=True)
    transaccion_id = Column(String(80), nullable=True)
    expira_en = Column(DateTime(timezone=True), nullable=False)
    aprobado_en = Column(DateTime(timezone=True), nullable=True)
    # Lo que se abonó a la cuenta y lo que sobró porque la cuenta cambió o ya estaba pagada
    pago_id = Column(BigInteger, ForeignKey("pago.id", name="fk_intento_pago_pago"), nullable=True)
    aplicado = Column(BigInteger, nullable=False, default=0)
    excedente = Column(BigInteger, nullable=False, default=0)
    reembolsado = Column(BigInteger, nullable=False, default=0)
    motivo_reembolso = Column(String(200), nullable=True)
    # Conciliación con el reporte de la pasarela (doc 20A, sección 5)
    comision = Column(BigInteger, nullable=True)
    fecha_abono = Column(Date, nullable=True)
    nota_conciliacion = Column(String(200), nullable=True)
