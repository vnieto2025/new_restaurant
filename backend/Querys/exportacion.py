from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from Querys.reporte import ReporteQuerys
from Utils.estados import CANCELADO
from Utils.tools import DEFAULT_TIMEZONE
from Models.orden_model import OrdenModel
from Models.orden_item_model import OrdenItemModel
from Models.cuenta_model import CuentaModel
from Models.pago_model import PagoModel
from Models.medio_pago_model import MedioPagoModel
from Models.mesa_model import MesaModel
from Models.zona_model import ZonaModel
from Models.producto_model import ProductoModel
from Models.categoria_model import CategoriaModel
from Models.cliente_model import ClienteModel
from Models.insumo_model import InsumoModel
from Models.movimiento_inventario_model import MovimientoInventarioModel
from Models.compra_model import CompraModel
from Models.documento_venta_model import DocumentoVentaModel
from Models.entrega_model import EntregaModel
from Models.zona_envio_model import ZonaEnvioModel
from Models.domiciliario_model import DomiciliarioModel
from Models.turno_mesero_model import TurnoMeseroModel
from Models.liquidacion_model import LiquidacionModel
from Models.liquidacion_linea_model import LiquidacionLineaModel


class ExportacionQuerys(ReporteQuerys):
    """ Consultas completas para descargar: sin los recortes de lo que se muestra en pantalla """

    def nombres(self, model):
        return {fila.id: fila.nombre for fila in self.scoped(model, include_deleted=True).all()}

    def ordenes_items(self, desde, hasta):
        return self.scoped(OrdenItemModel).join(OrdenModel, OrdenModel.id == OrdenItemModel.orden_id).filter(
            OrdenModel.jornada >= desde, OrdenModel.jornada <= hasta
        ).add_columns(OrdenModel).order_by(OrdenModel.jornada, OrdenModel.numero, OrdenItemModel.id).all()

    def cancelados(self, desde, hasta):
        return self.scoped(OrdenItemModel).join(OrdenModel, OrdenModel.id == OrdenItemModel.orden_id).filter(
            OrdenItemModel.estado == CANCELADO, OrdenModel.jornada >= desde, OrdenModel.jornada <= hasta
        ).add_columns(OrdenModel).order_by(OrdenModel.jornada, OrdenModel.numero, OrdenItemModel.id).all()

    def cuentas(self, desde, hasta):
        return self.scoped(CuentaModel).filter(
            CuentaModel.estado != "abierta", CuentaModel.jornada >= desde, CuentaModel.jornada <= hasta
        ).order_by(CuentaModel.jornada, CuentaModel.numero, CuentaModel.id).all()

    def pagos(self, desde, hasta):
        return self.scoped(PagoModel).join(CuentaModel, CuentaModel.id == PagoModel.cuenta_id).filter(
            CuentaModel.jornada >= desde, CuentaModel.jornada <= hasta
        ).add_columns(CuentaModel).order_by(PagoModel.creado_en, PagoModel.id).all()

    def productos(self):
        return self.scoped(ProductoModel).order_by(ProductoModel.nombre).all()

    # Los anonimizados ya no son datos de una persona: no se exportan
    def clientes(self):
        return self.scoped(ClienteModel).filter(ClienteModel.anonimizado_en.is_(None)).order_by(ClienteModel.nombre).all()

    def insumos(self):
        return self.scoped(InsumoModel).order_by(InsumoModel.nombre).all()

    def movimientos(self, desde, hasta, tz_name):
        # Días del calendario del restaurante como instantes: esta columna tiene hora, no jornada
        zona = ZoneInfo(tz_name or DEFAULT_TIMEZONE)
        inicio = datetime.combine(desde, time.min, tzinfo=zona).astimezone(timezone.utc)
        fin = datetime.combine(hasta + timedelta(days=1), time.min, tzinfo=zona).astimezone(timezone.utc)
        return self.scoped(MovimientoInventarioModel).filter(
            MovimientoInventarioModel.creado_en >= inicio, MovimientoInventarioModel.creado_en < fin
        ).order_by(MovimientoInventarioModel.creado_en, MovimientoInventarioModel.id).all()

    def compras(self, desde, hasta):
        return self.scoped(CompraModel).filter(CompraModel.fecha >= desde, CompraModel.fecha <= hasta).order_by(
            CompraModel.fecha, CompraModel.numero).all()

    def documentos(self, desde, hasta):
        return self.scoped(DocumentoVentaModel).filter(
            DocumentoVentaModel.jornada >= desde, DocumentoVentaModel.jornada <= hasta
        ).order_by(DocumentoVentaModel.jornada, DocumentoVentaModel.id).all()

    def entregas(self, desde, hasta):
        return self.scoped(EntregaModel).join(OrdenModel, OrdenModel.id == EntregaModel.orden_id).filter(
            OrdenModel.jornada >= desde, OrdenModel.jornada <= hasta
        ).add_columns(OrdenModel).order_by(OrdenModel.jornada, OrdenModel.numero).all()

    def turnos(self, desde, hasta):
        return self.scoped(TurnoMeseroModel).filter(
            TurnoMeseroModel.jornada >= desde, TurnoMeseroModel.jornada <= hasta
        ).order_by(TurnoMeseroModel.jornada, TurnoMeseroModel.inicio).all()

    # Liquidaciones ya aprobadas que tocan el periodo; una calculada todavía puede cambiar
    def liquidaciones(self, desde, hasta, tipos):
        return self.scoped(LiquidacionLineaModel).join(
            LiquidacionModel, LiquidacionModel.id == LiquidacionLineaModel.liquidacion_id
        ).filter(
            LiquidacionModel.tipo.in_(tipos), LiquidacionModel.estado.in_(["aprobada", "pagada"]),
            LiquidacionModel.desde <= hasta, LiquidacionModel.hasta >= desde,
        ).add_columns(LiquidacionModel).order_by(LiquidacionModel.desde, LiquidacionModel.id, LiquidacionLineaModel.nombre).all()


NOMBRES = {"mesas": MesaModel, "zonas": ZonaModel, "medios": MedioPagoModel, "categorias": CategoriaModel,
           "insumos": InsumoModel, "zonas_envio": ZonaEnvioModel, "domiciliarios": DomiciliarioModel}
