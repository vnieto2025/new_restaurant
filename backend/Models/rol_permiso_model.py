from Config.db import BASE
from Models.base import Registro
from sqlalchemy import Column, BigInteger, ForeignKey, UniqueConstraint

class RolPermisoModel(Registro, BASE):

    __tablename__ = "rol_permiso"
    __table_args__ = (UniqueConstraint("rol_id", "permiso_id", name="uq_rol_permiso"),)

    rol_id = Column(BigInteger, ForeignKey("rol.id"), nullable=False, index=True)
    permiso_id = Column(BigInteger, ForeignKey("permiso.id"), nullable=False)
