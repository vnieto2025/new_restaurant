from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, BigInteger, String, Date, DateTime, UniqueConstraint

ESTADOS_CONTRATO = ["prueba", "activo", "suspendido", "cancelado"]

class ContratoModel(DeRestaurante, BASE):

    __tablename__ = "contrato"
    # El contrato pertenece al restaurante, no a la empresa (doc 02A)
    __table_args__ = (UniqueConstraint("restaurante_id", name="uq_contrato_restaurante"),)

    estado = Column(String(15), nullable=False, default="prueba")
    fecha_inicio = Column(Date, nullable=False)
    # Fin de la prueba o de la vigencia; vacío = sin vencimiento
    fecha_fin = Column(Date, nullable=True)
    # Desde cuándo corre el plazo para descargar los datos (doc 41, sección 6)
    cancelado_en = Column(DateTime(timezone=True), nullable=True)
    # Cobro del servicio (doc 42, sección 6). En el MVP es manual: transferencia y factura emitida a mano
    mensualidad = Column(BigInteger, nullable=True)
    proximo_vencimiento = Column(Date, nullable=True)
    notas_comerciales = Column(String(300), nullable=True)
