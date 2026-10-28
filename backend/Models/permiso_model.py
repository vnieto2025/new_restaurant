from Config.db import BASE
from Models.base import Registro
from sqlalchemy import Column, String

class PermisoModel(Registro, BASE):

    __tablename__ = "permiso"

    # Acción concreta: ordenes.crear_mesa, cocina.operar... (doc 29)
    codigo = Column(String(60), nullable=False, unique=True)
    nombre = Column(String(150), nullable=False)
    # Módulo al que pertenece: si no está contratado, el permiso no es efectivo (RN-PER-04)
    modulo = Column(String(30), nullable=False)
