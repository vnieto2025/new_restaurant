from datetime import date, timedelta
from Utils.tools import Tools, CustomException, jornada
from Querys.reporte import ReporteQuerys
from Querys.caja import CajaQuerys
from Models.usuario_model import UsuarioModel
from Models.producto_model import ProductoModel
from Utils.estados import PENDIENTE, NUEVO, EN_PROCESO, DESPACHADO, CANCELADO

MAX_DIAS = 366
CANALES = {"tablet": "Mesa", "qr_mesa": "QR de mesa", "qr_rapido": "QR para llevar", "mostrador": "Mostrador",
           "domicilio": "Domicilio", "pos": "Venta directa"}


def variacion(actual, anterior):
    """ Porcentaje de cambio; None si no hay base para comparar (doc 26, sección 6) """
    if not anterior:
        return None
    return round((actual - anterior) * 100 / anterior, 1)


class Reporte:
    """ Reportes del MVP (doc 26, sección 4) y dashboard del administrador (doc 27) """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = ReporteQuerys(db, ctx, "caja" in ctx.get("modulos", set()))

    def hoy(self):
        return jornada(tz_name=self.ctx.get("zona_horaria"), inicio=self.ctx.get("hora_inicio_jornada"))

    def periodo(self, data: dict):
        hoy = self.hoy()
        try:
            desde = date.fromisoformat(data["desde"]) if data.get("desde") else hoy
            hasta = date.fromisoformat(data["hasta"]) if data.get("hasta") else desde
        except ValueError:
            raise CustomException("Las fechas deben tener el formato AAAA-MM-DD.")
        if hasta < desde:
            raise CustomException("La fecha final no puede ser anterior a la inicial.")
        if (hasta - desde).days + 1 > MAX_DIAS:
            raise CustomException(f"El periodo puede tener máximo {MAX_DIAS} días.")
        return desde, hasta

    # Ventas del periodo con comparativos y desgloses
    def sales(self, data: dict):

        desde, hasta = self.periodo(data)
        dias = (hasta - desde).days + 1
        totales = self.querys.totales(desde, hasta)

        anterior_desde, anterior_hasta = desde - timedelta(days=dias), desde - timedelta(days=1)
        comparativos = [self.comparativo("Periodo anterior", totales, anterior_desde, anterior_hasta)]
        if dias == 1:
            # El mismo día de la semana pasada es el comparativo más justo (doc 26, sección 6)
            semana = desde - timedelta(days=7)
            comparativos.insert(0, self.comparativo("Mismo día de la semana pasada", totales, semana, semana))

        serie = self.querys.serie(desde, hasta)
        meseros = self.querys.nombres_usuarios(self.querys.por_mesero_ventas(desde, hasta).keys())

        return self.tools.output(200, "Reporte de ventas.", {
            "desde": desde,
            "hasta": hasta,
            "en_curso": hasta >= self.hoy(),
            "base": "cuentas pagadas" if self.querys.con_caja else "órdenes de la jornada",
            "totales": totales,
            "comparativos": comparativos,
            "serie": [{"jornada": desde + timedelta(days=i), **serie.get(desde + timedelta(days=i), {"ventas": 0, "cuentas": 0})}
                      for i in range(dias)],
            "productos": self.filas(self.querys.por_producto(desde, hasta, 15)),
            "productos_por_unidades": self.filas(self.querys.por_producto(desde, hasta, 10, orden="unidades")),
            "menos_vendidos": self.filas(self.querys.menos_vendidos(desde, hasta)),
            "categorias": self.filas(self.querys.por_categoria(desde, hasta)),
            "zonas": self.filas(self.querys.por_zona(desde, hasta)),
            "canales": [{"nombre": CANALES.get(n, n), "unidades": u, "valor": v} for n, u, v in self.querys.por_canal(desde, hasta)],
            "meseros": [{"nombre": meseros.get(m, "Sin mesero"), "unidades": u, "valor": v}
                        for m, (u, v) in sorted(self.querys.por_mesero_ventas(desde, hasta).items(), key=lambda x: -x[1][1])],
            "medios": [{"nombre": n, "pagos": p, "valor": v} for n, p, v in self.querys.por_medio(desde, hasta)],
            "cancelaciones": self.cancellation_summary(desde, hasta),
        })

    def comparativo(self, nombre, totales, desde, hasta):
        otro = self.querys.totales(desde, hasta)
        return {
            "nombre": nombre,
            "desde": desde,
            "hasta": hasta,
            "ventas": otro["ventas"],
            "cuentas": otro["cuentas"],
            "ticket_promedio": otro["ticket_promedio"],
            "variacion_ventas": variacion(totales["ventas"], otro["ventas"]),
            "variacion_cuentas": variacion(totales["cuentas"], otro["cuentas"]),
            "variacion_ticket": variacion(totales["ticket_promedio"], otro["ticket_promedio"]),
        }

    def cancellation_summary(self, desde, hasta):
        items = self.querys.cancelaciones(desde, hasta)
        return {
            "items": len(items),
            "valor": sum(i["valor"] for i in items),
            "perdidas": sum(i["valor"] for i in items if i["tipo"] == "perdida"),
        }

    # Cancelaciones y pérdidas: quién, cuándo y por qué (doc 26, sección 4)
    def cancellations(self, data: dict):
        desde, hasta = self.periodo(data)
        return self.tools.output(200, "Cancelaciones.", self.querys.cancelaciones(desde, hasta))

    # Resumen por mesero del periodo
    def waiters(self, data: dict):

        desde, hasta = self.periodo(data)
        ventas = self.querys.por_mesero_ventas(desde, hasta)
        result = []
        for mesero_id, nombre in self.querys.meseros_con_actividad(desde, hasta).items():
            ordenes = self.querys.ordenes_de_mesero(mesero_id, desde, hasta)
            unidades, valor = ventas.get(mesero_id, (0, 0))
            mesas = len({o.sesion_mesa_id for o in ordenes})
            result.append({
                "mesero_id": mesero_id,
                "nombre": nombre,
                "mesas": mesas,
                "ordenes": len(ordenes),
                "items": unidades,
                "ventas": valor,
                "ticket_promedio": round(valor / mesas) if mesas else 0,
                "cancelaciones": len(self.querys.cancelaciones(desde, hasta, mesero_id)),
            })
        result.sort(key=lambda r: -r["ventas"])
        return self.tools.output(200, "Ventas por mesero.", result)

    def waiter_report(self, data: dict):
        """ Informe diario detallado de un mesero (doc 08A, sección 3).
            Un mesero solo ve el suyo; el administrador, el de cualquiera. """

        if "reportes.ver" in self.ctx["permisos"]:
            mesero_id = int(data.get("usuario_id") or self.ctx["usuario_id"])
        else:
            mesero_id = self.ctx["usuario_id"]
        mesero = self.db.get(UsuarioModel, mesero_id)
        if not mesero or mesero.empresa_id != self.ctx.get("empresa_id"):
            raise CustomException("El mesero no existe.", 404)
        desde, hasta = self.periodo(data)

        ordenes = self.querys.ordenes_de_mesero(mesero_id, desde, hasta)
        items = self.querys.items_de_ordenes([o.id for o in ordenes])
        por_orden = {}
        for item in items:
            por_orden.setdefault(item.orden_id, []).append(item)
        vivos = [i for i in items if i.estado != CANCELADO]

        mesas = []
        for sesion in self.querys.sesiones_de_mesero(mesero_id, desde, hasta):
            propias = [o for o in ordenes if o.sesion_mesa_id == sesion.id]
            cuenta = self.querys.cuenta_de_sesion(sesion.id)
            mesas.append({
                "mesa": self.querys.mesa_nombre(sesion.mesa_id),
                "abierta_en": sesion.abierta_en,
                "cerrada_en": sesion.cerrada_en,
                "ordenes": [f"#{o.numero:03d}" for o in propias],
                "total": sum(i.total for o in propias for i in por_orden.get(o.id, []) if i.estado != CANCELADO),
                "cuenta": cuenta.estado if cuenta else ("abierta" if sesion.estado == "abierta" else "sin cuenta"),
                "propina": cuenta.propina if cuenta and cuenta.estado == "pagada" else 0,
                "medios": self.querys.medios_de_cuenta(cuenta.id) if cuenta else [],
            })

        ventas = sum(i.total for i in vivos)
        return self.tools.output(200, "Informe del mesero.", {
            "mesero": mesero.nombre,
            "desde": desde,
            "hasta": hasta,
            "turnos": [{"inicio": t.inicio, "fin": t.fin, "cierre_automatico": t.cierre_automatico}
                       for t in self.querys.turnos_de_mesero(mesero_id, desde, hasta)],
            "atencion": {
                "mesas": len(mesas),
                "ordenes": len(ordenes),
                "items": sum(i.cantidad for i in vivos),
            },
            "ventas": {
                "total": ventas,
                "ticket_promedio": round(ventas / len(mesas)) if mesas else 0,
                "propinas": sum(m["propina"] for m in mesas),
            },
            "excepciones": {
                "cancelaciones": self.querys.cancelaciones(desde, hasta, mesero_id),
                "mesas_sin_cobrar": sum(1 for m in mesas if m["cuenta"] in ["abierta", "sin cuenta"]),
            },
            "mesas": mesas,
        })

    # Primera pantalla del administrador: ¿cómo va hoy? (doc 27, sección 2)
    def dashboard(self):

        hoy = self.hoy()
        totales = self.querys.totales(hoy, hoy)
        semana = hoy - timedelta(days=7)
        caja = None
        if self.querys.con_caja:
            caja_querys = CajaQuerys(self.db, self.ctx)
            turno = caja_querys.get_turno_abierto(caja_querys.get_caja().id)
            caja = {
                "turno_abierto": turno is not None,
                "cajero": caja_querys.nombre_usuario(turno.usuario_id) if turno else None,
                "efectivo_esperado": caja_querys.resumen_turno(turno)["efectivo_esperado"] if turno else None,
                "por_cobrar": len(caja_querys.sesiones_abiertas()),
            }

        estados = self.querys.items_en_curso()

        agotados = [p.nombre for p in self.querys.scoped(ProductoModel).filter(
            ProductoModel.agotado.is_(True), ProductoModel.activo.is_(True)).all()]
        return self.tools.output(200, "Dashboard.", {
            "jornada": hoy,
            "hoy": totales,
            "comparativo": self.comparativo("Mismo día de la semana pasada", totales, semana, semana),
            "en_vivo": {
                "por_aprobar": estados.get(PENDIENTE, 0),
                "en_cocina": estados.get(NUEVO, 0) + estados.get(EN_PROCESO, 0),
                "listos_sin_entregar": estados.get(DESPACHADO, 0),
            },
            "productos_del_dia": self.filas(self.querys.por_producto(hoy, hoy, 5, orden="unidades")),
            "agotados": agotados,
            "caja": caja,
        })

    def filas(self, datos):
        return [{"nombre": nombre, "unidades": unidades, "valor": valor} for nombre, unidades, valor in datos]
