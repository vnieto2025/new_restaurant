from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, BigInteger, Numeric, ForeignKey

class RecetaLineaModel(DeRestaurante, BASE):

    __tablename__ = "receta_linea"

    receta_id = Column(BigInteger, ForeignKey("receta.id"), nullable=False, index=True)
    insumo_id = Column(BigInteger, ForeignKey("insumo.id"), nullable=False)
    cantidad = Column(Numeric(16, 3), nullable=False)
    # Merma técnica del ingrediente: se descuenta cantidad × (1 + merma/100)
    merma = Column(Numeric(5, 2), nullable=False, default=0)
