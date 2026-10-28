import secrets
from datetime import timedelta
from Utils.tools import Tools, CustomException, clean_text, now, to_local
from Utils.cifrado import cifrar, descifrar
from Utils.pasarelas import PASARELAS, MODOS_SIMULADA, obtener_pasarela, PasarelaNoDisponible
from Utils.realtime import realtime, channels_for
from Utils.telefono import normalizar_telefono
from Querys.caja import CajaQuerys
from Models.pago_linea_config_model import PagoLineaConfigModel
from Models.intento_pago_model import IntentoPagoModel, ESTADOS_INTENTO
from Models.webhook_pago_model import WebhookPagoModel
from Models.cuenta_model import CuentaModel
from Models.pago_model import PagoModel
from Models.medio_pago_model import MedioPagoModel
from Models.sesion_mesa_model import SesionMesaModel
from Models.mesa_model import MesaModel
from Class.Impuesto import Impuesto

MEDIO_EN_LINEA = "Pago en línea"
ESTADOS_TEXTO = {"pendiente": "Esperando pago", "aprobado": "Aprobado", "rechazado": "Rechazado", "expirado": "Expirado",
                 "reembolsado": "Reembolsado", "parcial": "Reembolsado en parte"}
AMBIENTES = ["pruebas", "produccion"]


