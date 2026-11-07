from datetime import date, timedelta
from Utils.tools import Tools, CustomException, clean_text, to_local
from Utils.telefono import normalizar_telefono, telefono_legible
from Utils.notificaciones import guardar
from Querys.base import Querys
from Models.restaurante_model import RestauranteModel
from Models.cierre_jornada_model import CierreJornadaModel
from Models.turno_caja_model import TurnoCajaModel
from Models.usuario_model import UsuarioModel
from Models.insumo_model import InsumoModel
from Models.producto_model import ProductoModel
from Models.notificacion_config_model import NotificacionConfigModel
from Class.Reporte import Reporte
from Class.Alertas import pesos
from Class.Caja import dia_actual

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_larga(dia: date) -> str:
    return f"{DIAS[dia.weekday()]} {dia.day} de {MESES[dia.month - 1]}"


class ResumenDiario:
    """ Resumen de una jornada para el dueño (docs 26 y 31B): cuánto se vendió, cómo se pagó, qué salió mal.
        Se consulta en la aplicación y, si está activo, se deja listo para WhatsApp al cerrar la jornada. """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = Querys(db, ctx)

    def get(self, data: dict):
        hoy = dia_actual(self.ctx)
        try:
            dia = date.fromisoformat(data["jornada"]) if data.get("jornada") else hoy
        except ValueError:
            raise CustomException("La fecha debe tener el formato AAAA-MM-DD.")
        if dia > hoy:
            raise CustomException("Esa jornada todavía no empieza.")
        resumen = self.build(dia)
        config = self.config()
        return self.tools.output(200, "Resumen del día.", {
            **resumen, "texto": self.texto(resumen),
            "telefono": config.get("telefono"), "telefono_legible": telefono_legible(config["telefono"]) if config.get("telefono") else None,
        })

    def build(self, dia: date) -> dict:
        reporte = Reporte(self.db, self.ctx)
        modulos = self.ctx.get("modulos", set())
        totales = reporte.querys.totales(dia, dia)
        semana = dia - timedelta(days=7)
        cierre = self.querys.scoped(CierreJornadaModel).filter(CierreJornadaModel.jornada == dia).first()
        restaurante = self.db.get(RestauranteModel, self.ctx["restaurante_id"])

        caja = None
        if "caja" in modulos:
            turnos = self.querys.scoped(TurnoCajaModel).filter(TurnoCajaModel.jornada == dia).order_by(TurnoCajaModel.abierto_en).all()
            nombres = {u.id: u.nombre for u in self.db.query(UsuarioModel).filter(UsuarioModel.id.in_([t.usuario_id for t in turnos] or [0]))}
            caja = {
                "medios": [{"nombre": n, "pagos": p, "valor": v} for n, p, v in reporte.querys.por_medio(dia, dia)],
                "turnos": [{"cajero": nombres.get(t.usuario_id, "?"), "estado": t.estado, "diferencia": t.diferencia}
                           for t in turnos],
            }
        inventario = None
        if "inventario" in modulos:
            insumos = self.querys.scoped(InsumoModel).filter(InsumoModel.activo.is_(True)).all()
            inventario = {"negativos": sum(1 for i in insumos if i.stock < 0),
                          "bajos": sum(1 for i in insumos if i.stock >= 0 and i.stock_minimo > 0 and i.stock <= i.stock_minimo)}

        return {
            "restaurante": restaurante.nombre,
            "jornada": dia,
            "fecha": fecha_larga(dia),
            "en_curso": dia == dia_actual(self.ctx) and not cierre,
            "cerrada_en": to_local(cierre.creado_en, self.ctx.get("zona_horaria")) if cierre else None,
            "totales": totales,
            "comparativo": reporte.comparativo(f"El {DIAS[semana.weekday()]} pasado", totales, semana, semana),
            "productos": reporte.filas(reporte.querys.por_producto(dia, dia, 5, orden="unidades")),
            "cancelaciones": reporte.cancellation_summary(dia, dia),
            "caja": caja,
            "inventario": inventario,
            "agotados": [p.nombre for p in self.querys.scoped(ProductoModel).filter(
                ProductoModel.agotado.is_(True), ProductoModel.activo.is_(True)).order_by(ProductoModel.nombre).all()]
            if dia == dia_actual(self.ctx) else [],
        }

    def texto(self, r: dict) -> str:
        """ El mismo resumen en texto plano, listo para WhatsApp """
        t, comp = r["totales"], r["comparativo"]
        lineas = [f"*Resumen de {r['restaurante']}*", f"{r['fecha'].capitalize()}{' (en curso)' if r['en_curso'] else ''}", ""]
        ventas = f"Ventas: {pesos(t['ventas'])}"
        if comp["variacion_ventas"] is not None:
            ventas += f" ({'+' if comp['variacion_ventas'] >= 0 else ''}{comp['variacion_ventas']} % vs. {comp['nombre'].lower()})"
        lineas += [ventas, f"Cuentas: {t['cuentas']} · Ticket promedio: {pesos(t['ticket_promedio'])}"]
        if t["propinas"] or t["descuentos"]:
            lineas.append(f"Propinas: {pesos(t['propinas'])} · Descuentos: {pesos(t['descuentos'])}")
        if r["caja"] and r["caja"]["medios"]:
            lineas.append("Pagos: " + "; ".join(f"{m['nombre']} {pesos(m['valor'])}" for m in r["caja"]["medios"]))
        if r["productos"]:
            lineas.append("Lo más pedido: " + ", ".join(f"{p['unidades']} {p['nombre']}" for p in r["productos"]))
        c = r["cancelaciones"]
        if c["items"]:
            lineas.append(f"Cancelaciones: {c['items']} por {pesos(c['valor'])}" + (f" (pérdidas {pesos(c['perdidas'])})" if c["perdidas"] else ""))
        if r["caja"]:
            for turno in r["caja"]["turnos"]:
                if turno["estado"] != "cerrado":
                    lineas.append(f"Caja: el turno de {turno['cajero']} sigue abierto")
                elif turno["diferencia"]:
                    lineas.append(f"Caja: a {turno['cajero']} le {'sobraron' if turno['diferencia'] > 0 else 'faltaron'} {pesos(abs(turno['diferencia']))}")
        if r["inventario"] and (r["inventario"]["negativos"] or r["inventario"]["bajos"]):
            lineas.append(f"Inventario: {r['inventario']['bajos']} bajo el mínimo, {r['inventario']['negativos']} en negativo")
        if r["agotados"]:
            lineas.append("Agotados: " + ", ".join(r["agotados"]))
        if r["cerrada_en"]:
            lineas.append(f"Jornada cerrada a las {r['cerrada_en'].strftime('%I:%M %p').lstrip('0').lower().replace('am', 'a. m.').replace('pm', 'p. m.')}")
        return "\n".join(lineas)

    # ---- Envío al cerrar la jornada ----

    def config(self) -> dict:
        restaurante = self.db.get(RestauranteModel, self.ctx["restaurante_id"])
        return restaurante.resumen_diario or {}

    def get_config(self, data: dict = None):
        config = self.config()
        return self.tools.output(200, "Envío del resumen.", {
            "activo": bool(config.get("activo")), "nombre": config.get("nombre"),
            "telefono": telefono_legible(config["telefono"]) if config.get("telefono") else None,
            "puede_enviar": "pedidos" in self.ctx.get("modulos", set()),
        })

    def save_config(self, data: dict):
        activo = data.get("activo") is True
        telefono = normalizar_telefono(data.get("telefono"), obligatorio=activo) if data.get("telefono") else None
        if activo and not telefono:
            raise CustomException("Escribe el celular al que se envía el resumen.")
        restaurante = self.db.query(RestauranteModel).filter(RestauranteModel.id == self.ctx["restaurante_id"]).with_for_update().one()
        nombre = clean_text(data.get("nombre"))[:60] if data.get("nombre") else None
        restaurante.resumen_diario = {"activo": activo, "telefono": telefono, "nombre": nombre}
        self.querys.audit("resumen_diario_configurado", "restaurante", restaurante.id,
                          despues={"activo": activo, "telefono": telefono_legible(telefono) if telefono else None}, commit=False)
        self.db.commit()
        return self.get_config()

    def queue(self, dia: date):
        """ Al cerrar la jornada: deja el resumen en los avisos de WhatsApp. En modo manual alguien lo envía
            con el enlace; en automático lo envía la cola. Nunca frena el cierre. """
        config = self.config()
        if not config.get("activo") or not config.get("telefono") or "pedidos" not in self.ctx.get("modulos", set()):
            return False
        avisos = self.querys.scoped(NotificacionConfigModel).first()
        modo = avisos.modo if avisos else "manual"
        estado = "pendiente" if modo == "automatico" else "manual"
        try:
            with self.db.begin_nested():
                guardar(self.db, self.querys, {"evento": "resumen_diario", "nombre": config.get("nombre") or "Dueño",
                                               "telefono": config["telefono"], "mensaje": self.texto(self.build(dia)),
                                               "modo": modo, "estado": estado})
        except Exception:  # noqa: BLE001
            return False
        return estado == "pendiente"
