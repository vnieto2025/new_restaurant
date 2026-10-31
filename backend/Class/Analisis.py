from datetime import timedelta
from sqlalchemy import func
from Utils.tools import Tools, CustomException, DEFAULT_TIMEZONE
from Utils.contexto import modulos_activos
from Utils.estados import NUEVO, DESPACHADO
from Querys.exportacion import ExportacionQuerys
from Querys.reporte import ReporteQuerys
from Class.Reporte import Reporte, variacion
from Models.cuenta_model import CuentaModel
from Models.orden_model import OrdenModel
from Models.orden_item_model import OrdenItemModel
from Models.historial_estado_model import HistorialEstadoModel
from Models.punto_produccion_model import PuntoProduccionModel
from Models.entrega_model import EntregaModel
from Models.domiciliario_model import DomiciliarioModel
from Models.cliente_model import ClienteModel
from Models.insumo_model import InsumoModel
from Models.movimiento_inventario_model import MovimientoInventarioModel
from Models.restaurante_model import RestauranteModel

DIAS_INACTIVO = 30
LIMITE_LISTA = 10


def minutos(desde, hasta):
    return (hasta - desde).total_seconds() / 60


def resumen_tiempos(valores):
    """ Promedio y percentil 90: el promedio esconde los pedidos que se demoran de verdad """
    orden = sorted(valores)
    return {"cantidad": len(orden), "promedio": round(sum(orden) / len(orden), 1),
            "p90": round(orden[min(len(orden) - 1, int(len(orden) * 0.9))], 1)}


