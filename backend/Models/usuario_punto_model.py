from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, BigInteger, ForeignKey, UniqueConstraint

# Puntos de producción que atiende un usuario de cocina o bar
class UsuarioPuntoModel(DeRestaurante, BASE):

    __tablename__ = "usuario_punto"
    __table_args__ = (UniqueConstraint("usuario_id", "punto_produccion_id", name="uq_usuario_punto"),)

    usuario_id = Column(BigInteger, ForeignKey("usuario.id"), nullable=False, index=True)
    punto_produccion_id = Column(BigInteger, ForeignKey("punto_produccion.id"), nullable=False)
