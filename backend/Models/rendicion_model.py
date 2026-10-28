from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, BigInteger, ForeignKey

# El domiciliario entrega en caja lo que cobró contra entrega (doc 15B, sección 6; RN-DOM-03)
class RendicionModel(DeRestaurante, BASE):

    __tablename__ = "rendicion"

    domiciliario_id = Column(BigInteger, ForeignKey("domiciliario.id", name="fk_rendicion_domiciliario"), nullable=False, index=True)
    turno_caja_id = Column(BigInteger, ForeignKey("turno_caja.id", name="fk_rendicion_turno"), nullable=False, index=True)
    esperado = Column(BigInteger, nullable=False)
    entregado = Column(BigInteger, nullable=False)
    # entregado - esperado: negativo es faltante a cargo del domiciliario
    diferencia = Column(BigInteger, nullable=False)
    notas = Column(String(200), nullable=True)
    # Liquidación que descontó el faltante
    liquidacion_id = Column(BigInteger, ForeignKey("liquidacion.id", name="fk_rendicion_liquidacion"), nullable=True)
    usuario_id = Column(BigInteger, ForeignKey("usuario.id", name="fk_rendicion_usuario"), nullable=True)
