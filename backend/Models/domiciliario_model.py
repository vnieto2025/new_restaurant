from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Boolean, BigInteger, ForeignKey, UniqueConstraint

VINCULOS = ["propio", "independiente"]

# Quien lleva los domicilios, identificado por código (doc 15B, sección 2)
class DomiciliarioModel(DeRestaurante, BASE):

    __tablename__ = "domiciliario"
    __table_args__ = (UniqueConstraint("restaurante_id", "codigo", name="uq_domiciliario_codigo"),)

    nombre = Column(String(100), nullable=False)
    codigo = Column(String(10), nullable=False)
    documento = Column(String(30), nullable=True)
    telefono = Column(String(20), nullable=True)
    # Informativo: el tratamiento laboral lo define el restaurante (doc 26A)
    vinculo = Column(String(15), nullable=False, default="propio")
    # Usuario con el que ve sus entregas en el celular (opcional)
    usuario_id = Column(BigInteger, ForeignKey("usuario.id", name="fk_domiciliario_usuario"), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
