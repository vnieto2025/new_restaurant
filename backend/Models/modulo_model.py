from Config.db import BASE
from Models.base import Registro
from sqlalchemy import Column, String, Boolean

class ModuloModel(Registro, BASE):

    __tablename__ = "modulo"

    # base, pedidos, caja, inventario... (doc 02A)
    codigo = Column(String(30), nullable=False, unique=True)
    nombre = Column(String(100), nullable=False)
    # Códigos de los módulos que requiere, separados por coma
    depende_de = Column(String(200), nullable=True)
    # El módulo base siempre está activo
    obligatorio = Column(Boolean, nullable=False, default=False)
