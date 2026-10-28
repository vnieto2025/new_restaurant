from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Boolean, Integer, Text, UniqueConstraint

# Pasarela de pagos del restaurante (doc 20A). Cada restaurante usa su propia cuenta en la pasarela:
# el software integra y no recauda dinero de terceros (sección 6)
class PagoLineaConfigModel(DeRestaurante, BASE):

    __tablename__ = "pago_linea_config"
    __table_args__ = (UniqueConstraint("restaurante_id", name="uq_pago_linea_config"),)

    activo = Column(Boolean, nullable=False, default=False)
    pasarela = Column(String(30), nullable=False, default="simulada")
    ambiente = Column(String(12), nullable=False, default="pruebas")
    # Llaves y secreto de firma de los avisos de la pasarela, cifrados; nunca se devuelven
    credenciales = Column(Text, nullable=True)
    permitir_propina = Column(Boolean, nullable=False, default=True)
    # Tiempo para completar el pago antes de que el intento expire
    minutos_expiracion = Column(Integer, nullable=False, default=30)
