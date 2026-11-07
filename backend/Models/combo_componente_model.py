from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Integer, BigInteger, ForeignKey

# Parte de un combo: "Bebida", con sus productos a elegir (doc 12, sección 4)
class ComboComponenteModel(DeRestaurante, BASE):

    __tablename__ = "combo_componente"

    combo_id = Column(BigInteger, ForeignKey("producto.id", name="fk_combo_componente_combo"), nullable=False, index=True)
    nombre = Column(String(60), nullable=False)
    # Unidades de este componente por cada combo: "2 empanadas"
    cantidad = Column(Integer, nullable=False, default=1)
    orden = Column(Integer, nullable=False, default=0)
