from Config.db import BASE
from Models.base import DeRestaurante
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, ForeignKey, Date, DateTime, Time, JSON, UniqueConstraint

TIPOS_CUPON = ["porcentaje", "valor", "producto", "envio"]
CANALES_CUPON = ["mesa", "para_llevar", "domicilio"]
# Vencido y agotado no se guardan: salen de la vigencia y de las redenciones (doc 25A, sección 2)
ESTADOS_CUPON = ["activo", "pausado", "anulado"]
ORIGENES_CUPON = ["manual", "automatico"]

# Cupón de descuento con sus reglas de uso (doc 25A). Una plantilla no se canjea: sirve para emitir
# un cupón personal después de una compra (sección 3, "Automático al pedir").
class CuponModel(DeRestaurante, BASE):

    __tablename__ = "cupon"
    __table_args__ = (UniqueConstraint("restaurante_id", "codigo", name="uq_cupon_codigo"),)

    # En mayúsculas, sin espacios
    codigo = Column(String(30), nullable=False)
    nombre = Column(String(100), nullable=False)
    # Lo que ve el cliente: "10 % en tu próxima visita"
    descripcion = Column(String(200), nullable=True)
    tipo = Column(String(12), nullable=False)
    # Porcentaje (1 a 100) o pesos, según el tipo. En "producto" es el porcentaje sobre una unidad (100 = gratis)
    valor = Column(BigInteger, nullable=False, default=0)
    # Descuento máximo de un cupón de porcentaje
    tope = Column(BigInteger, nullable=True)
    producto_id = Column(BigInteger, ForeignKey("producto.id", name="fk_cupon_producto"), nullable=True)
    inicia = Column(Date, nullable=True)
    termina = Column(Date, nullable=True)
    # Listas; vacío = sin restricción
    canales = Column(JSON, nullable=True)
    zonas = Column(JSON, nullable=True)
    productos = Column(JSON, nullable=True)
    categorias = Column(JSON, nullable=True)
    # 0 = lunes ... 6 = domingo
    dias = Column(JSON, nullable=True)
    hora_desde = Column(Time, nullable=True)
    hora_hasta = Column(Time, nullable=True)
    monto_minimo = Column(BigInteger, nullable=False, default=0)
    usos_maximos = Column(Integer, nullable=True)
    usos_por_cliente = Column(Integer, nullable=True)
    # Cupón personal: solo lo usa este cliente (RN-CUP-04)
    cliente_id = Column(BigInteger, ForeignKey("cliente.id", name="fk_cupon_cliente"), nullable=True, index=True)
    acumulable = Column(Boolean, nullable=False, default=False)
    estado = Column(String(10), nullable=False, default="activo")
    origen = Column(String(12), nullable=False, default="manual")
    # Plantilla de emisión automática: compra mínima que la dispara y días de validez del cupón emitido
    plantilla = Column(Boolean, nullable=False, default=False)
    emitir_desde = Column(BigInteger, nullable=True)
    dias_validez = Column(Integer, nullable=True)
    plantilla_id = Column(BigInteger, ForeignKey("cupon.id", name="fk_cupon_plantilla"), nullable=True)
    cuenta_origen_id = Column(BigInteger, ForeignKey("cuenta.id", name="fk_cupon_cuenta_origen"), nullable=True)
    enviado_en = Column(DateTime(timezone=True), nullable=True)
    creado_por = Column(BigInteger, ForeignKey("usuario.id", name="fk_cupon_creado_por"), nullable=True)
