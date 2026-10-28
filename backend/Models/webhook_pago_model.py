from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Boolean, BigInteger, Text, DateTime, ForeignKey

# Aviso de la pasarela guardado tal como llegó, antes de procesarlo (doc 31, sección 7)
class WebhookPagoModel(DeRestaurante, BASE):

    __tablename__ = "webhook_pago"

    intento_pago_id = Column(BigInteger, ForeignKey("intento_pago.id", name="fk_webhook_pago_intento"), nullable=True, index=True)
    pasarela = Column(String(30), nullable=False)
    cuerpo = Column(Text, nullable=False)
    firma_valida = Column(Boolean, nullable=False, default=False)
    estado_recibido = Column(String(20), nullable=True)
    procesado_en = Column(DateTime(timezone=True), nullable=True)
    resultado = Column(String(200), nullable=True)
