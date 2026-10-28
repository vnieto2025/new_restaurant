from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Boolean, BigInteger, ForeignKey, DateTime, Date, Index, text

# Cuándo estuvo activo un mesero en una jornada (doc 08A, sección 2). Es operativo, no control de asistencia.
class TurnoMeseroModel(DeRestaurante, BASE):

    __tablename__ = "turno_mesero"
    __table_args__ = (
        Index("uq_turno_mesero_abierto", "usuario_id", "restaurante_id", unique=True,
              postgresql_where=text("estado = 'abierto'")),
    )

    usuario_id = Column(BigInteger, ForeignKey("usuario.id"), nullable=False, index=True)
    jornada = Column(Date, nullable=False)
    inicio = Column(DateTime(timezone=True), nullable=False)
    fin = Column(DateTime(timezone=True), nullable=True)
    # abierto, cerrado
    estado = Column(String(10), nullable=False, default="abierto")
    # Cerrado por el cierre de jornada y no por el mesero (RN-MSR-03)
    cierre_automatico = Column(Boolean, nullable=False, default=False)
    dispositivo_id = Column(BigInteger, ForeignKey("dispositivo.id"), nullable=True)
