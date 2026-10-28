from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Boolean, BigInteger, ForeignKey, DateTime

TIPOS_QR = ["mesa", "rapido", "domicilio"]

# Token opaco que va dentro del QR: /q/<token> (doc 10A)
class QrAccesoModel(DeRestaurante, BASE):

    __tablename__ = "qr_acceso"

    tipo = Column(String(10), nullable=False, default="mesa")
    zona_id = Column(BigInteger, ForeignKey("zona.id"), nullable=False)
    mesa_id = Column(BigInteger, ForeignKey("mesa.id"), nullable=False, index=True)
    token = Column(String(64), nullable=False, unique=True)
    activo = Column(Boolean, nullable=False, default=True)
    revocado_en = Column(DateTime(timezone=True), nullable=True)
