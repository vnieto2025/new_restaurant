from Config.db import BASE
from Models.base import DeEmpresa
from sqlalchemy import Column, String, Time, Integer, Boolean

TIPOS_RESTAURANTE = ["restaurante", "comida_rapida", "bar", "panaderia", "cocina_oculta", "otro"]
ESTADOS_RESTAURANTE = ["activo", "pausado", "cerrado", "inactivo"]

class RestauranteModel(DeEmpresa, BASE):

    __tablename__ = "restaurante"

    nombre = Column(String(150), nullable=False)
    tipo = Column(String(20), nullable=False, default="restaurante")
    direccion = Column(String(200), nullable=True)
    telefono = Column(String(30), nullable=True)
    zona_horaria = Column(String(50), nullable=False, default="America/Bogota")
    # Hora en que empieza el "día" operativo (RG-09)
    hora_inicio_jornada = Column(Time, nullable=False)
    moneda = Column(String(3), nullable=False, default="COP")
    # activo, pausado (no recibe órdenes por QR), cerrado temporal, inactivo (doc 07)
    estado = Column(String(15), nullable=False, default="activo")
    # Mensaje que ve el cliente en la carta cuando el restaurante está pausado o cerrado
    mensaje_carta = Column(String(250), nullable=True)
    # Porcentaje de propina que se sugiere al cobrar; 0 = no sugerir (doc 20, sección 5)
    propina_sugerida = Column(Integer, nullable=False, default=10)
    # Los productos marcados agotados vuelven a estar disponibles al cerrar la jornada (doc 12, sección 5)
    reiniciar_agotados = Column(Boolean, nullable=False, default=True)
    # Aviso de tratamiento de datos que ve el cliente; la versión sube con cada cambio (doc 32A)
    aviso_datos = Column(String(600), nullable=True)
    aviso_version = Column(Integer, nullable=False, default=1, server_default="1")
    politica_url = Column(String(250), nullable=True)
