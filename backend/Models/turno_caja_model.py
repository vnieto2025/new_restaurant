from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, BigInteger, ForeignKey, DateTime, Date, Index, text

# Periodo en que un cajero responde por una caja (doc 20, sección 2)
class TurnoCajaModel(DeRestaurante, BASE):

    __tablename__ = "turno_caja"
    __table_args__ = (
        # Una caja tiene a lo sumo un turno abierto (RN-CAJ-02)
        Index("uq_turno_abierto_caja", "caja_id", unique=True, postgresql_where=text("estado = 'abierto'")),
    )

    caja_id = Column(BigInteger, ForeignKey("caja.id"), nullable=False, index=True)
    usuario_id = Column(BigInteger, ForeignKey("usuario.id"), nullable=False)
    # abierto, cerrado
    estado = Column(String(10), nullable=False, default="abierto")
    jornada = Column(Date, nullable=False)
    abierto_en = Column(DateTime(timezone=True), nullable=False)
    fondo_inicial = Column(BigInteger, nullable=False, default=0)
    cerrado_en = Column(DateTime(timezone=True), nullable=True)
    cerrado_por = Column(BigInteger, ForeignKey("usuario.id"), nullable=True)
    efectivo_esperado = Column(BigInteger, nullable=True)
    efectivo_contado = Column(BigInteger, nullable=True)
    # La diferencia de arqueo se guarda siempre (RN-CAJ-06)
    diferencia = Column(BigInteger, nullable=True)
    observacion = Column(String(250), nullable=True)
