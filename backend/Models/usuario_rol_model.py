from Config.db import BASE
from Models.base import Registro
from sqlalchemy import Column, BigInteger, ForeignKey, UniqueConstraint

# Un usuario puede tener varios roles; sus permisos son la unión (RN-PER-03)
class UsuarioRolModel(Registro, BASE):

    __tablename__ = "usuario_rol"
    __table_args__ = (UniqueConstraint("usuario_id", "rol_id", name="uq_usuario_rol"),)

    usuario_id = Column(BigInteger, ForeignKey("usuario.id"), nullable=False, index=True)
    rol_id = Column(BigInteger, ForeignKey("rol.id"), nullable=False)
