from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, ForeignKey, DateTime, Numeric, JSON

# Lo que le corresponde a una persona en una liquidación
class LiquidacionLineaModel(DeRestaurante, BASE):

    __tablename__ = "liquidacion_linea"

    liquidacion_id = Column(BigInteger, ForeignKey("liquidacion.id", name="fk_linea_liquidacion"), nullable=False, index=True)
    usuario_id = Column(BigInteger, ForeignKey("usuario.id", name="fk_linea_usuario"), nullable=True, index=True)
    domiciliario_id = Column(BigInteger, ForeignKey("domiciliario.id", name="fk_linea_domiciliario"), nullable=True, index=True)
    nombre = Column(String(150), nullable=False)
    rol = Column(String(30), nullable=True)
    # Reparto del pozo: horas del periodo (de sus turnos o escritas por el administrador) y puntos del rol
    horas = Column(Numeric(7, 2), nullable=False, default=0)
    horas_editadas = Column(Boolean, nullable=False, default=False)
    peso = Column(Numeric(5, 2), nullable=False, default=0)
    participa = Column(Boolean, nullable=False, default=True)
    # Propinas: parte individual (de sus mesas) y parte del pozo
    individual = Column(BigInteger, nullable=False, default=0)
    pozo = Column(BigInteger, nullable=False, default=0)
    # Domiciliarios: entregas del periodo, su pago, propinas que van directo y faltantes de rendiciones
    entregas = Column(Integer, nullable=False, default=0)
    pago_entregas = Column(BigInteger, nullable=False, default=0)
    propinas = Column(BigInteger, nullable=False, default=0)
    descuentos = Column(BigInteger, nullable=False, default=0)
    ajustes = Column(BigInteger, nullable=False, default=0)
    total = Column(BigInteger, nullable=False, default=0)
    # Detalle por zona o por entrega, y efectivo pendiente por rendir
    detalle = Column(JSON, nullable=True)
    pagado_en = Column(DateTime(timezone=True), nullable=True)
    pagado_por = Column(BigInteger, ForeignKey("usuario.id", name="fk_linea_pagado_por"), nullable=True)
    medio_pago = Column(String(30), nullable=True)
    referencia_pago = Column(String(60), nullable=True)
