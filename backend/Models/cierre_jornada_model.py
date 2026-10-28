from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, BigInteger, ForeignKey, Date, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

# Jornada operativa cerrada: no admite más cobros ni órdenes (RN-CAJ-07, doc 20 sección 8)
class CierreJornadaModel(DeRestaurante, BASE):

    __tablename__ = "cierre_jornada"
    __table_args__ = (UniqueConstraint("restaurante_id", "jornada", name="uq_cierre_jornada"),)

    jornada = Column(Date, nullable=False)
    cerrado_por = Column(BigInteger, ForeignKey("usuario.id"), nullable=True)
    # Totales congelados al cerrar
    resumen = Column(JSONB, nullable=False)
