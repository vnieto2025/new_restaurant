from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Boolean

# Punto de cobro. En el MVP hay una por restaurante, preparado para varias (doc 20, preguntas abiertas)
class CajaModel(DeRestaurante, BASE):

    __tablename__ = "caja"

    nombre = Column(String(40), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
