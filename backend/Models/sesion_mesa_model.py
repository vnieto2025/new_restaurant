from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Boolean, BigInteger, ForeignKey, DateTime, Index, text

# Agrupa las órdenes de una mesa hasta que se cierra la cuenta (doc 10A, sección 6)
class SesionMesaModel(DeRestaurante, BASE):

    __tablename__ = "sesion_mesa"
    __table_args__ = (
        # Una mesa normal tiene como máximo una sesión abierta; la externa admite muchas (doc 10)
        Index(
            "uq_sesion_abierta_mesa",
            "mesa_id",
            unique=True,
            postgresql_where=text("estado = 'abierta' AND es_externa = false"),
        ),
    )

    mesa_id = Column(BigInteger, ForeignKey("mesa.id"), nullable=False, index=True)
    zona_id = Column(BigInteger, ForeignKey("zona.id"), nullable=False)
    es_externa = Column(Boolean, nullable=False, default=False)
    # abierta, cerrada
    estado = Column(String(10), nullable=False, default="abierta")
    mesero_id = Column(BigInteger, ForeignKey("usuario.id"), nullable=True)
    abierta_en = Column(DateTime(timezone=True), nullable=False)
    cerrada_en = Column(DateTime(timezone=True), nullable=True)
    cerrada_por = Column(BigInteger, ForeignKey("usuario.id"), nullable=True)
