from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, BigInteger, ForeignKey

# Ajuste manual con motivo (RN-PRP-04). Sin liquidación: corrige una ya aprobada y entra en la siguiente (RN-PRP-03)
class LiquidacionAjusteModel(DeRestaurante, BASE):

    __tablename__ = "liquidacion_ajuste"

    tipo = Column(String(15), nullable=False)
    liquidacion_id = Column(BigInteger, ForeignKey("liquidacion.id", name="fk_ajuste_liquidacion"), nullable=True, index=True)
    origen_liquidacion_id = Column(BigInteger, ForeignKey("liquidacion.id", name="fk_ajuste_origen"), nullable=True)
    usuario_id = Column(BigInteger, ForeignKey("usuario.id", name="fk_ajuste_usuario"), nullable=True)
    domiciliario_id = Column(BigInteger, ForeignKey("domiciliario.id", name="fk_ajuste_domiciliario"), nullable=True)
    valor = Column(BigInteger, nullable=False)
    motivo = Column(String(200), nullable=False)
    creado_por = Column(BigInteger, ForeignKey("usuario.id", name="fk_ajuste_creado_por"), nullable=True)
