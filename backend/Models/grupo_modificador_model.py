from Config.db import BASE
from Models.base import DeRestaurante, BorradoLogico
from sqlalchemy import Column, String, Boolean, Integer, UniqueConstraint

# Opciones relacionadas con reglas simples: "Adicionales", "Punto de cocción" (doc 12, sección 3)
class GrupoModificadorModel(DeRestaurante, BorradoLogico, BASE):

    __tablename__ = "grupo_modificador"
    __table_args__ = (UniqueConstraint("restaurante_id", "nombre", name="uq_grupo_modificador_nombre"),)

    nombre = Column(String(60), nullable=False)
    # Mínimo > 0 = obligatorio elegir (RN-PRO-03); máximo = cuántas opciones se pueden marcar
    minimo = Column(Integer, nullable=False, default=0)
    maximo = Column(Integer, nullable=False, default=1)
    activo = Column(Boolean, nullable=False, default=True)
