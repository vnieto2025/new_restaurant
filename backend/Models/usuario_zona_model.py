from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, BigInteger, ForeignKey, UniqueConstraint

# Zonas asignadas a un mesero (doc 08A)
class UsuarioZonaModel(DeRestaurante, BASE):

    __tablename__ = "usuario_zona"
    __table_args__ = (UniqueConstraint("usuario_id", "zona_id", name="uq_usuario_zona"),)

    usuario_id = Column(BigInteger, ForeignKey("usuario.id"), nullable=False, index=True)
    zona_id = Column(BigInteger, ForeignKey("zona.id"), nullable=False)
