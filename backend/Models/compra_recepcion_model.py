from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, BigInteger, ForeignKey

# Cada vez que llega mercancía de una compra: quién la recibió y cuánto valía (RN-COM-02, RN-COM-03)
class CompraRecepcionModel(DeRestaurante, BASE):

    __tablename__ = "compra_recepcion"

    compra_id = Column(BigInteger, ForeignKey("compra.id", name="fk_compra_recepcion_compra"), nullable=False, index=True)
    usuario_id = Column(BigInteger, ForeignKey("usuario.id", name="fk_compra_recepcion_usuario"), nullable=True)
    valor = Column(BigInteger, nullable=False, default=0)
    notas = Column(String(200), nullable=True)
    # Gasto de caja con el que se pagó, si la compra se paga desde la caja (doc 23, sección 6)
    movimiento_caja_id = Column(BigInteger, ForeignKey("movimiento_caja.id", name="fk_compra_recepcion_movimiento_caja"),
                                nullable=True)