class PagoLinea:
    """ Pagos en línea por pasarela (doc 20A): el cliente paga desde su celular, la pasarela avisa el
        resultado con una notificación firmada y el pago se aplica a la cuenta como en caja. """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = CajaQuerys(db, ctx)

    # ---- Configuración ----

    def get_config(self):
        return self.tools.output(200, "Pagos en línea.", self.format_config(self.config()))

    def save_config(self, data: dict):
        pasarela = data.get("pasarela") or "simulada"
        if pasarela not in PASARELAS:
            raise CustomException("La pasarela no está disponible.")
        ambiente = data.get("ambiente") or "pruebas"
        if ambiente not in AMBIENTES:
            raise CustomException("El ambiente no es válido.")
        minutos = int(data.get("minutos_expiracion") or 30)
        if minutos < 5 or minutos > 1440:
            raise CustomException("El tiempo para pagar debe estar entre 5 minutos y 24 horas.")
        config = self.config(lock=True)
        if not config:
            self.querys.insert_data(PagoLineaConfigModel, {}, commit=False)
            config = self.config(lock=True)
        guardadas = descifrar(config.credenciales)
        nuevas = {k: clean_text(str(v)) for k, v in (data.get("credenciales") or {}).items() if v not in (None, "")}
        if pasarela == "simulada":
            if nuevas.get("modo") and nuevas["modo"] not in MODOS_SIMULADA:
                raise CustomException("El modo de la pasarela simulada no es válido.")
            # La simulada firma con un secreto propio que se genera una vez
            nuevas.setdefault("secreto", guardadas.get("secreto") or secrets.token_hex(24))
        if nuevas:
            config.credenciales = cifrar({**guardadas, **nuevas})
        activo = data.get("activo") is True
        if activo and not config.credenciales:
            raise CustomException("Configura las credenciales de la pasarela antes de activar los pagos en línea.")
        antes = {"activo": config.activo, "pasarela": config.pasarela, "ambiente": config.ambiente}
        config.activo, config.pasarela, config.ambiente = activo, pasarela, ambiente
        config.permitir_propina = data.get("permitir_propina") is not False
        config.minutos_expiracion = minutos
        self.medio_en_linea()
        self.querys.audit("pagos_linea_configurados", "pago_linea_config", config.id, antes=antes,
                          despues={"activo": activo, "pasarela": pasarela, "ambiente": ambiente}, commit=False)
        self.db.commit()
        return self.tools.output(200, "Pagos en línea guardados.", self.format_config(config))

    # ---- Cobro ----

    def link(self, data: dict):
        """ Enlace para que el cliente pague desde su celular; se envía por WhatsApp (doc 31B) """
        self.check_active()
        sesion = self.querys.get_own(SesionMesaModel, data["sesion_mesa_id"], "pedido")
        if sesion.estado != "abierta":
            raise CustomException("Ese pedido ya no tiene nada por cobrar.", 409)
        ordenes = self.querys.ordenes_de_sesion(sesion.id)
        if not ordenes:
            raise CustomException("Ese pedido no tiene órdenes.", 409)
        cuenta = self.account_for(sesion)
        saldo = cuenta.total - cuenta.pagado
        if saldo <= 0:
            raise CustomException("La cuenta ya está pagada.", 409)
        ultima = ordenes[-1]
        telefono = next((o.cliente_telefono for o in reversed(ordenes) if o.cliente_telefono), None)
        try:
            telefono = normalizar_telefono(telefono)
        except CustomException:
            telefono = None
        self.db.commit()
        return self.tools.output(200, "Enlace de pago listo.", {
            "seguimiento": ultima.token_seguimiento, "saldo": saldo, "telefono": telefono,
            "cliente_nombre": next((o.cliente_nombre for o in ordenes if o.cliente_nombre), None),
            "restaurante": self.querys.restaurante_actual().nombre,
        })

    def create_attempt(self, sesion, propina: int, clave: str, origen: str):
        """ Intento con monto fijo: saldo de la cuenta más la propina (RN-PAG-02). Idempotente por clave. """
        config = self.check_active()
        existente = self.querys.scoped(IntentoPagoModel).filter(IntentoPagoModel.clave_idempotencia == clave).first()
        if existente:
            return existente
        if sesion.estado != "abierta":
            raise CustomException("Esta cuenta ya no tiene nada por pagar.", 409)
        cuenta = self.account_for(sesion, lock=True)
        saldo = cuenta.total - cuenta.pagado
        if saldo <= 0:
            raise CustomException("Esta cuenta ya está pagada.", 409)
        if propina and not config.permitir_propina:
            propina = 0
        if propina < 0 or propina > saldo:
            raise CustomException("La propina no es válida.")
        intento_id = self.querys.insert_data(IntentoPagoModel, {
            "cuenta_id": cuenta.id, "referencia": f"P{self.ctx['restaurante_id']}-{secrets.token_hex(8).upper()}",
            "token": secrets.token_urlsafe(24), "clave_idempotencia": clave, "pasarela": config.pasarela,
            "monto": saldo + propina, "propina": propina, "estado": "pendiente", "origen": origen,
            "expira_en": now() + timedelta(minutes=config.minutos_expiracion),
        }, commit=False)
        intento = self.db.get(IntentoPagoModel, intento_id)
        pasarela = obtener_pasarela(config.pasarela, descifrar(config.credenciales), config.ambiente)
        try:
            intento.url_pago = pasarela.crear_sesion({"referencia": intento.referencia, "monto": intento.monto,
                                                      "descripcion": f"Cuenta {cuenta.id}"})
        except PasarelaNoDisponible:
            self.db.rollback()
            raise CustomException("No pudimos conectar con la pasarela de pagos. Puedes pagar en caja.", 409)
        self.querys.audit("intento_pago_creado", "intento_pago", intento.id, despues={"monto": intento.monto,
                                                                                    "propina": propina}, commit=False)
        return intento

    # ---- Resultado de la pasarela ----

    def process_notification(self, intento, notificacion, webhook):
        """ Aplica el resultado firmado. Repetidos o fuera de orden no cambian un estado final. """
        if notificacion.monto is not None and int(notificacion.monto) != intento.monto:
            webhook.resultado = "El monto no coincide con el intento: no se aplica."
            return
        if notificacion.estado == "aprobado":
            if intento.estado in ("aprobado", "reembolsado", "parcial"):
                webhook.resultado = "Ya estaba aprobado."
                return
            intento.estado, intento.aprobado_en = "aprobado", now()
            intento.transaccion_id = notificacion.transaccion_id
            intento.comision = notificacion.comision
            webhook.resultado = self.apply(intento)
        elif notificacion.estado == "rechazado":
            if intento.estado in ("pendiente", "expirado"):
                intento.estado = "rechazado"
                intento.transaccion_id = notificacion.transaccion_id
                webhook.resultado = "Rechazado."
            else:
                webhook.resultado = f"Ignorado: el intento ya está {intento.estado}."
        else:
            webhook.resultado = "Estado desconocido."

    def apply(self, intento):
        """ Abona a la cuenta lo aprobado. Si la cuenta cambió, se abona hasta el saldo y lo demás queda
            por reembolsar; si ya estaba pagada o anulada, todo queda por reembolsar (doc 20A, sección 4). """
        from Class.Cuenta import Cuenta
        from Class.Documento import Documento
        cuenta = self.querys.get_own(CuentaModel, intento.cuenta_id, "cuenta", lock=True)
        if cuenta.estado != "abierta":
            intento.excedente = intento.monto
            self.querys.audit("pago_linea_sin_aplicar", "intento_pago", intento.id,
                              despues={"monto": intento.monto, "cuenta": cuenta.estado}, commit=False)
            return "La cuenta ya estaba cerrada: el pago queda por reembolsar."
        cuentas = Cuenta(self.db, self.ctx)
        cuentas.refresh(cuenta)
        if intento.propina:
            cuenta.propina += intento.propina
            cuentas.recalc(cuenta)
        saldo = cuenta.total - cuenta.pagado
        aplicar = min(intento.monto, saldo)
        caja = self.querys.get_caja()
        turno = self.querys.get_turno_abierto(caja.id)
        pago = PagoModel(self.querys._with_tenant(PagoModel, {
            "cuenta_id": cuenta.id, "turno_caja_id": turno.id if turno else None, "medio_pago_id": self.medio_en_linea().id,
            "monto": aplicar, "referencia": (intento.transaccion_id or intento.referencia)[:60],
            "clave_idempotencia": f"linea:{intento.referencia}", "usuario_id": None,
        }))
        self.db.add(pago)
        self.db.flush()
        cuenta.pagado += aplicar
        intento.pago_id, intento.aplicado, intento.excedente = pago.id, aplicar, intento.monto - aplicar
        documento = None
        if cuenta.pagado >= cuenta.total:
            cuentas.settle(cuenta, turno)
            documento, _ = Documento(self.db, self.ctx).generate_for_account(cuenta, None, caja.id)
        self.querys.audit("pago_linea_aplicado", "intento_pago", intento.id, despues={
            "aplicado": aplicar, "excedente": intento.excedente, "cuenta": cuenta.estado}, commit=False)
        self.pending_wakeups = {"documento": bool(documento), "cuenta": cuenta}
        if intento.excedente:
            return f"Aplicado {aplicar}; {intento.excedente} queda por reembolsar."
        return "Pago aplicado a la cuenta." if cuenta.estado == "abierta" else "Pago aplicado: cuenta pagada."

    def after_commit(self):
        datos = getattr(self, "pending_wakeups", None)
        if not datos:
            return
        cuenta = datos["cuenta"]
        realtime.publish(cuenta.restaurante_id, channels_for(cuenta.zona_id),
                         {"tipo": "cuenta.pagada" if cuenta.estado == "pagada" else "cuenta.abonada",
                          "cuenta_id": cuenta.id, "mesa_id": cuenta.mesa_id})
        if datos["documento"]:
            from Utils.emision import cola_emision
            cola_emision.despertar()

    # ---- Reembolsos y conciliación ----

    def refund(self, data: dict):
        """ Devolución por la pasarela, con permiso y motivo (RN-PAG-03). Solo lo que no está abonado a
            una cuenta vigente: si el pago está aplicado, primero se anula en caja. """
        intento = self.querys.get_own(IntentoPagoModel, data["intento_pago_id"], "pago en línea", lock=True)
        if intento.estado not in ("aprobado", "parcial"):
            raise CustomException("Solo se reembolsa un pago aprobado.", 409)
        disponible = self.refundable(intento)
        monto = int(data.get("monto") or disponible)
        if monto <= 0 or monto > disponible:
            raise CustomException(f"Se pueden reembolsar hasta {self.tools.format_number(disponible)}. "
                                  "Si el pago está abonado a una cuenta, anula primero ese pago en caja.")
        config = self.config()
        pasarela = obtener_pasarela(intento.pasarela, descifrar(config.credenciales), config.ambiente)
        try:
            pasarela.reembolsar(intento.transaccion_id, monto)
        except PasarelaNoDisponible as error:
            raise CustomException(f"{error} Intenta el reembolso más tarde.", 409)
        motivo = clean_text(data["motivo"])
        intento.reembolsado += monto
        intento.motivo_reembolso = motivo
        intento.estado = "reembolsado" if intento.reembolsado >= intento.monto else "parcial"
        self.querys.audit("pago_linea_reembolsado", "intento_pago", intento.id, despues={"monto": monto}, motivo=motivo,
                          commit=False)
        self.db.commit()
        return self.tools.output(200, f"Reembolso de {self.tools.format_number(monto)} solicitado a la pasarela.",
                                 self.format(intento))

    def list(self, data: dict):
        self.expire_old()
        query = self.querys.scoped(IntentoPagoModel)
        if data.get("estado"):
            if data["estado"] == "por_reembolsar":
                query = query.filter(IntentoPagoModel.excedente > IntentoPagoModel.reembolsado,
                                     IntentoPagoModel.estado.in_(["aprobado", "parcial"]))
            elif data["estado"] in ESTADOS_INTENTO:
                query = query.filter(IntentoPagoModel.estado == data["estado"])
            else:
                raise CustomException("El estado no es válido.")
        desde, hasta = Impuesto.parse_date(data.get("desde")), Impuesto.parse_date(data.get("hasta"))
        if desde:
            query = query.filter(IntentoPagoModel.creado_en >= desde)
        if hasta:
            query = query.filter(IntentoPagoModel.creado_en < hasta + timedelta(days=1))
        filas = query.order_by(IntentoPagoModel.id.desc()).limit(300).all()
        aprobados = [f for f in filas if f.estado in ("aprobado", "reembolsado", "parcial")]
        resumen = {
            "bruto": sum(f.monto for f in aprobados),
            "comision": sum(f.comision or 0 for f in aprobados),
            "reembolsado": sum(f.reembolsado for f in aprobados),
            "por_reembolsar": sum(self.refundable(f) for f in aprobados if f.excedente > f.reembolsado),
            "sin_abono": sum(1 for f in aprobados if not f.fecha_abono),
        }
        resumen["neto"] = resumen["bruto"] - resumen["comision"] - resumen["reembolsado"]
        self.db.commit()
        return self.tools.output(200, "Pagos en línea.", {"pagos": [self.format(f) for f in filas], "resumen": resumen})

    def reconcile(self, data: dict):
        """ Marca un pago como abonado por la pasarela, con su comisión real (doc 20A, sección 5) """
        intento = self.querys.get_own(IntentoPagoModel, data["intento_pago_id"], "pago en línea", lock=True)
        if intento.estado not in ("aprobado", "reembolsado", "parcial"):
            raise CustomException("Solo se concilia un pago aprobado.", 409)
        intento.fecha_abono = Impuesto.parse_date(data["fecha_abono"])
        if data.get("comision") not in (None, ""):
            comision = int(data["comision"])
            if comision < 0 or comision > intento.monto:
                raise CustomException("La comisión no es válida.")
            intento.comision = comision
        intento.nota_conciliacion = clean_text(data.get("nota"))
        self.db.commit()
        return self.tools.output(200, "Pago conciliado.", self.format(intento))

    # ---- Apoyo ----

    def config(self, lock=False):
        query = self.querys.scoped(PagoLineaConfigModel)
        if lock:
            query = query.with_for_update()
        return query.first()

    def check_active(self):
        if "pagos_linea" not in (self.ctx.get("modulos") or set()):
            raise CustomException("El restaurante no tiene contratados los pagos en línea.", 403)
        config = self.config()
        if not config or not config.activo:
            raise CustomException("Los pagos en línea no están activos en este restaurante.", 409)
        return config

    def account_for(self, sesion, lock=False):
        from Class.Cuenta import Cuenta
        cuenta = self.querys.get_cuenta_by_sesion(sesion.id, lock=lock)
        if not cuenta:
            mesa = self.db.get(MesaModel, sesion.mesa_id)
            try:
                self.querys.insert_data(CuentaModel, {"sesion_mesa_id": sesion.id, "mesa_id": mesa.id, "zona_id": mesa.zona_id},
                                        commit=False)
            except CustomException:
                self.db.rollback()
            cuenta = self.querys.get_cuenta_by_sesion(sesion.id, lock=lock)
        Cuenta(self.db, self.ctx).refresh(cuenta)
        return cuenta

    def medio_en_linea(self):
        medio = self.querys.scoped(MedioPagoModel).filter(MedioPagoModel.tipo == "en_linea").first()
        if not medio:
            medio_id = self.querys.insert_data(MedioPagoModel, {"nombre": MEDIO_EN_LINEA, "tipo": "en_linea", "orden": 99,
                                                                "activo": True}, commit=False)
            medio = self.db.get(MedioPagoModel, medio_id)
        return medio

    def refundable(self, intento):
        """ Lo que se puede devolver: lo no abonado a una cuenta vigente, menos lo ya devuelto """
        vigente = 0
        if intento.pago_id:
            pago = self.db.get(PagoModel, intento.pago_id)
            vigente = intento.aplicado if pago and pago.estado == "aplicado" else 0
        return max(intento.monto - vigente - intento.reembolsado, 0)

    def expire_old(self):
        self.querys.scoped(IntentoPagoModel).filter(IntentoPagoModel.estado == "pendiente",
                                                    IntentoPagoModel.expira_en < now()).update(
            {"estado": "expirado"}, synchronize_session=False)

    def format_config(self, config):
        credenciales = descifrar(config.credenciales) if config else {}
        return {
            "activo": bool(config and config.activo), "pasarela": config.pasarela if config else "simulada",
            "pasarelas": list(PASARELAS), "ambiente": config.ambiente if config else "pruebas",
            "tiene_credenciales": bool(config and config.credenciales),
            "modo_simulada": credenciales.get("modo", "normal"),
            "permitir_propina": config.permitir_propina if config else True,
            "minutos_expiracion": config.minutos_expiracion if config else 30,
            "contratado": "pagos_linea" in (self.ctx.get("modulos") or set()),
        }

    def format(self, intento):
        cuenta = self.db.get(CuentaModel, intento.cuenta_id)
        mesa = self.db.get(MesaModel, cuenta.mesa_id) if cuenta else None
        ordenes = self.querys.ordenes_de_sesion(cuenta.sesion_mesa_id) if cuenta else []
        return {
            "id": intento.id, "referencia": intento.referencia, "estado": intento.estado,
            "estado_texto": ESTADOS_TEXTO[intento.estado], "origen": intento.origen, "monto": intento.monto,
            "propina": intento.propina, "aplicado": intento.aplicado, "excedente": intento.excedente,
            "reembolsado": intento.reembolsado, "reembolsable": self.refundable(intento) if intento.estado in ("aprobado", "parcial") else 0,
            "motivo_reembolso": intento.motivo_reembolso, "transaccion_id": intento.transaccion_id,
            "comision": intento.comision, "neto": intento.monto - (intento.comision or 0) - intento.reembolsado,
            "fecha_abono": intento.fecha_abono, "nota_conciliacion": intento.nota_conciliacion,
            "cuenta_id": intento.cuenta_id, "cuenta_estado": cuenta.estado if cuenta else None,
            "cuenta_numero": f"C-{cuenta.numero:05d}" if cuenta and cuenta.numero else None,
            "mesa": (next((o.cliente_nombre for o in ordenes if o.cliente_nombre), None) or mesa.nombre) if mesa and mesa.tipo == "externa"
            else (mesa.nombre if mesa else None),
            "creado_en": intento.creado_en, "hora_local": to_local(intento.creado_en, self.ctx.get("zona_horaria")),
            "aprobado_en": intento.aprobado_en,
        }


