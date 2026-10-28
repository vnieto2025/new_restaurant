from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Numeric, BigInteger, ForeignKey

# Cómo se compra: "Bulto de 25 kg" = 25000 g. El factor es explícito (RN-INV-03)
class InsumoPresentacionModel(DeRestaurante, BASE):

    __tablename__ = "insumo_presentacion"

    insumo_id = Column(BigInteger, ForeignKey("insumo.id"), nullable=False, index=True)
    nombre = Column(String(60), nullable=False)
    factor = Column(Numeric(16, 3), nullable=False)
