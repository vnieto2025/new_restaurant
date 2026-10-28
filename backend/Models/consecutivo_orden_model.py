from Config.db import BASE
from sqlalchemy import Column, BigInteger, Integer, Date, ForeignKey

# Último número de orden usado por restaurante y jornada (#001, #002...)
class ConsecutivoOrdenModel(BASE):

    __tablename__ = "consecutivo_orden"

    restaurante_id = Column(BigInteger, ForeignKey("restaurante.id"), primary_key=True)
    jornada = Column(Date, primary_key=True)
    ultimo = Column(Integer, nullable=False, default=0)
