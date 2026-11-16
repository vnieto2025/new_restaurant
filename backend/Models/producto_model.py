from Config.db import BASE
from Models.base import DeRestaurante, BorradoLogico
from sqlalchemy import Column, String, Boolean, Integer, BigInteger, ForeignKey, Text, UniqueConstraint, Index, text

class ProductoModel(DeRestaurante, BorradoLogico, BASE):

    __tablename__ = "producto"
    __table_args__ = (
        UniqueConstraint("restaurante_id", "nombre", name="uq_producto_nombre"),
        # Un código de barras identifica un solo producto vigente del restaurante (ADR-058)
        Index("uq_producto_codigo_barras", "restaurante_id", "codigo_barras", unique=True,
              postgresql_where=text("codigo_barras IS NOT NULL AND eliminado_en IS NULL")),
    )

    categoria_id = Column(BigInteger, ForeignKey("categoria.id"), nullable=False, index=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    # Foto comprimida, relativa a MEDIA_DIR, en la carpeta del restaurante
    imagen = Column(String(200), nullable=True)
    # Aviso para el cliente: "Contiene gluten, lácteos". Lo escribe el restaurante, que es quien sabe qué lleva cada plato
    alergenos = Column(String(200), nullable=True)
    # Precio final de carta, con impuesto incluido, en pesos enteros (RG-03, ADR-010)
    precio = Column(BigInteger, nullable=False)
    # Lo que lee el lector de código de barras en caja, mostrador y mesa (ADR-058)
    codigo_barras = Column(String(40), nullable=True)
    punto_produccion_id = Column(BigInteger, ForeignKey("punto_produccion.id"), nullable=True)
    # Vacío = el de la categoría o, si tampoco tiene, el impuesto por defecto
    impuesto_id = Column(BigInteger, ForeignKey("impuesto.id"), nullable=True)
    orden = Column(Integer, nullable=False, default=0)
    # simple o combo: un combo tiene componentes en vez de grupos de modificadores (doc 12, sección 4)
    tipo = Column(String(10), nullable=False, default="simple", server_default="simple")
    agotado = Column(Boolean, nullable=False, default=False)
    activo = Column(Boolean, nullable=False, default=True)
