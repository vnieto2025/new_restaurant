from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Boolean, Integer, BigInteger, UniqueConstraint

# Área de cobertura con tarifa fija (doc 15B, sección 1). Por lista de barrios: sin mapas en esta fase
class ZonaEnvioModel(DeRestaurante, BASE):

    __tablename__ = "zona_envio"
    __table_args__ = (UniqueConstraint("restaurante_id", "nombre", name="uq_zona_envio_nombre"),)

    nombre = Column(String(60), nullable=False)
    # Barrios o sectores que cubre, para encontrar la zona al tomar el pedido
    barrios = Column(String(500), nullable=True)
    # Lo que se le cobra al cliente y lo que se le reconoce al domiciliario (pueden diferir)
    tarifa = Column(BigInteger, nullable=False, default=0)
    pago_domiciliario = Column(BigInteger, nullable=False, default=0)
    pedido_minimo = Column(BigInteger, nullable=False, default=0)
    orden = Column(Integer, nullable=False, default=0)
    activo = Column(Boolean, nullable=False, default=True)