def registrar_webhook(db, pasarela_nombre: str, cuerpo: bytes, cabeceras: dict):
    """ Entrada del aviso de la pasarela: se ubica el intento por su referencia (sin sesión de empresa,
        como al resolver un QR), se guarda crudo, se verifica la firma y se procesa (RN-API-06).
        Devuelve (código HTTP, mensaje). """
    from Utils.pasarelas import obtener_pasarela as pasarela_de
    clase = PASARELAS.get(pasarela_nombre)
    if not clase:
        return 404, "Pasarela desconocida."
    try:
        referencia = clase({}, "pruebas").interpretar(cuerpo).referencia
    except Exception:  # noqa: BLE001
        return 400, "Aviso ilegible."
    intento = db.query(IntentoPagoModel).filter(IntentoPagoModel.referencia == referencia).first()
    if not intento:
        return 404, "Referencia desconocida."
    from Utils.contexto import modulos_activos
    from Models.restaurante_model import RestauranteModel
    restaurante = db.get(RestauranteModel, intento.restaurante_id)
    modulos, _ = modulos_activos(db, restaurante)
    # Con los módulos reales: con facturación contratada, la cuenta pagada sale con su documento de venta
    ctx = {"empresa_id": intento.empresa_id, "restaurante_id": intento.restaurante_id, "usuario_id": None,
           "zona_horaria": restaurante.zona_horaria, "hora_inicio_jornada": restaurante.hora_inicio_jornada,
           "publico": True, "modulos": set(modulos), "permisos": set()}
    pagos = PagoLinea(db, ctx)
    config = pagos.config()
    pasarela = pasarela_de(pasarela_nombre, descifrar(config.credenciales) if config else {}, config.ambiente if config else "pruebas")
    valida = pasarela.verificar_firma(cuerpo, {k.lower(): v for k, v in cabeceras.items()})
    notificacion = pasarela.interpretar(cuerpo)
    webhook = WebhookPagoModel(pagos.querys._with_tenant(WebhookPagoModel, {
        "intento_pago_id": intento.id, "pasarela": pasarela_nombre, "cuerpo": cuerpo.decode(errors="replace")[:4000],
        "firma_valida": valida, "estado_recibido": notificacion.estado}))
    db.add(webhook)
    if not valida:
        webhook.resultado = "Firma no válida: se ignora."
        db.commit()
        return 401, "Firma no válida."
    intento = pagos.querys.get_own(IntentoPagoModel, intento.id, "intento", lock=True)
    pagos.process_notification(intento, notificacion, webhook)
    webhook.procesado_en = now()
    db.commit()
    pagos.after_commit()
    return 200, webhook.resultado
