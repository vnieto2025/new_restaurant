from Config.db import BASE
from Models.base import DeRestaurante, BorradoLogico
from sqlalchemy import Column, String, Boolean, UniqueConstraint

TIPOS_IMPUESTO = ["iva", "consumo", "otro"]

# Impuesto que cobra el restaurante. La tasa no va aquí: va en impuesto_tarifa con vigencia (RG-06)
class ImpuestoModel(DeRestaurante, BorradoLogico, BASE):

    __tablename__ = "impuesto"
    __table_args__ = (UniqueConstraint("restaurante_id", "nombre", name="uq_impuesto_nombre"),)

    nombre = Column(String(60), nullable=False)
    tipo = Column(String(10), nullable=False)
    # Código del impuesto ante el proveedor de facturación (lo define la normativa)
    codigo = Column(String(10), nullable=True)
    # El que aplica a los productos sin impuesto propio ni de su categoría
    por_defecto = Column(Boolean, nullable=False, default=False)
    activo = Column(Boolean, nullable=False, default=True)
