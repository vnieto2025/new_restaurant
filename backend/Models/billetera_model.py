from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Boolean, Integer


# Billetera digital (Nequi, Daviplata...) para que el cliente sepa cómo pagar: es informativa, el cobro
# se registra en caja con su medio de pago (ADR-060)
class BilleteraModel(DeRestaurante, BASE):

    __tablename__ = "billetera"

    nombre = Column(String(40), nullable=False)
    # Dígitos con indicativo de país, como los demás teléfonos
    telefono = Column(String(20), nullable=True)
    titular = Column(String(80), nullable=True)
    qr_imagen = Column(String(200), nullable=True)
    orden = Column(Integer, nullable=False, default=0)
    activo = Column(Boolean, nullable=False, default=True)
