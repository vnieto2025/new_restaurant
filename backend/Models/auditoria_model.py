from Config.db import BASE
from Models.base import Registro
from sqlalchemy import Column, String, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB

# Quién, cuándo, qué cambió y desde dónde (RG-14, RG-15)
class AuditoriaModel(Registro, BASE):

    __tablename__ = "auditoria"

    empresa_id = Column(BigInteger, ForeignKey("empresa.id"), nullable=True, index=True)
    restaurante_id = Column(BigInteger, ForeignKey("restaurante.id"), nullable=True, index=True)
    usuario_id = Column(BigInteger, ForeignKey("usuario.id"), nullable=True)
    accion = Column(String(60), nullable=False, index=True)
    entidad = Column(String(40), nullable=False)
    entidad_id = Column(BigInteger, nullable=True)
    antes = Column(JSONB, nullable=True)
    despues = Column(JSONB, nullable=True)
    motivo = Column(String(250), nullable=True)
    ip = Column(String(50), nullable=True)
    dispositivo = Column(String(250), nullable=True)
