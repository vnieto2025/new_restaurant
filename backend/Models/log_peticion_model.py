from Config.db import BASE
from Utils.tools import now
from sqlalchemy import Column, String, BigInteger, DateTime, Text

# Registro técnico de cada petición POST (heredado de AppGym)
class LogPeticionModel(BASE):

    __tablename__ = "log_peticion"

    id = Column(BigInteger, primary_key=True)
    service = Column(String(200), nullable=False)
    method = Column(String(10), nullable=False)
    request = Column(Text)
    response = Column(Text)
    ip = Column(String(50), nullable=True)
    creado_en = Column(DateTime(timezone=True), default=now, nullable=False)

    def __init__(self, data: dict):
        self.service = data['service']
        self.method = data['method']
        self.request = data['request']
        self.response = data['response']
        self.ip = data['ip']
        if 'creado_en' in data:
            self.creado_en = data['creado_en']
