from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, BigInteger, ForeignKey, Date

MEDIOS_SUSCRIPCION = ["transferencia", "efectivo", "tarjeta", "otro"]

# Pago del restaurante por el servicio (doc 42, sección 6). Lo registra el proveedor del software a mano.
class PagoSuscripcionModel(DeRestaurante, BASE):

    __tablename__ = "pago_suscripcion"

    contrato_id = Column(BigInteger, ForeignKey("contrato.id", name="fk_pago_suscripcion_contrato"), nullable=False, index=True)
    valor = Column(BigInteger, nullable=False)
    fecha = Column(Date, nullable=False)
    # Periodo que cubre: el vencimiento avanza con cada pago
    periodo_desde = Column(Date, nullable=False)
    periodo_hasta = Column(Date, nullable=False)
    medio = Column(String(15), nullable=False)
    referencia = Column(String(60), nullable=True)
    # Número de la factura del servicio, emitida por fuera
    factura = Column(String(40), nullable=True)
    registrado_por = Column(BigInteger, ForeignKey("usuario.id", name="fk_pago_suscripcion_usuario"), nullable=True)
