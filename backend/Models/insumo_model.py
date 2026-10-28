from Config.db import BASE
from Models.base import DeRestaurante, BorradoLogico
from sqlalchemy import Column, String, Boolean, Numeric, UniqueConstraint

UNIDADES = {"g": "gramos", "ml": "mililitros", "und": "unidades"}

# Insumo, producto de reventa, empaque o preparación (doc 22, sección 2).
# Las cantidades siempre van en la unidad base: así no se mezclan unidades (RN-INV-03)
class InsumoModel(DeRestaurante, BorradoLogico, BASE):

    __tablename__ = "insumo"
    __table_args__ = (UniqueConstraint("restaurante_id", "nombre", name="uq_insumo_nombre"),)

    nombre = Column(String(100), nullable=False)
    codigo = Column(String(30), nullable=True)
    categoria = Column(String(40), nullable=True)
    unidad = Column(String(5), nullable=False)
    # Preparación (sub-receta): se elabora en el restaurante con su propia receta (doc 14)
    es_preparacion = Column(Boolean, nullable=False, default=False)
    # Costo promedio ponderado por unidad base (doc 22, sección 4)
    costo_promedio = Column(Numeric(16, 4), nullable=False, default=0)
    # Suma de los movimientos, mantenida en la misma transacción de cada movimiento (RN-INV-01)
    stock = Column(Numeric(16, 3), nullable=False, default=0)
    stock_minimo = Column(Numeric(16, 3), nullable=False, default=0)
    ubicacion = Column(String(40), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
