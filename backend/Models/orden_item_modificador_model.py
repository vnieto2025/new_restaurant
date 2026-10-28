from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, BigInteger, ForeignKey

# Lo elegido en cada ítem, copiado al crear la orden (RG-13)
class OrdenItemModificadorModel(DeRestaurante, BASE):

    __tablename__ = "orden_item_modificador"

    orden_item_id = Column(BigInteger, ForeignKey("orden_item.id"), nullable=False, index=True)
    opcion_id = Column(BigInteger, ForeignKey("opcion_modificador.id"), nullable=False)
    grupo_nombre = Column(String(60), nullable=False)
    nombre = Column(String(60), nullable=False)
    precio_extra = Column(BigInteger, nullable=False, default=0)
