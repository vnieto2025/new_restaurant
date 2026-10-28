from Config.db import BASE
from Models.base import DeEmpresa, BorradoLogico
from sqlalchemy import Column, String, Text, Integer, BigInteger, Boolean, ForeignKey, DateTime, Date, UniqueConstraint

ESTADOS_CLIENTE = ["activo", "inactivo", "bloqueado"]

# Cliente registrado. Es por empresa: la misma persona en dos empresas son dos registros (doc 25, RN-CLI-01)
class ClienteModel(DeEmpresa, BorradoLogico, BASE):

    __tablename__ = "cliente"
    # El teléfono es el identificador principal y es único en la empresa (RN-CLI-02)
    __table_args__ = (UniqueConstraint("empresa_id", "telefono", name="uq_cliente_telefono"),)

    nombre = Column(String(120), nullable=False)
    # Solo dígitos, con indicativo de país (573001234567)
    telefono = Column(String(20), nullable=True)
    correo = Column(String(150), nullable=True)
    tipo_documento = Column(String(10), nullable=True)
    documento = Column(String(30), nullable=True)
    notas = Column(Text, nullable=True)
    estado = Column(String(10), nullable=False, default="activo")
    # Autorización de tratamiento de datos para gestionar sus órdenes (doc 32A, RN-PRI-02)
    datos_aceptado_en = Column(DateTime(timezone=True), nullable=True)
    datos_canal = Column(String(20), nullable=True)
    datos_version = Column(Integer, nullable=True)
    # Comunicaciones comerciales: consentimiento separado y revocable (RN-CLI-04)
    comercial_aceptado_en = Column(DateTime(timezone=True), nullable=True)
    comercial_canal = Column(String(20), nullable=True)
    comercial_revocado_en = Column(DateTime(timezone=True), nullable=True)
    # Avisos sobre sus propias órdenes (lista, en camino). Puede pedir no recibirlos (doc 31B, sección 4)
    acepta_avisos = Column(Boolean, nullable=False, default=True, server_default="true")
    # Supresión: se borran los datos personales y se conservan las ventas (RN-CLI-05)
    anonimizado_en = Column(DateTime(timezone=True), nullable=True)
    ultima_compra = Column(Date, nullable=True)
    registrado_por = Column(BigInteger, ForeignKey("usuario.id"), nullable=True)
