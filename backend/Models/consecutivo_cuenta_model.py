from Config.db import BASE
from sqlalchemy import Column, BigInteger, Integer, ForeignKey

# Último número de comprobante usado por restaurante (continuo, no se reinicia)
class ConsecutivoCuentaModel(BASE):

    __tablename__ = "consecutivo_cuenta"

    restaurante_id = Column(BigInteger, ForeignKey("restaurante.id"), primary_key=True)
    ultimo = Column(Integer, nullable=False, default=0)
