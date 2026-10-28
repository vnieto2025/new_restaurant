from Utils.tools import Tools, CustomException, clean_text, now, to_local
from Utils.estados import PENDIENTE, DESPACHADO, ENTREGADO, CANCELADO
from Utils.realtime import realtime, channels_for
from Querys.entrega import EntregaQuerys
from Querys.orden import OrdenQuerys
from Querys.caja import CajaQuerys
from Querys.mesa import MesaQuerys
from Querys.facturacion import FacturacionQuerys
from Models.entrega_model import EntregaModel, DECISIONES_FALLO
from Models.zona_envio_model import ZonaEnvioModel
from Models.domiciliario_model import DomiciliarioModel
from Models.rendicion_model import RendicionModel
from Models.orden_model import OrdenModel
from Models.cuenta_model import CuentaModel
from Models.pago_model import PagoModel
from Models.sesion_mesa_model import SesionMesaModel
from Models.cliente_direccion_model import ClienteDireccionModel
from Class.Caja import dia_actual, validar_monto
from Utils.notificaciones import notificar
from Utils.mensajeria import cola_mensajes

ACTIVAS = ["pendiente_asignacion", "asignada", "en_camino"]
ESTADOS_TEXTO = {"pendiente_asignacion": "Sin domiciliario", "asignada": "Asignada", "en_camino": "En camino",
                 "entregada": "Entregada", "fallida": "Fallida"}
DECISIONES_TEXTO = {"reintento": "Se reintenta", "cancelacion": "Cancelada", "perdida": "Pérdida"}


