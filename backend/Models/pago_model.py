from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, BigInteger, ForeignKey, DateTime, UniqueConstraint

# Dinero que cubre total o parte de una cuenta. No se edita: se anula con motivo (RN-CAJ-05, RG-12)
class PagoModel(DeRestaurante, BASE):

    __tablename__ = "pago"
    __table_args__ = (UniqueConstraint("restaurante_id", "clave_idempotencia", name="uq_pago_idempotencia"),)

    cuenta_id = Column(BigInteger, ForeignKey("cuenta.id"), nullable=False, index=True)
    # Vacío solo en pagos en línea que llegan sin turno de caja abierto (no son efectivo del cajón)
    turno_caja_id = Column(BigInteger, ForeignKey("turno_caja.id"), nullable=True, index=True)
    medio_pago_id = Column(BigInteger, ForeignKey("medio_pago.id"), nullable=False)
    # Lo que se abona a la cuenta
    monto = Column(BigInteger, nullable=False)
    # Solo efectivo: lo que entregó el cliente y lo que se le devolvió
    recibido = Column(BigInteger, nullable=True)
    cambio = Column(BigInteger, nullable=True)
    referencia = Column(String(60), nullable=True)
    # aplicado, anulado
    estado = Column(String(10), nullable=False, default="aplicado")
    usuario_id = Column(BigInteger, ForeignKey("usuario.id"), nullable=True)
    clave_idempotencia = Column(String(90), nullable=False)
    anulado_en = Column(DateTime(timezone=True), nullable=True)
    anulado_por = Column(BigInteger, ForeignKey("usuario.id"), nullable=True)
    anulado_motivo = Column(String(200), nullable=True)
