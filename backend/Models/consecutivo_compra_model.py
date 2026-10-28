from Config.db import BASE
from sqlalchemy import Column, BigInteger, Integer, ForeignKey

# Último número de compra usado por restaurante
class ConsecutivoCompraModel(BASE):

    __tablename__ = "consecutivo_compra"

    restaurante_id = Column(BigInteger, ForeignKey("restaurante.id", name="fk_consecutivo_compra_restaurante"), primary_key=True)
    ultimo = Column(Integer, nullable=False, default=0)
