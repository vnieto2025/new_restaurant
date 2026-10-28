from Config.db import BASE
from Models.base import DeRestaurante, BorradoLogico
from sqlalchemy import Column, String, Boolean, Integer, BigInteger, ForeignKey, UniqueConstraint

TIPOS_MESA = ["normal", "externa"]

class MesaModel(DeRestaurante, BorradoLogico, BASE):

    __tablename__ = "mesa"
    # Nombres únicos dentro de una zona (RN-MES-06)
    __table_args__ = (UniqueConstraint("zona_id", "nombre", name="uq_mesa_nombre"),)

    zona_id = Column(BigInteger, ForeignKey("zona.id"), nullable=False, index=True)
    nombre = Column(String(40), nullable=False)
    capacidad = Column(Integer, nullable=True)
    tipo = Column(String(10), nullable=False, default="normal")
    orden = Column(Integer, nullable=False, default=0)
    activo = Column(Boolean, nullable=False, default=True)
    # Fuera de servicio temporal: rechaza órdenes por cualquier canal (RN-MES-07)
    bloqueada = Column(Boolean, nullable=False, default=False)
