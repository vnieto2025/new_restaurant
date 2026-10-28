from Config.db import BASE
from Models.base import Registro
from sqlalchemy import Column, String

# Hasta dónde llega lo que ve un rol (doc 29, sección 4)
ALCANCES = ["plataforma", "empresa", "restaurante", "zona", "punto"]

class RolModel(Registro, BASE):

    __tablename__ = "rol"

    # Roles fijos del sistema en el MVP (ADR-017)
    codigo = Column(String(30), nullable=False, unique=True)
    nombre = Column(String(100), nullable=False)
    alcance = Column(String(15), nullable=False)
