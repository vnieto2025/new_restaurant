from Config.db import BASE
from Models.base import DeRestaurante, BorradoLogico
from sqlalchemy import Column, String, Boolean, Integer, UniqueConstraint

TIPOS_PUNTO = ["cocina", "bar", "otro"]

# Lugar donde se preparan ítems: cocina, bar, parrilla... (doc 19)
class PuntoProduccionModel(DeRestaurante, BorradoLogico, BASE):

    __tablename__ = "punto_produccion"
    __table_args__ = (UniqueConstraint("restaurante_id", "nombre", name="uq_punto_nombre"),)

    nombre = Column(String(60), nullable=False)
    tipo = Column(String(15), nullable=False, default="cocina")
    # Imprime la tirilla de la comanda al abrirla (doc 19A)
    imprime_al_abrir = Column(Boolean, nullable=False, default=False)
    # Pasa de nuevo a despachado sin "en proceso" (bebidas simples)
    salta_en_proceso = Column(Boolean, nullable=False, default=False)
    # Minutos objetivo para la alerta de demora (opcional)
    tiempo_objetivo = Column(Integer, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
