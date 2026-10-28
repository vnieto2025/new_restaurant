from Config.db import BASE
from Models.base import Registro, BorradoLogico
from sqlalchemy import Column, String, Text, Boolean, BigInteger, ForeignKey, DateTime, Index, text

class UsuarioModel(Registro, BorradoLogico, BASE):

    __tablename__ = "usuario"
    __table_args__ = (
        Index("uq_usuario_pin_empresa", "empresa_id", "pin_hash", unique=True, postgresql_where=text("pin_hash IS NOT NULL")),
    )

    # Vacío solo para el superadministrador de plataforma
    empresa_id = Column(BigInteger, ForeignKey("empresa.id"), nullable=True, index=True)
    # Nombre de acceso, único en toda la plataforma (se guarda en minúsculas)
    usuario = Column(String(60), nullable=False, unique=True)
    nombre = Column(String(150), nullable=False)
    documento = Column(String(30), nullable=True)
    correo = Column(String(150), nullable=True)
    password = Column(Text, nullable=False)
    # PIN corto para identificarse en una tablet o pantalla autorizada (hash, nunca en claro)
    pin_hash = Column(Text, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    ultimo_acceso = Column(DateTime(timezone=True), nullable=True)
