from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Boolean, BigInteger, ForeignKey, DateTime

TIPOS_DISPOSITIVO = ["zona", "produccion"]

# Tablet de zona o pantalla de producción autorizada por el administrador (doc 08, sección 2)
class DispositivoModel(DeRestaurante, BASE):

    __tablename__ = "dispositivo"

    nombre = Column(String(60), nullable=False)
    tipo = Column(String(12), nullable=False)
    zona_id = Column(BigInteger, ForeignKey("zona.id"), nullable=True)
    punto_produccion_id = Column(BigInteger, ForeignKey("punto_produccion.id"), nullable=True)
    # Huella del secreto que guarda el dispositivo; el secreto en claro nunca se guarda
    token_hash = Column(String(64), nullable=True, unique=True)
    # Código de un solo uso para emparejar, con vencimiento
    codigo = Column(String(6), nullable=True, index=True)
    codigo_expira = Column(DateTime(timezone=True), nullable=True)
    emparejado_en = Column(DateTime(timezone=True), nullable=True)
    ultimo_uso = Column(DateTime(timezone=True), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
