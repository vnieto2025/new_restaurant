from Config.db import BASE
from Models.base import DeEmpresa
from sqlalchemy import Column, BigInteger, ForeignKey, UniqueConstraint

class ContratoModuloModel(DeEmpresa, BASE):

    __tablename__ = "contrato_modulo"
    __table_args__ = (UniqueConstraint("contrato_id", "modulo_id", name="uq_contrato_modulo"),)

    contrato_id = Column(BigInteger, ForeignKey("contrato.id"), nullable=False, index=True)
    modulo_id = Column(BigInteger, ForeignKey("modulo.id"), nullable=False)
