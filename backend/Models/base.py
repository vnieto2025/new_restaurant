from Utils.tools import now
from sqlalchemy import BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import mapped_column


class Registro:
    """ Campos que llevan todas las tablas (RG-10) y el constructor por diccionario
        que usa Querys.insert_data: model(data) """

    id = mapped_column(BigInteger, primary_key=True)
    creado_en = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    actualizado_en = mapped_column(DateTime(timezone=True), default=now, onupdate=now, nullable=False)

    def __init__(self, data: dict):
        columns = self.__table__.columns.keys()
        for key, value in data.items():
            if key in columns:
                setattr(self, key, value)


class DeEmpresa(Registro):
    """ Tabla de negocio de una empresa (RG-02): toda consulta se filtra por empresa_id """

    empresa_id = mapped_column(BigInteger, ForeignKey("empresa.id"), nullable=False, index=True)


class DeRestaurante(DeEmpresa):
    """ Tabla que además pertenece a un restaurante concreto de la empresa """

    restaurante_id = mapped_column(BigInteger, ForeignKey("restaurante.id"), nullable=False, index=True)


class BorradoLogico:
    """ Entidades con historial: no se borran, se marcan (RG-11) """

    eliminado_en = mapped_column(DateTime(timezone=True), nullable=True)
