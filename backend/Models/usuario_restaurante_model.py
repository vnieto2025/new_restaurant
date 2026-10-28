from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, BigInteger, ForeignKey, UniqueConstraint

# Restaurantes a los que tiene acceso un usuario (el admin de empresa los ve todos)
class UsuarioRestauranteModel(DeRestaurante, BASE):

    __tablename__ = "usuario_restaurante"
    __table_args__ = (UniqueConstraint("usuario_id", "restaurante_id", name="uq_usuario_restaurante"),)

    usuario_id = Column(BigInteger, ForeignKey("usuario.id"), nullable=False, index=True)
