from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, Integer, BigInteger, ForeignKey, UniqueConstraint

# Un grupo de modificadores se reutiliza en varios productos (doc 12, sección 3)
class ProductoGrupoModel(DeRestaurante, BASE):

    __tablename__ = "producto_grupo"
    __table_args__ = (UniqueConstraint("producto_id", "grupo_id", name="uq_producto_grupo"),)

    producto_id = Column(BigInteger, ForeignKey("producto.id"), nullable=False, index=True)
    grupo_id = Column(BigInteger, ForeignKey("grupo_modificador.id"), nullable=False)
    orden = Column(Integer, nullable=False, default=0)
