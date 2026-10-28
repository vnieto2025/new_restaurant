from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Boolean, Integer, BigInteger, Date, ForeignKey

TIPOS_DOCUMENTO = ["pos", "factura", "nota_credito"]

# Rango de numeración autorizado para un tipo de documento (doc 21, sección 5)
class ResolucionModel(DeRestaurante, BASE):

    __tablename__ = "resolucion"

    tipo_documento = Column(String(15), nullable=False)
    numero_resolucion = Column(String(40), nullable=True)
    prefijo = Column(String(10), nullable=False, default="")
    desde = Column(BigInteger, nullable=False)
    hasta = Column(BigInteger, nullable=False)
    # Último número entregado; se incrementa de forma atómica al emitir
    ultimo = Column(BigInteger, nullable=True)
    vigente_desde = Column(Date, nullable=False)
    vigente_hasta = Column(Date, nullable=True)
    # Vacío = sirve para cualquier caja del restaurante
    caja_id = Column(BigInteger, ForeignKey("caja.id"), nullable=True)
    # Aviso cuando quedan pocos números
    alerta_restantes = Column(Integer, nullable=False, default=100)
    activo = Column(Boolean, nullable=False, default=True)
