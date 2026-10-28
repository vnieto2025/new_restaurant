from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Boolean, Integer, UniqueConstraint

TIPOS_MEDIO = ["efectivo", "tarjeta", "transferencia", "otro", "en_linea"]
# Medios que solo registra el sistema (pasarela de pagos), no el cajero
MEDIOS_SISTEMA = ["en_linea"]

# Efectivo, datáfono, transferencia, Nequi... (doc 20). Solo el efectivo entra al arqueo.
class MedioPagoModel(DeRestaurante, BASE):

    __tablename__ = "medio_pago"
    __table_args__ = (UniqueConstraint("restaurante_id", "nombre", name="uq_medio_pago_nombre"),)

    nombre = Column(String(40), nullable=False)
    tipo = Column(String(15), nullable=False, default="otro")
    # Pide número de referencia o aprobación al cobrar
    pide_referencia = Column(Boolean, nullable=False, default=False)
    orden = Column(Integer, nullable=False, default=0)
    activo = Column(Boolean, nullable=False, default=True)