class Analisis:
    """ Reportes de la fase 2 (doc 26, sección 5). Cada sección aparece solo con su módulo contratado. """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.modulos = ctx.get("modulos", set())
        self.querys = ExportacionQuerys(db, ctx, "caja" in self.modulos)
        self.reporte = Reporte(db, ctx)
        self.tz = ctx.get("zona_horaria") or DEFAULT_TIMEZONE

    def analysis(self, data: dict):
        desde, hasta = self.reporte.periodo(data)
        resultado = {"desde": desde, "hasta": hasta, "horas": self.peak_hours(desde, hasta), "clientes": self.customers(desde, hasta)}
        if "pedidos" in self.modulos:
            resultado["tiempos"] = self.kitchen_times(desde, hasta)
        if "domicilios" in self.modulos:
            resultado["domiciliarios"] = self.couriers(desde, hasta)
        if "inventario" in self.modulos:
            resultado["inventario"] = self.inventory(desde, hasta)
        return self.tools.output(200, "Análisis del periodo.", resultado)

    def peak_hours(self, desde, hasta):
        """ Ventas por día de la semana y hora. Salen de lo mismo que el total del reporte, para que cuadren (RN-REP-01) """
        if self.querys.con_caja:
            momento = func.timezone(self.tz, CuentaModel.pagada_en)
            filas = self.querys.scoped(CuentaModel).with_entities(
                func.extract("isodow", momento), func.extract("hour", momento),
                func.sum(CuentaModel.subtotal - CuentaModel.descuento - CuentaModel.descuento_cupon), func.count(CuentaModel.id),
            ).filter(CuentaModel.estado == "pagada", CuentaModel.jornada >= desde, CuentaModel.jornada <= hasta
                     ).group_by(func.extract("isodow", momento), func.extract("hour", momento)).all()
        else:
            momento = func.timezone(self.tz, OrdenModel.creado_en)
            filas = self.querys.items_vendidos(desde, hasta).with_entities(
                func.extract("isodow", momento), func.extract("hour", momento),
                func.sum(OrdenItemModel.total), func.count(func.distinct(OrdenModel.sesion_mesa_id)),
            ).group_by(func.extract("isodow", momento), func.extract("hour", momento)).all()
        celdas = [{"dia": int(dia) - 1, "hora": int(hora), "ventas": int(ventas or 0), "cuentas": int(cuentas or 0)}
                  for dia, hora, ventas, cuentas in filas]
        return {"celdas": celdas, "maximo": max((c["ventas"] for c in celdas), default=0)}

    def kitchen_times(self, desde, hasta):
        """ De que la comanda llega a producción a que se despacha, por punto (doc 26, sección 5) """
        filas = self.querys.scoped(HistorialEstadoModel).join(
            OrdenItemModel, OrdenItemModel.id == HistorialEstadoModel.orden_item_id
        ).join(OrdenModel, OrdenModel.id == OrdenItemModel.orden_id).filter(
            OrdenModel.jornada >= desde, OrdenModel.jornada <= hasta,
            HistorialEstadoModel.estado_nuevo == DESPACHADO, OrdenItemModel.punto_produccion_id.isnot(None),
        ).with_entities(HistorialEstadoModel.creado_en, OrdenItemModel.id, OrdenItemModel.creado_en,
                        OrdenItemModel.punto_produccion_id).order_by(HistorialEstadoModel.creado_en).all()
        # Una orden aprobada empieza a contar al aprobarse, no al pedirse
        aprobadas = dict(self.querys.scoped(HistorialEstadoModel).filter(
            HistorialEstadoModel.estado_nuevo == NUEVO,
            HistorialEstadoModel.orden_item_id.in_([f[1] for f in filas] or [0]),
        ).with_entities(HistorialEstadoModel.orden_item_id, HistorialEstadoModel.creado_en).all())
        # Reabierta y despachada de nuevo: cuenta el último despacho
        ultimos = {item: (fin, creado, punto) for fin, item, creado, punto in filas}
        por_punto = {}
        for item, (fin, creado, punto) in ultimos.items():
            por_punto.setdefault(punto, []).append(minutos(aprobadas.get(item, creado), fin))
        nombres = self.querys.nombres(PuntoProduccionModel)
        return [{"nombre": nombres.get(punto, "Sin punto"), **resumen_tiempos(valores)}
                for punto, valores in sorted(por_punto.items(), key=lambda x: nombres.get(x[0], ""))]

    def couriers(self, desde, hasta):
        por_persona = {}
        for entrega, _ in self.querys.entregas(desde, hasta):
            if not entrega.domiciliario_id and entrega.estado != "fallida":
                continue
            fila = por_persona.setdefault(entrega.domiciliario_id, {"entregadas": 0, "fallidas": 0, "tiempos": [], "pago": 0})
            if entrega.estado == "entregada":
                fila["entregadas"] += 1
                fila["pago"] += entrega.pago_domiciliario
                if entrega.salida_en and entrega.entregada_en:
                    fila["tiempos"].append(minutos(entrega.salida_en, entrega.entregada_en))
            elif entrega.estado == "fallida":
                fila["fallidas"] += 1
        nombres = self.querys.nombres(DomiciliarioModel)
        resultado = [{
            "nombre": nombres.get(persona, "Sin asignar"), "entregadas": f["entregadas"], "fallidas": f["fallidas"], "pago": f["pago"],
            "minutos_promedio": round(sum(f["tiempos"]) / len(f["tiempos"]), 1) if f["tiempos"] else None,
        } for persona, f in por_persona.items()]
        return sorted(resultado, key=lambda f: -f["entregadas"])

    def customers(self, desde, hasta):
        """ Nuevos, frecuentes e inactivos (doc 25, sección 5). Los nombres solo los ve quien tiene acceso a clientes. """
        con_nombres = "clientes.ver" in self.ctx.get("permisos", set())
        activos = self.querys.scoped(ClienteModel).filter(ClienteModel.anonimizado_en.is_(None))
        dia_local = func.date(func.timezone(self.tz, ClienteModel.creado_en))
        nuevos = activos.filter(dia_local >= desde, dia_local <= hasta).count()
        limite = self.reporte.hoy() - timedelta(days=DIAS_INACTIVO)
        inactivos = activos.filter(ClienteModel.ultima_compra.isnot(None), ClienteModel.ultima_compra < limite)
        frecuentes = self.querys.scoped(OrdenModel).join(ClienteModel, ClienteModel.id == OrdenModel.cliente_id).filter(
            ClienteModel.anonimizado_en.is_(None), OrdenModel.jornada >= desde, OrdenModel.jornada <= hasta,
        ).with_entities(ClienteModel.nombre, func.count(OrdenModel.id), func.sum(OrdenModel.total)).group_by(
            ClienteModel.id, ClienteModel.nombre).having(func.count(OrdenModel.id) >= 2).order_by(
            func.count(OrdenModel.id).desc(), func.sum(OrdenModel.total).desc()).all()
        return {
            "total": activos.count(), "nuevos": nuevos, "inactivos": inactivos.count(), "dias_inactivo": DIAS_INACTIVO,
            "frecuentes_cantidad": len(frecuentes), "con_nombres": con_nombres,
            "frecuentes": [{"nombre": n, "ordenes": int(o), "valor": int(v or 0)} for n, o, v in frecuentes[:LIMITE_LISTA]] if con_nombres else [],
            "por_recuperar": [{"nombre": c.nombre, "ultima_compra": c.ultima_compra} for c in inactivos.order_by(
                ClienteModel.ultima_compra.desc()).limit(LIMITE_LISTA).all()] if con_nombres else [],
        }

    def inventory(self, desde, hasta):
        insumos = self.querys.scoped(InsumoModel).filter(InsumoModel.activo.is_(True)).all()
        nombres = self.querys.nombres(InsumoModel)
        criticos = sorted((i for i in insumos if i.stock_minimo and i.stock <= i.stock_minimo), key=lambda i: i.stock / i.stock_minimo)
        mermas, costos = {}, {}
        for m in self.querys.movimientos(desde, hasta, self.tz):
            if m.tipo == "merma":
                fila = mermas.setdefault(m.insumo_id, {"cantidad": 0, "valor": 0})
                fila["cantidad"] += abs(float(m.cantidad))
                fila["valor"] += abs(m.costo_total or 0)
            elif m.tipo == "compra" and m.costo_unitario:
                # Vienen en orden de tiempo: primera y última compra del periodo
                costos.setdefault(m.insumo_id, []).append(float(m.costo_unitario))
        variaciones = [{"nombre": nombres.get(i), "antes": round(v[0]), "despues": round(v[-1]), "variacion": variacion(v[-1], v[0])}
                       for i, v in costos.items() if len(v) > 1 and v[0] != v[-1]]
        return {
            "criticos": [{"nombre": i.nombre, "unidad": i.unidad, "stock": float(i.stock), "minimo": float(i.stock_minimo)} for i in criticos],
            "mermas": sorted(({"nombre": nombres.get(i), **f, "cantidad": round(f["cantidad"], 3)} for i, f in mermas.items()), key=lambda f: -f["valor"]),
            "valor_mermas": sum(f["valor"] for f in mermas.values()),
            "variacion_costos": sorted(variaciones, key=lambda f: -abs(f["variacion"] or 0)),
        }

    def branches(self, data: dict):
        """ Comparativo entre los restaurantes de una empresa (doc 26, sección 5): solo el dueño los ve todos """
        if "admin_empresa" not in self.ctx.get("roles", []):
            raise CustomException("Solo el administrador de la empresa compara restaurantes.", 403)
        desde, hasta = self.reporte.periodo(data)
        dias = (hasta - desde).days + 1
        filas = []
        restaurantes = self.db.query(RestauranteModel).filter(RestauranteModel.empresa_id == self.ctx["empresa_id"],
                                                              RestauranteModel.estado != "inactivo").order_by(RestauranteModel.nombre).all()
        for restaurante in restaurantes:
            modulos, _ = modulos_activos(self.db, restaurante)
            querys = ReporteQuerys(self.db, {**self.ctx, "restaurante_id": restaurante.id}, "caja" in modulos)
            totales = querys.totales(desde, hasta)
            anterior = querys.totales(desde - timedelta(days=dias), desde - timedelta(days=1))
            filas.append({"nombre": restaurante.nombre, "ventas": totales["ventas"], "cuentas": totales["cuentas"],
                          "ticket_promedio": totales["ticket_promedio"], "variacion_ventas": variacion(totales["ventas"], anterior["ventas"])})
        filas.sort(key=lambda f: -f["ventas"])
        total = sum(f["ventas"] for f in filas)
        for fila in filas:
            fila["participacion"] = round(fila["ventas"] * 100 / total, 1) if total else 0
        return self.tools.output(200, "Comparativo entre restaurantes.", {"desde": desde, "hasta": hasta, "total": total, "restaurantes": filas})
