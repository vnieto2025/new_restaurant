from Config.db import BASE
from Models.base import Registro
from sqlalchemy import Column, String

ESTADOS_EMPRESA = ["prueba", "activa", "suspendida", "cancelada"]

class EmpresaModel(Registro, BASE):

    __tablename__ = "empresa"

    nombre_comercial = Column(String(150), nullable=False)
    razon_social = Column(String(200), nullable=True)
    documento_fiscal = Column(String(30), nullable=True)
    pais = Column(String(2), nullable=False, default="CO")
    moneda = Column(String(3), nullable=False, default="COP")
    zona_horaria = Column(String(50), nullable=False, default="America/Bogota")
    contacto_nombre = Column(String(150), nullable=True)
    contacto_correo = Column(String(150), nullable=True)
    contacto_telefono = Column(String(30), nullable=True)
    # prueba, activa, suspendida, cancelada (doc 06)
    estado = Column(String(15), nullable=False, default="prueba")
