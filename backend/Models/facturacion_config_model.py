from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Boolean, Integer, Text, UniqueConstraint

# Cómo factura el restaurante: proveedor tecnológico y credenciales cifradas (doc 21A, sección 4)
class FacturacionConfigModel(DeRestaurante, BASE):

    __tablename__ = "facturacion_config"
    __table_args__ = (UniqueConstraint("restaurante_id", name="uq_facturacion_config"),)

    activo = Column(Boolean, nullable=False, default=False)
    proveedor = Column(String(30), nullable=False, default="simulado")
    ambiente = Column(String(12), nullable=False, default="pruebas")
    # Nunca se devuelven al cliente después de guardarlas (RN-FIS-03)
    credenciales = Column(Text, nullable=True)
    documento_defecto = Column(String(15), nullable=False, default="pos")
    # Plazo para pedir factura a nombre propio después de pagar
    dias_factura_posterior = Column(Integer, nullable=False, default=30)
