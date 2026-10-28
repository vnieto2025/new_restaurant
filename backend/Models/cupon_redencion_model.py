from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, BigInteger, ForeignKey, DateTime, UniqueConstraint

# aplicada: en una cuenta abierta (ya cuenta como uso); redimida: la cuenta se pagó;
# quitada: se retiró antes de pagar; revertida: la cuenta se anuló (RN-CUP-03)
ESTADOS_REDENCION = ["aplicada", "redimida", "quitada", "revertida"]
USOS_VIGENTES = ["aplicada", "redimida"]

# Uso de un cupón en una cuenta (doc 25A, sección 4)
class CuponRedencionModel(DeRestaurante, BASE):

    __tablename__ = "cupon_redencion"
    __table_args__ = (UniqueConstraint("cupon_id", "cuenta_id", name="uq_redencion_cupon_cuenta"),)

    cupon_id = Column(BigInteger, ForeignKey("cupon.id", name="fk_redencion_cupon"), nullable=False, index=True)
    cuenta_id = Column(BigInteger, ForeignKey("cuenta.id", name="fk_redencion_cuenta"), nullable=False, index=True)
    cliente_id = Column(BigInteger, ForeignKey("cliente.id", name="fk_redencion_cliente"), nullable=True, index=True)
    # Descuento que da hoy; mientras la cuenta está abierta se recalcula con lo que se pide
    valor = Column(BigInteger, nullable=False, default=0)
    estado = Column(String(10), nullable=False, default="aplicada", index=True)
    canal = Column(String(12), nullable=False)
    # Sin usuario: lo aplicó el cliente desde su celular
    aplicada_por = Column(BigInteger, ForeignKey("usuario.id", name="fk_redencion_usuario"), nullable=True)
    # Por qué no descuenta ahora (la cuenta bajó del mínimo, ya no tiene el producto)
    nota = Column(String(200), nullable=True)
    # Venta neta de la cuenta al pagarse: ventas atribuidas al cupón (doc 25A, sección 6)
    ventas = Column(BigInteger, nullable=False, default=0)
    redimida_en = Column(DateTime(timezone=True), nullable=True)
    revertida_en = Column(DateTime(timezone=True), nullable=True)
    motivo = Column(String(200), nullable=True)
