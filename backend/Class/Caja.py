from Utils.tools import Tools, CustomException, clean_text, jornada, now
from Utils.realtime import realtime
from Querys.caja import CajaQuerys
from Models.turno_caja_model import TurnoCajaModel
from Models.movimiento_caja_model import MovimientoCajaModel, TIPOS_MOVIMIENTO
from Models.medio_pago_model import MedioPagoModel, TIPOS_MEDIO, MEDIOS_SISTEMA
from Models.cierre_jornada_model import CierreJornadaModel
from Class.TurnoMesero import TurnoMesero

MAX_MONTO = 1_000_000_000


def dia_actual(ctx: dict):
    return jornada(tz_name=ctx.get("zona_horaria"), inicio=ctx.get("hora_inicio_jornada"))


def validar_monto(valor, campo="monto", permitir_cero=False):
    monto = int(valor)
    if monto < 0 or (monto == 0 and not permitir_cero) or monto > MAX_MONTO:
        raise CustomException(f"El {campo} no es válido.")
    return monto


class Caja:
    """ Turnos de caja, movimientos de efectivo, medios de pago y cierre de jornada (doc 20) """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = CajaQuerys(db, ctx)

    # Lo que necesita la pantalla de caja: turno abierto, medios y jornada
    def status(self):
        caja = self.querys.get_caja()
        turno = self.querys.get_turno_abierto(caja.id)
        dia = dia_actual(self.ctx)
        restaurante = self.querys.restaurante_actual()
        return self.tools.output(200, "Estado de caja.", {
            "caja": {"id": caja.id, "nombre": caja.nombre},
            "turno": self.querys.format_turno(turno) if turno else None,
            "medios": [self.format_medio(m) for m in self.querys.medios() if m.tipo not in MEDIOS_SISTEMA],
            "jornada": dia,
            "jornada_cerrada": self.querys.jornada_cerrada(dia),
            "propina_sugerida": restaurante.propina_sugerida,
        })

    # Apertura con fondo inicial de efectivo (doc 20, sección 2)
    def open_shift(self, data: dict):

        caja = self.querys.get_caja()
        dia = dia_actual(self.ctx)
        if self.querys.jornada_cerrada(dia):
            raise CustomException("La jornada de hoy ya se cerró. El turno se abre en la próxima jornada.", 409)
        abierto = self.querys.get_turno_abierto(caja.id, lock=True)
        if abierto:
            raise CustomException(f"Ya hay un turno abierto por {self.querys.nombre_usuario(abierto.usuario_id)}.", 409)

        fondo = validar_monto(data.get("fondo_inicial") or 0, "fondo inicial", permitir_cero=True)
        try:
            turno_id = self.querys.insert_data(TurnoCajaModel, {
                "caja_id": caja.id, "usuario_id": self.ctx["usuario_id"], "jornada": dia,
                "abierto_en": now(), "fondo_inicial": fondo,
            }, commit=False)
        except CustomException:
            raise CustomException("Otro usuario acaba de abrir el turno de esta caja.", 409)
        self.querys.audit("turno_abierto", "turno_caja", turno_id, despues={"fondo_inicial": fondo})

        turno = self.db.get(TurnoCajaModel, turno_id)
        return self.tools.output(201, "Turno abierto.", self.querys.format_turno(turno))

    # Cierre con arqueo: contado vs. esperado (RN-CAJ-06)
    def close_shift(self, data: dict):

        caja = self.querys.get_caja()
        turno = self.querys.get_turno_abierto(caja.id, lock=True)
        if not turno:
            raise CustomException("No hay un turno abierto.", 409)

        pendientes = self.querys.cuentas_abiertas_con_pagos()
        if pendientes and data.get("confirmar_pendientes") is not True:
            raise CustomException(
                f"Hay {len(pendientes)} cuentas con pago parcial sin terminar. Confirma para cerrar el turno de todas formas.",
                409, {"cuentas_pendientes": len(pendientes)})

        resumen = self.querys.resumen_turno(turno)
        contado = validar_monto(data["efectivo_contado"], "efectivo contado", permitir_cero=True)
        turno.estado = "cerrado"
        turno.cerrado_en = now()
        turno.cerrado_por = self.ctx["usuario_id"]
        turno.efectivo_esperado = resumen["efectivo_esperado"]
        turno.efectivo_contado = contado
        turno.diferencia = contado - resumen["efectivo_esperado"]
        turno.observacion = clean_text(data.get("observacion"))
        self.db.flush()
        self.querys.audit("turno_cerrado", "turno_caja", turno.id, despues={
            "esperado": turno.efectivo_esperado, "contado": contado, "diferencia": turno.diferencia,
        }, motivo=turno.observacion)

        msg = "Turno cerrado. El efectivo cuadra." if turno.diferencia == 0 else \
            f"Turno cerrado con diferencia de {self.tools.format_number(turno.diferencia)}."
        return self.tools.output(200, msg, self.querys.format_turno(turno))

    def get_shift(self, data: dict):
        turno = self.querys.get_own(TurnoCajaModel, data["turno_id"], "turno")
        return self.tools.output(200, "Informe del turno.", self.querys.format_turno(turno))

    def list_shifts(self, data: dict):
        turnos = [self.querys.format_turno(t, con_resumen=False) for t in self.querys.list_turnos(int(data.get("limite") or 20))]
        return self.tools.output(200, "Turnos de caja." if turnos else "Aún no hay turnos.", turnos)

    # Gastos menores, retiros y aportes (doc 20, sección 7)
    def movement(self, data: dict):

        tipo = data["tipo"]
        if tipo not in TIPOS_MOVIMIENTO:
            raise CustomException("El tipo de movimiento no es válido.")
        caja = self.querys.get_caja()
        turno = self.querys.get_turno_abierto(caja.id)
        if not turno:
            raise CustomException("Abre el turno de caja antes de registrar movimientos.", 409)

        monto = validar_monto(data["monto"])
        if tipo in ["gasto", "retiro"]:
            disponible = self.querys.resumen_turno(turno)["efectivo_esperado"]
            if monto > disponible:
                raise CustomException(f"En caja debería haber {self.tools.format_number(disponible)}: no alcanza para este {tipo}.")

        movimiento_id = self.querys.insert_data(MovimientoCajaModel, {
            "turno_caja_id": turno.id, "tipo": tipo, "monto": monto,
            "concepto": clean_text(data["concepto"]), "usuario_id": self.ctx["usuario_id"],
        }, commit=False)
        self.querys.audit(f"caja_{tipo}", "movimiento_caja", movimiento_id, despues={"monto": monto},
                          motivo=clean_text(data["concepto"]))

        nombres = {"gasto": "Gasto registrado.", "retiro": "Retiro registrado.", "aporte": "Aporte registrado."}
        return self.tools.output(201, nombres[tipo], self.querys.format_turno(turno))

    def list_payment_methods(self, data: dict):
        medios = [self.format_medio(m) for m in self.querys.medios(incluir_inactivos=data.get("todos") is True)
                  if m.tipo not in MEDIOS_SISTEMA]
        return self.tools.output(200, "Medios de pago.", medios)

    def save_payment_method(self, data: dict):

        tipo = data.get("tipo") or "otro"
        if tipo not in TIPOS_MEDIO or tipo in MEDIOS_SISTEMA:
            raise CustomException("El tipo de medio de pago no es válido.")
        fields = {
            "nombre": clean_text(data["nombre"]),
            "tipo": tipo,
            "pide_referencia": data.get("pide_referencia") is True,
            "orden": int(data.get("orden") or 0),
            "activo": data.get("activo") is not False,
        }
        existentes = {m.nombre.lower(): m for m in self.querys.medios(incluir_inactivos=True)}
        mismo = existentes.get(fields["nombre"].lower())

        if data.get("medio_pago_id"):
            medio = self.querys.get_own(MedioPagoModel, data["medio_pago_id"], "medio de pago")
            if medio.tipo in MEDIOS_SISTEMA:
                raise CustomException("Ese medio lo registra la pasarela de pagos y no se edita.")
            if mismo and mismo.id != medio.id:
                raise CustomException("Ya existe un medio de pago con ese nombre.")
            if medio.tipo == "efectivo" and (tipo != "efectivo" or not fields["activo"]):
                raise CustomException("El efectivo no se puede desactivar ni cambiar de tipo: lo usa el arqueo.")
            self.querys.update_data(MedioPagoModel, medio.id, fields, "medio de pago")
            return self.tools.output(200, "Medio de pago actualizado.", self.format_medio(medio))

        if mismo:
            raise CustomException("Ya existe un medio de pago con ese nombre.")
        if tipo == "efectivo":
            raise CustomException("El restaurante ya tiene el medio efectivo.")
        medio_id = self.querys.insert_data(MedioPagoModel, fields)
        return self.tools.output(201, "Medio de pago creado.", self.format_medio(self.db.get(MedioPagoModel, medio_id)))

    # Qué falta para poder cerrar la jornada (doc 20, sección 8)
    def day_status(self):
        dia = dia_actual(self.ctx)
        cierre = self.querys.get_cierre(dia)
        sesiones = self.querys.sesiones_abiertas()
        turnos = self.querys.turnos_abiertos()
        return self.tools.output(200, "Estado de la jornada.", {
            "jornada": dia,
            "cerrada": cierre is not None,
            "resumen": cierre.resumen if cierre else self.day_summary(dia),
            "bloqueos": {
                "turnos_abiertos": len(turnos),
                "mesas_abiertas": sum(1 for s in sesiones if not s.es_externa),
                "pedidos_externos_abiertos": sum(1 for s in sesiones if s.es_externa),
            },
        })

    def close_day(self, data: dict):

        dia = dia_actual(self.ctx)
        if self.querys.jornada_cerrada(dia):
            raise CustomException("La jornada ya estaba cerrada.", 409)
        if self.querys.turnos_abiertos():
            raise CustomException("Cierra el turno de caja antes de cerrar la jornada.", 409)
        sesiones = self.querys.sesiones_abiertas()
        if sesiones:
            raise CustomException(
                f"Hay {len(sesiones)} mesas o pedidos sin cobrar. Cóbralos o anúlalos antes de cerrar la jornada.", 409)

        resumen = self.day_summary(dia)
        self.querys.insert_data(CierreJornadaModel, {"jornada": dia, "cerrado_por": self.ctx["usuario_id"],
                                                     "resumen": resumen}, commit=False)
        restaurante = self.querys.restaurante_actual()
        reiniciados = self.querys.reset_agotados() if restaurante.reiniciar_agotados else 0
        TurnoMesero(self.db, self.ctx).close_all()
        self.querys.audit("jornada_cerrada", "cierre_jornada", None,
                          despues={"jornada": str(dia), "ventas": resumen["ventas"], "agotados_reiniciados": reiniciados})
        realtime.publish(self.ctx["restaurante_id"], ["ordenes"], {"tipo": "jornada.cerrada", "jornada": str(dia)})

        return self.tools.output(200, "Jornada cerrada. No se reciben más órdenes ni cobros hasta la próxima.",
                                 {"jornada": dia, "resumen": resumen})

    # Totales de la jornada que se congelan al cerrar
    def day_summary(self, dia):
        pagadas = self.querys.cuentas_de_jornada(dia, "pagada")
        anuladas = self.querys.cuentas_de_jornada(dia, "anulada")
        medios = {m.id: m.nombre for m in self.querys.medios(incluir_inactivos=True)}
        por_medio = {}
        for cuenta in pagadas:
            for pago in self.querys.pagos_de(cuenta.id):
                if pago.estado == "aplicado":
                    nombre = medios.get(pago.medio_pago_id, "?")
                    por_medio[nombre] = por_medio.get(nombre, 0) + pago.monto
        ventas = sum(c.subtotal - c.descuento - c.descuento_cupon for c in pagadas)
        return {
            "jornada": str(dia),
            "cuentas": len(pagadas),
            "ventas": ventas,
            "propinas": sum(c.propina for c in pagadas),
            "descuentos": sum(c.descuento + c.descuento_cupon for c in pagadas),
            "cupones": sum(c.descuento_cupon + c.descuento_envio for c in pagadas),
            "domicilios": sum(c.envio - c.descuento_envio for c in pagadas),
            "ticket_promedio": round(ventas / len(pagadas)) if pagadas else 0,
            "cuentas_anuladas": len(anuladas),
            "por_medio": por_medio,
        }

    def format_medio(self, medio):
        return {"id": medio.id, "nombre": medio.nombre, "tipo": medio.tipo, "pide_referencia": medio.pide_referencia,
                "orden": medio.orden, "activo": medio.activo}
