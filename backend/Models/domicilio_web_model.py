from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Boolean, UniqueConstraint

# Pedidos de domicilio hechos por el propio cliente desde el enlace o el QR de domicilios (doc 17A, sección 2.6).
# El enlace es un QR de tipo "domicilio" sobre la mesa externa; esta fila dice si se reciben y cómo
class DomicilioWebModel(DeRestaurante, BASE):

    __tablename__ = "domicilio_web"
    __table_args__ = (UniqueConstraint("restaurante_id", name="uq_domicilio_web"),)

    activo = Column(Boolean, nullable=False, default=False)
    # Cada pedido espera la confirmación de quien despacha antes de ir a cocina (anti-spam, doc 17A sección 5)
    aprobacion = Column(Boolean, nullable=False, default=True)
    # Aviso visible arriba de la carta: horario de domicilios, tiempo estimado…
    mensaje = Column(String(200), nullable=True)
