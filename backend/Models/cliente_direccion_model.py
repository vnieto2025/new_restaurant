from Config.db import BASE
from Models.base import DeEmpresa
from sqlalchemy import Column, String, Boolean, BigInteger, ForeignKey

class ClienteDireccionModel(DeEmpresa, BASE):

    __tablename__ = "cliente_direccion"

    cliente_id = Column(BigInteger, ForeignKey("cliente.id"), nullable=False, index=True)
    # "Casa", "Trabajo"
    nombre = Column(String(40), nullable=True)
    direccion = Column(String(200), nullable=False)
    indicaciones = Column(String(250), nullable=True)
    barrio = Column(String(80), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
