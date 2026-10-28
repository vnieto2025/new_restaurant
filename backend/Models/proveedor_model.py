from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Boolean, Integer, BigInteger, UniqueConstraint

FORMAS_PAGO_PROVEEDOR = ["contado", "credito"]

# Directorio de proveedores (doc 24). Con compras no se borra: se inactiva (RN-PRV-01)
class ProveedorModel(DeRestaurante, BASE):

    __tablename__ = "proveedor"
    __table_args__ = (UniqueConstraint("restaurante_id", "nombre", name="uq_proveedor_nombre"),)

    nombre = Column(String(100), nullable=False)
    razon_social = Column(String(150), nullable=True)
    tipo_documento = Column(String(5), nullable=True)
    documento = Column(String(30), nullable=True)
    contacto = Column(String(100), nullable=True)
    telefono = Column(String(20), nullable=True)
    whatsapp = Column(String(20), nullable=True)
    correo = Column(String(120), nullable=True)
    direccion = Column(String(200), nullable=True)
    # Condiciones habituales (doc 24, sección 1)
    forma_pago = Column(String(10), nullable=False, default="contado")
    plazo_dias = Column(Integer, nullable=False, default=0)
    dias_entrega = Column(String(80), nullable=True)
    pedido_minimo = Column(BigInteger, nullable=False, default=0)
    notas = Column(String(500), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
