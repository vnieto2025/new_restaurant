from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, BigInteger, Numeric, ForeignKey

# Lo que suma (positivo) o resta (negativo) una opción de modificador: "Queso extra" = +30 g de queso
class OpcionInsumoModel(DeRestaurante, BASE):

    __tablename__ = "opcion_insumo"

    opcion_id = Column(BigInteger, ForeignKey("opcion_modificador.id"), nullable=False, index=True)
    insumo_id = Column(BigInteger, ForeignKey("insumo.id"), nullable=False)
    cantidad = Column(Numeric(16, 3), nullable=False)
