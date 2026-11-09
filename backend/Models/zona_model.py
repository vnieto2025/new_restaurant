from Config.db import BASE
from Models.base import DeRestaurante, BorradoLogico
from sqlalchemy import Column, String, Boolean, Integer, BigInteger, ForeignKey, UniqueConstraint

MODOS_QR = ["libre", "aprobacion"]
# zona: todo el pedido va al punto de la zona | producto: cada producto a su punto (cocina, bar...) (ADR-056)
REPARTOS = ["zona", "producto"]

# Área del restaurante que une carta, mesas, meseros y punto de producción (doc 09)
class ZonaModel(DeRestaurante, BorradoLogico, BASE):

    __tablename__ = "zona"
    __table_args__ = (UniqueConstraint("restaurante_id", "nombre", name="uq_zona_nombre"),)

    nombre = Column(String(60), nullable=False)
    codigo = Column(String(10), nullable=True)
    orden = Column(Integer, nullable=False, default=0)
    carta_id = Column(BigInteger, ForeignKey("carta.id"), nullable=True)
    punto_produccion_id = Column(BigInteger, ForeignKey("punto_produccion.id"), nullable=True)
    # Cómo entran las órdenes por QR de mesa (ADR-012)
    modo_qr = Column(String(15), nullable=False, default="aprobacion")
    # Cómo se reparte un pedido entre los puntos de producción (ADR-056)
    reparto = Column(String(10), nullable=False, default="zona", server_default="zona")
    # Zona lógica de mostrador donde vive la mesa externa
    es_mostrador = Column(Boolean, nullable=False, default=False)
    activo = Column(Boolean, nullable=False, default=True)
