from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Integer, BigInteger, ForeignKey, Time

# atencion: cuándo se reciben órdenes; carta: qué carta usa una zona en esa franja (doc 08A, sección 4)
TIPOS_HORARIO = ["atencion", "carta"]

# Franja semanal en hora del restaurante. Si "hasta" es menor que "desde", cruza la medianoche.
class HorarioModel(DeRestaurante, BASE):

    __tablename__ = "horario"

    tipo = Column(String(10), nullable=False)
    # Vacío = horario del restaurante; con zona = horario o carta de esa zona
    zona_id = Column(BigInteger, ForeignKey("zona.id"), nullable=True, index=True)
    # 0 = lunes ... 6 = domingo
    dia_semana = Column(Integer, nullable=False)
    desde = Column(Time, nullable=False)
    hasta = Column(Time, nullable=False)
    carta_id = Column(BigInteger, ForeignKey("carta.id"), nullable=True)
