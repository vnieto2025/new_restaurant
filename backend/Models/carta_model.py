from Config.db import BASE
from Models.base import DeRestaurante, BorradoLogico
from sqlalchemy import Column, String, Boolean, UniqueConstraint

class CartaModel(DeRestaurante, BorradoLogico, BASE):

    __tablename__ = "carta"
    __table_args__ = (UniqueConstraint("restaurante_id", "nombre", name="uq_carta_nombre"),)

    nombre = Column(String(80), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
