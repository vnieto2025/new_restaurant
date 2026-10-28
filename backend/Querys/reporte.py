from Querys.base import Querys
from Models.orden_model import OrdenModel
from Models.orden_item_model import OrdenItemModel
from Models.cuenta_model import CuentaModel
from Models.pago_model import PagoModel
from Models.medio_pago_model import MedioPagoModel
from Models.producto_model import ProductoModel
from Models.categoria_model import CategoriaModel
from Models.zona_model import ZonaModel
from Models.usuario_model import UsuarioModel
from Models.sesion_mesa_model import SesionMesaModel
from Models.mesa_model import MesaModel
from Models.turno_mesero_model import TurnoMeseroModel
from Models.historial_estado_model import HistorialEstadoModel
from Utils.estados import CANCELADO, PENDIENTES_DE_ENTREGA
from sqlalchemy import func, and_


class ReporteQuerys(Querys):
    """ Cifras de los reportes (doc 26). Con caja contratada la venta sale de las cuentas pagadas
        (RN-REP-01); sin caja, de los ítems no cancelados de las órdenes de la jornada. """

    def __init__(self, db, ctx: dict, con_caja: bool):
        super().__init__(db, ctx)
        self.con_caja = con_caja

    # Ítems vendidos en el periodo, con su orden, listos para agrupar
    def items_vendidos(self, desde, hasta):
        query = self.scoped(OrdenItemModel).join(OrdenModel, OrdenModel.id == OrdenItemModel.orden_id).filter(
            OrdenItemModel.estado != CANCELADO)
        if self.con_caja:
            query = query.join(CuentaModel, and_(CuentaModel.sesion_mesa_id == OrdenModel.sesion_mesa_id,
                                                 CuentaModel.estado == "pagada")).filter(
                CuentaModel.jornada >= desde, CuentaModel.jornada <= hasta)
        else:
            query = query.filter(OrdenModel.jornada >= desde, OrdenModel.jornada <= hasta)
        return query

    def totales(self, desde, hasta):
        if self.con_caja:
            fila = self.scoped(CuentaModel).with_entities(
                func.count(CuentaModel.id),
                func.coalesce(func.sum(CuentaModel.subtotal - CuentaModel.descuento - CuentaModel.descuento_cupon), 0),
                func.coalesce(func.sum(CuentaModel.propina), 0),
                func.coalesce(func.sum(CuentaModel.descuento + CuentaModel.descuento_cupon), 0),
            ).filter(CuentaModel.estado == "pagada", CuentaModel.jornada >= desde, CuentaModel.jornada <= hasta).one()
            cuentas, ventas, propinas, descuentos = (int(v or 0) for v in fila)
            anuladas = self.scoped(CuentaModel).filter(CuentaModel.estado == "anulada", CuentaModel.jornada >= desde,
                                                       CuentaModel.jornada <= hasta).count()
        else:
            fila = self.items_vendidos(desde, hasta).with_entities(
                func.count(func.distinct(OrdenModel.sesion_mesa_id)), func.coalesce(func.sum(OrdenItemModel.total), 0)).one()
            cuentas, ventas = (int(v or 0) for v in fila)
            propinas = descuentos = anuladas = 0

        ordenes = self.scoped(OrdenModel).filter(OrdenModel.jornada >= desde, OrdenModel.jornada <= hasta,
                                                 OrdenModel.total > 0).count()
        return {
            "ventas": ventas,
            "cuentas": cuentas,
            "ticket_promedio": round(ventas / cuentas) if cuentas else 0,
            "propinas": propinas,
            "descuentos": descuentos,
            "cuentas_anuladas": anuladas,
            "ordenes": ordenes,
        }

    def serie(self, desde, hasta):
        if self.con_caja:
            filas = self.scoped(CuentaModel).with_entities(
                CuentaModel.jornada, func.sum(CuentaModel.subtotal - CuentaModel.descuento - CuentaModel.descuento_cupon),
                func.count(CuentaModel.id)
            ).filter(CuentaModel.estado == "pagada", CuentaModel.jornada >= desde, CuentaModel.jornada <= hasta
                     ).group_by(CuentaModel.jornada).all()
        else:
            filas = self.items_vendidos(desde, hasta).with_entities(
                OrdenModel.jornada, func.sum(OrdenItemModel.total), func.count(func.distinct(OrdenModel.sesion_mesa_id))
            ).group_by(OrdenModel.jornada).all()
        return {jornada: {"ventas": int(ventas or 0), "cuentas": int(cuentas or 0)} for jornada, ventas, cuentas in filas}

    def agrupar(self, desde, hasta, columna, limite=None, orden="valor"):
        query = self.items_vendidos(desde, hasta).with_entities(
            columna, func.sum(OrdenItemModel.cantidad), func.sum(OrdenItemModel.total)).group_by(columna)
        query = query.order_by(func.sum(OrdenItemModel.total if orden == "valor" else OrdenItemModel.cantidad).desc())
        if limite:
            query = query.limit(limite)
        return [(clave, int(unidades or 0), int(valor or 0)) for clave, unidades, valor in query.all()]

    def por_producto(self, desde, hasta, limite=None, orden="valor"):
        return self.agrupar(desde, hasta, OrdenItemModel.nombre_producto, limite, orden)

    def menos_vendidos(self, desde, hasta, limite=5):
        query = self.items_vendidos(desde, hasta).with_entities(
            OrdenItemModel.nombre_producto, func.sum(OrdenItemModel.cantidad), func.sum(OrdenItemModel.total)
        ).group_by(OrdenItemModel.nombre_producto).order_by(func.sum(OrdenItemModel.cantidad).asc()).limit(limite)
        return [(nombre, int(u or 0), int(v or 0)) for nombre, u, v in query.all()]

    def por_categoria(self, desde, hasta):
        query = self.items_vendidos(desde, hasta).join(
            ProductoModel, ProductoModel.id == OrdenItemModel.producto_id
        ).join(CategoriaModel, CategoriaModel.id == ProductoModel.categoria_id).with_entities(
            CategoriaModel.nombre, func.sum(OrdenItemModel.cantidad), func.sum(OrdenItemModel.total)
        ).group_by(CategoriaModel.nombre).order_by(func.sum(OrdenItemModel.total).desc())
        return [(nombre, int(u or 0), int(v or 0)) for nombre, u, v in query.all()]

    def por_canal(self, desde, hasta):
        return self.agrupar(desde, hasta, OrdenModel.canal)

    def por_zona(self, desde, hasta):
        nombres = {z.id: z.nombre for z in self.scoped(ZonaModel, include_deleted=True).all()}
        return [(nombres.get(zona_id, "Sin zona"), u, v) for zona_id, u, v in self.agrupar(desde, hasta, OrdenModel.zona_id)]

    def por_mesero_ventas(self, desde, hasta):
        return {mesero_id: (u, v) for mesero_id, u, v in self.agrupar(desde, hasta, OrdenModel.mesero_id)}

    def por_medio(self, desde, hasta):
        if not self.con_caja:
            return []
        filas = self.scoped(PagoModel).join(CuentaModel, CuentaModel.id == PagoModel.cuenta_id).join(
            MedioPagoModel, MedioPagoModel.id == PagoModel.medio_pago_id
        ).with_entities(MedioPagoModel.nombre, func.count(PagoModel.id), func.sum(PagoModel.monto)).filter(
            PagoModel.estado == "aplicado", CuentaModel.estado == "pagada",
            CuentaModel.jornada >= desde, CuentaModel.jornada <= hasta,
        ).group_by(MedioPagoModel.nombre).order_by(func.sum(PagoModel.monto).desc()).all()
        return [(nombre, int(pagos), int(monto or 0)) for nombre, pagos, monto in filas]

    def cancelaciones(self, desde, hasta, mesero_id=None):
        query = self.scoped(OrdenItemModel).join(OrdenModel, OrdenModel.id == OrdenItemModel.orden_id).filter(
            OrdenItemModel.estado == CANCELADO, OrdenModel.jornada >= desde, OrdenModel.jornada <= hasta)
        if mesero_id:
            query = query.filter(OrdenModel.mesero_id == mesero_id)
        items = query.add_columns(OrdenModel).order_by(OrdenItemModel.actualizado_en.desc()).limit(300).all()

        # Quién canceló: el último cambio a "cancelado" en el historial
        historial = {}
        for h in self.scoped(HistorialEstadoModel).filter(
            HistorialEstadoModel.orden_item_id.in_([item.id for item, _ in items] or [0]),
            HistorialEstadoModel.estado_nuevo == CANCELADO,
        ).all():
            historial[h.orden_item_id] = h
        usuarios = self.nombres_usuarios({h.usuario_id for h in historial.values()})
        mesas = {m.id: m.nombre for m in self.scoped(MesaModel, include_deleted=True).all()}

        return [{
            "orden": f"#{orden.numero:03d}",
            "jornada": orden.jornada,
            "mesa": mesas.get(orden.mesa_id),
            "producto": item.nombre_producto,
            "cantidad": item.cantidad,
            "valor": item.total,
            "tipo": item.tipo_cancelacion or "cancelacion",
            "motivo": item.motivo_cancelacion,
            "usuario": usuarios.get(historial[item.id].usuario_id) if item.id in historial and historial[item.id].usuario_id else "Cliente o sistema",
            "momento": item.actualizado_en,
        } for item, orden in items]

    # Ítems que todavía ocupan a alguien, por estado (operación en vivo, doc 27)
    def items_en_curso(self):
        filas = self.scoped(OrdenItemModel).with_entities(OrdenItemModel.estado, func.count(OrdenItemModel.id)).filter(
            OrdenItemModel.estado.in_(PENDIENTES_DE_ENTREGA)).group_by(OrdenItemModel.estado).all()
        return {estado: int(cantidad) for estado, cantidad in filas}

    def nombres_usuarios(self, ids):
        ids = [i for i in ids if i]
        return {u.id: u.nombre for u in self.db.query(UsuarioModel).filter(UsuarioModel.id.in_(ids or [0])).all()}

    # Para el informe por mesero (doc 08A, sección 3)
    def sesiones_de_mesero(self, mesero_id, desde, hasta):
        return self.scoped(SesionMesaModel).join(OrdenModel, OrdenModel.sesion_mesa_id == SesionMesaModel.id).filter(
            OrdenModel.mesero_id == mesero_id, OrdenModel.jornada >= desde, OrdenModel.jornada <= hasta
        ).distinct().order_by(SesionMesaModel.abierta_en.asc()).all()

    def ordenes_de_mesero(self, mesero_id, desde, hasta):
        return self.scoped(OrdenModel).filter(OrdenModel.mesero_id == mesero_id, OrdenModel.jornada >= desde,
                                              OrdenModel.jornada <= hasta).all()

    def turnos_de_mesero(self, mesero_id, desde, hasta):
        return self.scoped(TurnoMeseroModel).filter(TurnoMeseroModel.usuario_id == mesero_id, TurnoMeseroModel.jornada >= desde,
                                                    TurnoMeseroModel.jornada <= hasta).order_by(TurnoMeseroModel.inicio.asc()).all()

    def meseros_con_actividad(self, desde, hasta):
        ids = {m for (m,) in self.scoped(OrdenModel).with_entities(OrdenModel.mesero_id).filter(
            OrdenModel.jornada >= desde, OrdenModel.jornada <= hasta, OrdenModel.mesero_id.isnot(None)).distinct().all()}
        return self.nombres_usuarios(ids)

    def cuenta_de_sesion(self, sesion_id):
        return self.scoped(CuentaModel).filter(CuentaModel.sesion_mesa_id == sesion_id).first()

    def medios_de_cuenta(self, cuenta_id):
        filas = self.scoped(PagoModel).join(MedioPagoModel, MedioPagoModel.id == PagoModel.medio_pago_id).with_entities(
            MedioPagoModel.nombre).filter(PagoModel.cuenta_id == cuenta_id, PagoModel.estado == "aplicado").distinct().all()
        return [nombre for (nombre,) in filas]

    def items_de_ordenes(self, orden_ids):
        return self.scoped(OrdenItemModel).filter(OrdenItemModel.orden_id.in_(orden_ids or [0])).all()

    def mesa_nombre(self, mesa_id):
        mesa = self.db.get(MesaModel, mesa_id)
        return mesa.nombre if mesa else None