class Entrega:
    """ Entregas a domicilio: asignación, salida, entrega, fallo y rendición del efectivo (doc 15B).
        La entrega va ligada a la orden y no reemplaza los estados de sus ítems. """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = EntregaQuerys(db, ctx)
        self.ordenes = OrdenQuerys(db, ctx)

    # ---- Al pedir ----

    def prepare(self, datos: dict, valor_items: int, cliente_nombre, cliente_telefono):
        """ Valida los datos de entrega antes de crear la orden (RN-DOM-01, RN-EXT-03) """
        if "domicilios" not in self.ctx.get("modulos", set()):
            raise CustomException("El restaurante no tiene contratado el módulo de domicilios.", 403)
        zona = self.querys.get_own(ZonaEnvioModel, datos.get("zona_envio_id"), "zona de envío")
        if not zona.activo:
            raise CustomException(f"La zona {zona.nombre} no está recibiendo domicilios.")
        if valor_items < zona.pedido_minimo:
            raise CustomException(f"El pedido mínimo para {zona.nombre} es {self.tools.format_number(zona.pedido_minimo)}.")
        telefono = clean_text(datos.get("telefono")) or clean_text(cliente_telefono)
        direccion = clean_text(datos.get("direccion"))
        if not telefono or not direccion or not clean_text(cliente_nombre):
            raise CustomException("Un domicilio necesita nombre, teléfono y dirección.")
        facturacion = FacturacionQuerys(self.db, self.ctx)
        defecto = facturacion.impuesto_defecto()
        porcentaje = facturacion.tarifas_vigentes(dia_actual(self.ctx)).get(defecto.id) if defecto else None
        return {
            "zona_envio_id": zona.id, "cliente_nombre": clean_text(cliente_nombre)[:100], "telefono": telefono[:30],
            "direccion": direccion[:200], "barrio": clean_text(datos.get("barrio")),
            "indicaciones": clean_text(datos.get("indicaciones")), "tarifa": zona.tarifa,
            "pago_domiciliario": zona.pago_domiciliario,
            "impuesto_id": defecto.id if defecto and porcentaje is not None else None, "impuesto_porcentaje": porcentaje,
            "guardar_direccion": datos.get("guardar_direccion") is True,
            "forma_pago": datos.get("forma_pago") if datos.get("forma_pago") in ("contra_entrega", "en_linea") else None,
        }

    def attach(self, orden, preparada: dict, cliente=None):
        guardar = preparada.pop("guardar_direccion")
        self.querys.insert_data(EntregaModel, {**preparada, "orden_id": orden.id, "sesion_mesa_id": orden.sesion_mesa_id},
                                commit=False)
        # La dirección queda en el cliente para el próximo pedido, si autorizó sus datos
        if guardar and cliente and cliente.datos_aceptado_en:
            existentes = self.querys.scoped(ClienteDireccionModel).filter(
                ClienteDireccionModel.cliente_id == cliente.id, ClienteDireccionModel.activo.is_(True)).all()
            if not any(d.direccion.lower() == preparada["direccion"].lower() for d in existentes):
                self.querys.insert_data(ClienteDireccionModel, {
                    "cliente_id": cliente.id, "direccion": preparada["direccion"], "barrio": preparada["barrio"],
                    "indicaciones": preparada["indicaciones"]}, commit=False)

    def cancel_unconfirmed(self, orden, motivo):
        """ Pedido web de domicilio rechazado antes de ir a cocina: la entrega se cierra sin cobrar el envío """
        entrega = self.querys.scoped(EntregaModel).filter(EntregaModel.orden_id == orden.id).with_for_update().first()
        if not entrega or entrega.estado not in ACTIVAS:
            return
        entrega.estado, entrega.decision, entrega.fallida_en = "fallida", "cancelacion", now()
        entrega.motivo_fallo = f"No confirmado: {motivo}"[:200]
        self.close_failed(entrega, motivo)

    # ---- Seguimiento ----

    def list(self, data: dict):
        """ Entregas activas y las cerradas de la jornada. El domiciliario solo ve las suyas. """
        propio = self.own_courier()
        dia = dia_actual(self.ctx)
        activas = self.querys.entregas(ACTIVAS, domiciliario_id=propio.id if propio else None)
        cerradas = self.querys.entregas(["entregada", "fallida"], jornada=dia, domiciliario_id=propio.id if propio else None)
        domiciliarios = [] if propio else [{
            "id": d.id, "nombre": d.nombre, "codigo": d.codigo, "en_camino": self.querys.en_camino_de(d.id),
        } for d in self.querys.domiciliarios()]
        return self.tools.output(200, "Entregas.", {
            "activas": [self.format(e) for e in activas],
            "cerradas": [self.format(e) for e in reversed(cerradas)],
            "domiciliarios": domiciliarios,
            "propio": {"id": propio.id, "nombre": propio.nombre, "codigo": propio.codigo} if propio else None,
            "motivos_fallo": ["Cliente ausente", "Dirección errada", "No contesta el teléfono", "Rechazó el pedido"],
        })

    def zones(self):
        from Class.Domicilio import Domicilio
        return Domicilio(self.db, self.ctx).list_zones({})

    def assign(self, data: dict):
        entrega = self.get(data["entrega_id"], lock=True)
        if entrega.estado not in ("pendiente_asignacion", "asignada"):
            raise CustomException("La entrega ya salió del local.", 409)
        domiciliario = self.querys.get_own(DomiciliarioModel, data["domiciliario_id"], "domiciliario")
        if not domiciliario.activo:
            raise CustomException(f"{domiciliario.nombre} está inactivo.")
        if self.awaiting_confirmation(entrega):
            raise CustomException("Confirma el pedido antes de asignarlo.", 409)
        entrega.domiciliario_id, entrega.estado, entrega.asignada_en = domiciliario.id, "asignada", now()
        self.db.commit()
        self.notify(entrega, "entrega.asignada")
        return self.tools.output(200, f"Asignada a {domiciliario.nombre} ({domiciliario.codigo}).", self.format(entrega))

    def depart(self, data: dict):
        """ Sale del local: todo lo de la orden debe estar listo. Queda lo que debe cobrar contra entrega. """
        entrega = self.get(data["entrega_id"], lock=True)
        self.check_courier(entrega)
        if entrega.estado != "asignada":
            raise CustomException("Asigna un domiciliario antes de que salga." if entrega.estado == "pendiente_asignacion"
                                  else "La entrega ya salió.", 409)
        items = [i for i in self.ordenes.items_of(entrega.orden_id) if i.estado != CANCELADO]
        if any(i.estado not in (DESPACHADO, ENTREGADO) for i in items):
            raise CustomException("La orden aún no está lista en cocina.", 409)
        saldo = self.balance(entrega)
        entrega.monto_a_cobrar, entrega.contra_entrega = saldo, saldo > 0
        entrega.estado, entrega.salida_en = "en_camino", now()
        en_cola = notificar(self.db, self.ctx, "domicilio_salio", self.db.get(OrdenModel, entrega.orden_id), entrega)
        self.db.commit()
        if en_cola:
            cola_mensajes.despertar()
        self.notify(entrega, "entrega.en_camino")
        mensaje = "Salió a domicilio." + (f" Debe cobrar {self.tools.format_number(saldo)}." if saldo else " Ya está pagada.")
        return self.tools.output(200, mensaje, self.format(entrega))

    def deliver(self, data: dict):
        entrega = self.get(data["entrega_id"], lock=True)
        self.check_courier(entrega)
        if entrega.estado != "en_camino":
            raise CustomException("Solo se marca entregada una entrega en camino.", 409)
        orden = self.querys.get_own(OrdenModel, entrega.orden_id, "orden", lock=True)
        for item in self.ordenes.items_of(orden.id, lock=True):
            if item.estado == DESPACHADO:
                self.ordenes.transition(item, ENTREGADO)
        entrega.estado, entrega.entregada_en = "entregada", now()
        self.close_session_if_settled(entrega)
        self.db.commit()
        self.notify(entrega, "entrega.entregada")
        return self.tools.output(200, "Entregada." + (" Recuerda rendir el efectivo en caja." if entrega.contra_entrega else ""),
                                 self.format(entrega))

    def fail(self, data: dict):
        """ No se pudo entregar: motivo y decisión (RN-DOM-04). Reintentar la devuelve a la lista;
            cancelar o darla por perdida cancela lo que quedaba y no cobra el domicilio. """
        entrega = self.get(data["entrega_id"], lock=True)
        self.check_courier(entrega)
        if entrega.estado not in ACTIVAS:
            raise CustomException("La entrega ya está cerrada.", 409)
        motivo, decision = clean_text(data["motivo"]), data["decision"]
        if decision not in DECISIONES_FALLO:
            raise CustomException("La decisión debe ser reintentar, cancelar o pérdida.")
        if decision != "reintento" and "domicilios.despachar" not in self.ctx.get("permisos", set()):
            raise CustomException("Solo quien despacha decide cancelar o dar por perdido un domicilio.", 403)
        self.querys.audit("entrega_fallida", "entrega", entrega.id, antes={"estado": entrega.estado},
                          despues={"decision": decision}, motivo=motivo, commit=False)
        entrega.intentos += 1
        entrega.motivo_fallo, entrega.decision, entrega.fallida_en = motivo, decision, now()
        if decision == "reintento":
            entrega.estado, entrega.domiciliario_id, entrega.salida_en = "pendiente_asignacion", None, None
            mensaje = "Vuelve a la lista para salir de nuevo."
        else:
            entrega.estado = "fallida"
            for item in self.ordenes.items_of(entrega.orden_id, lock=True):
                if item.estado not in (CANCELADO, ENTREGADO):
                    self.ordenes.transition(item, CANCELADO, motivo=f"Domicilio fallido: {motivo}"[:200])
            self.ordenes.recalc_total(self.db.get(OrdenModel, entrega.orden_id))
            mensaje = self.close_failed(entrega, motivo)
        en_cola = notificar(self.db, self.ctx, "entrega_fallida", self.db.get(OrdenModel, entrega.orden_id), entrega)
        self.db.commit()
        if en_cola:
            cola_mensajes.despertar()
        self.notify(entrega, "entrega.fallida")
        return self.tools.output(200, mensaje, self.format(entrega))

    # ---- Efectivo contra entrega ----

    def cash_pending(self, data: dict = None):
        """ Cuánto debe rendir cada domiciliario: las cuentas que cobró y aún no entrega en caja """
        grupos = {}
        for entrega in self.querys.por_rendir():
            saldo = self.balance(entrega)
            domiciliario = self.db.get(DomiciliarioModel, entrega.domiciliario_id)
            grupo = grupos.setdefault(domiciliario.id, {"domiciliario_id": domiciliario.id, "nombre": domiciliario.nombre,
                                                        "codigo": domiciliario.codigo, "esperado": 0, "entregas": []})
            grupo["esperado"] += saldo
            grupo["entregas"].append({"id": entrega.id, "orden": self.order_label(entrega), "cliente": entrega.cliente_nombre,
                                      "monto": saldo, "entregada_en": entrega.entregada_en})
        tz = self.ctx.get("zona_horaria")
        rendiciones = [{
            "id": r.id, "domiciliario": self.db.get(DomiciliarioModel, r.domiciliario_id).nombre, "esperado": r.esperado,
            "entregado": r.entregado, "diferencia": r.diferencia, "notas": r.notas, "hora_local": to_local(r.creado_en, tz),
            "usuario": CajaQuerys(self.db, self.ctx).nombre_usuario(r.usuario_id),
        } for r in self.querys.rendiciones(limite=20)]
        return self.tools.output(200, "Efectivo por rendir.", {"pendientes": list(grupos.values()), "rendiciones": rendiciones})

    def render(self, data: dict):
        """ El domiciliario entrega el efectivo: se cobran sus cuentas en el turno abierto y queda la
            diferencia con usuario (RN-DOM-03). Un faltante queda a su cargo y no descuadra el arqueo. """
        domiciliario = self.querys.get_own(DomiciliarioModel, data["domiciliario_id"], "domiciliario")
        caja = CajaQuerys(self.db, self.ctx)
        turno = caja.get_turno_abierto(caja.get_caja().id, lock=True)
        if not turno:
            raise CustomException("Abre el turno de caja para recibir el efectivo.", 409)
        entregas = self.querys.por_rendir(domiciliario.id)
        if not entregas:
            raise CustomException(f"{domiciliario.nombre} no tiene efectivo por rendir.", 409)
        entregado = validar_monto(data["entregado"], "valor entregado", permitir_cero=True)
        efectivo = next((m for m in caja.medios() if m.tipo == "efectivo"), None)

        from Class.Cuenta import Cuenta
        from Class.Documento import Documento
        cuentas_api = Cuenta(self.db, self.ctx)
        esperado, documentos = 0, False
        rendicion_id = self.querys.insert_data(RendicionModel, {
            "domiciliario_id": domiciliario.id, "turno_caja_id": turno.id, "esperado": 0, "entregado": entregado,
            "diferencia": 0, "notas": clean_text(data.get("notas")), "usuario_id": self.ctx.get("usuario_id"),
        }, commit=False)
        for entrega in entregas:
            cuenta = self.account_of(entrega, crear=True)
            if cuenta.estado == "abierta":
                cuentas_api.refresh(cuenta)
                saldo = cuenta.total - cuenta.pagado
                if saldo > 0:
                    self.db.add(PagoModel(caja._with_tenant(PagoModel, {
                        "cuenta_id": cuenta.id, "turno_caja_id": turno.id, "medio_pago_id": efectivo.id, "monto": saldo,
                        "recibido": saldo, "cambio": 0, "usuario_id": self.ctx.get("usuario_id"),
                        "clave_idempotencia": f"rendicion-{rendicion_id}:{entrega.id}",
                        "referencia": f"Domicilio {domiciliario.codigo}",
                    })))
                    cuenta.pagado += saldo
                    esperado += saldo
                cuentas_api.settle(cuenta, turno)
                documento, _ = Documento(self.db, self.ctx).generate_for_account(cuenta, None, caja.get_caja().id)
                documentos = documentos or bool(documento)
            entrega.rendicion_id = rendicion_id
        rendicion = self.db.get(RendicionModel, rendicion_id)
        rendicion.esperado, rendicion.diferencia = esperado, entregado - esperado
        self.querys.audit("rendicion_domiciliario", "rendicion", rendicion_id, despues={
            "esperado": esperado, "entregado": entregado, "diferencia": rendicion.diferencia}, motivo=rendicion.notas, commit=False)
        self.db.commit()
        if documentos:
            from Utils.emision import cola_emision
            cola_emision.despertar()
        if rendicion.diferencia == 0:
            mensaje = f"Rendición de {domiciliario.nombre} recibida. Cuadra."
        elif rendicion.diferencia < 0:
            mensaje = f"Rendición recibida con faltante de {self.tools.format_number(-rendicion.diferencia)} a cargo de {domiciliario.nombre}."
        else:
            mensaje = f"Rendición recibida con sobrante de {self.tools.format_number(rendicion.diferencia)}."
        return self.tools.output(200, mensaje, {"id": rendicion_id, "esperado": esperado, "entregado": entregado,
                                                "diferencia": rendicion.diferencia, "cuentas": len(entregas)})

    # ---- Apoyo ----

    def get(self, entrega_id, lock=False):
        return self.querys.get_own(EntregaModel, entrega_id, "entrega", lock=lock)

    def own_courier(self):
        """ Quien solo tiene el permiso de entregar es un domiciliario: trabaja con su propio registro """
        permisos = self.ctx.get("permisos", set())
        if "domicilios.despachar" in permisos:
            return None
        propio = self.querys.domiciliario_de_usuario(self.ctx.get("usuario_id"))
        if not propio:
            raise CustomException("Tu usuario no está ligado a un domiciliario. Pídeselo al administrador.", 403)
        return propio

    def check_courier(self, entrega):
        propio = self.own_courier()
        if propio and entrega.domiciliario_id != propio.id:
            raise CustomException("Esa entrega no es tuya.", 403)

    def account_of(self, entrega, crear=False):
        caja = CajaQuerys(self.db, self.ctx)
        cuenta = caja.get_cuenta_by_sesion(entrega.sesion_mesa_id, lock=True)
        if not cuenta and crear:
            orden = self.db.get(OrdenModel, entrega.orden_id)
            self.querys.insert_data(CuentaModel, {"sesion_mesa_id": entrega.sesion_mesa_id, "mesa_id": orden.mesa_id,
                                                  "zona_id": orden.zona_id}, commit=False)
            cuenta = caja.get_cuenta_by_sesion(entrega.sesion_mesa_id, lock=True)
        return cuenta

    def balance(self, entrega):
        """ Saldo por cobrar de la cuenta del domicilio (sin caja contratada no se cobra aquí) """
        if "caja" not in self.ctx.get("modulos", set()):
            return 0
        caja = CajaQuerys(self.db, self.ctx)
        cuenta = caja.get_cuenta_by_sesion(entrega.sesion_mesa_id)
        if cuenta and cuenta.estado != "abierta":
            return 0
        subtotal = caja.subtotal_de_sesion(entrega.sesion_mesa_id)
        envio = caja.envio_de_sesion(entrega.sesion_mesa_id)
        if not cuenta:
            return subtotal + envio
        descuentos = min(cuenta.descuento + cuenta.descuento_cupon, subtotal) + min(cuenta.descuento_envio, envio)
        return max(subtotal + envio - descuentos + cuenta.propina - cuenta.pagado, 0)

    def close_session_if_settled(self, entrega):
        """ Sin caja contratada, la sesión del pedido se cierra al entregar (como en mostrador) """
        if "caja" in self.ctx.get("modulos", set()):
            return
        sesion = self.db.get(SesionMesaModel, entrega.sesion_mesa_id)
        if sesion.estado == "abierta":
            MesaQuerys(self.db, self.ctx).close_session(sesion, self.ctx.get("usuario_id"))

    def close_failed(self, entrega, motivo):
        """ Domicilio cancelado o perdido: si no se pagó nada, la cuenta se anula y el pedido se cierra.
            Si ya se había pagado, caja decide la devolución anulando la cuenta. """
        cuenta = self.account_of(entrega)
        if cuenta and cuenta.pagado > 0:
            return "Domicilio cerrado. Ya tenía pagos: anula la cuenta en caja para devolver el dinero."
        if cuenta and cuenta.estado == "abierta":
            cuenta.estado, cuenta.anulada_en = "anulada", now()
            cuenta.anulada_por, cuenta.anulada_motivo = self.ctx.get("usuario_id"), f"Domicilio fallido: {motivo}"[:200]
            cuenta.jornada = dia_actual(self.ctx)
        sesion = self.db.get(SesionMesaModel, entrega.sesion_mesa_id)
        if sesion.estado == "abierta":
            MesaQuerys(self.db, self.ctx).close_session(sesion, self.ctx.get("usuario_id"))
        return "Domicilio cerrado. No se cobra."

    def awaiting_confirmation(self, entrega):
        return any(i.estado == PENDIENTE for i in self.ordenes.items_of(entrega.orden_id))

    def order_label(self, entrega):
        orden = self.db.get(OrdenModel, entrega.orden_id)
        return f"#{orden.numero:03d}"

    def format(self, entrega):
        orden = self.db.get(OrdenModel, entrega.orden_id)
        items = [i for i in self.ordenes.items_of(orden.id) if i.estado != CANCELADO]
        zona = self.db.get(ZonaEnvioModel, entrega.zona_envio_id)
        domiciliario = self.db.get(DomiciliarioModel, entrega.domiciliario_id) if entrega.domiciliario_id else None
        cuenta = CajaQuerys(self.db, self.ctx).get_cuenta_by_sesion(entrega.sesion_mesa_id)
        tz = self.ctx.get("zona_horaria")
        return {
            "id": entrega.id, "orden_id": orden.id, "orden": f"#{orden.numero:03d}", "estado": entrega.estado,
            "estado_texto": ESTADOS_TEXTO[entrega.estado],
            "lista": bool(items) and all(i.estado in (DESPACHADO, ENTREGADO) for i in items),
            # Pedido hecho por el cliente en la web: puede esperar la confirmación de quien despacha
            "web": orden.creado_por is None, "por_confirmar": any(i.estado == PENDIENTE for i in items),
            "forma_pago": entrega.forma_pago,
            "items": [{"nombre": i.nombre_producto, "cantidad": i.cantidad, "estado": i.estado} for i in items],
            "cliente_nombre": entrega.cliente_nombre, "telefono": entrega.telefono, "direccion": entrega.direccion,
            "barrio": entrega.barrio, "indicaciones": entrega.indicaciones,
            "zona_envio": zona.nombre if zona else None, "tarifa": entrega.tarifa,
            "domiciliario": {"id": domiciliario.id, "nombre": domiciliario.nombre, "codigo": domiciliario.codigo}
            if domiciliario else None,
            "por_cobrar": self.balance(entrega) if entrega.estado in ACTIVAS else entrega.monto_a_cobrar,
            "pagada": bool(cuenta and cuenta.estado == "pagada"),
            "contra_entrega": entrega.contra_entrega, "rendida": entrega.rendicion_id is not None,
            "intentos": entrega.intentos, "motivo_fallo": entrega.motivo_fallo,
            "decision": entrega.decision, "decision_texto": DECISIONES_TEXTO.get(entrega.decision),
            "creado_en": entrega.creado_en, "hora_pedido": to_local(entrega.creado_en, tz),
            "salida_en": entrega.salida_en, "hora_salida": to_local(entrega.salida_en, tz),
            "entregada_en": entrega.entregada_en, "hora_entrega": to_local(entrega.entregada_en, tz),
            "notas": orden.notas,
        }

    def notify(self, entrega, tipo: str):
        orden = self.db.get(OrdenModel, entrega.orden_id)
        realtime.publish(orden.restaurante_id, channels_for(orden.zona_id), {
            "tipo": tipo, "entrega_id": entrega.id, "orden_id": orden.id, "numero": orden.numero, "zona_id": orden.zona_id})
