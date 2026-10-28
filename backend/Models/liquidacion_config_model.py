from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Numeric, JSON, UniqueConstraint

PERIODOS = ["semanal", "quincenal", "mensual"]
MODELOS_PROPINA = ["individual", "colectiva", "mixta"]
METODOS_REPARTO = ["horas", "puntos", "horas_puntos"]
DESTINOS_PROPINA_DOMICILIO = ["pozo", "domiciliario"]
MODELOS_PAGO_DOMICILIO = ["zona", "porcentaje", "mixto"]

# Reglas de reparto de propinas y de pago a domiciliarios (doc 26A). Las define el restaurante:
# el sistema calcula y registra, no decide qué es legalmente correcto.
class LiquidacionConfigModel(DeRestaurante, BASE):

    __tablename__ = "liquidacion_config"
    __table_args__ = (UniqueConstraint("restaurante_id", name="uq_liquidacion_config_restaurante"),)

    periodo = Column(String(10), nullable=False, default="quincenal")
    modelo = Column(String(12), nullable=False, default="colectiva")
    # En el modelo mixto: parte de cada propina que va al mesero de la mesa
    porcentaje_individual = Column(Integer, nullable=False, default=50)
    metodo = Column(String(12), nullable=False, default="horas_puntos")
    # Cada zona reparte su propio pozo
    por_zona = Column(Boolean, nullable=False, default=False)
    # Puntos por rol: {"mesero": 1.0, "cocina": 0.8}. Peso 0 = no participa del pozo
    pesos = Column(JSON, nullable=True)
    # Solo si está permitido y acordado con el personal
    retencion = Column(Numeric(5, 2), nullable=False, default=0)
    propina_domicilio = Column(String(12), nullable=False, default="pozo")
    pago_domicilio = Column(String(10), nullable=False, default="zona")
    pago_porcentaje = Column(Numeric(5, 2), nullable=False, default=0)
    pago_base = Column(BigInteger, nullable=False, default=0)
