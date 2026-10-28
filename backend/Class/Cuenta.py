from sqlalchemy.exc import IntegrityError
from Utils.tools import Tools, CustomException, clean_text, now
from Utils.realtime import realtime, channels_for
from Querys.caja import CajaQuerys
from Querys.mesa import MesaQuerys
from Models.cuenta_model import CuentaModel
from Models.pago_model import PagoModel
from Models.mesa_model import MesaModel
from Models.medio_pago_model import MedioPagoModel, MEDIOS_SISTEMA
from Models.sesion_mesa_model import SesionMesaModel
from Class.Caja import dia_actual, validar_monto
from Class.Mesa import check_zone_scope
from Class.Documento import Documento
from Class.Cupon import Cupon
from Utils.emision import cola_emision

MAX_PAGOS = 10


class Cuenta:
    """ Cobro de una mesa o de un pedido externo: cuenta, propina, descuento y pagos (doc 20, sección 3) """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = CajaQuerys(db, ctx)
        self.mesas = MesaQuerys(db, ctx)

    # Todo lo que está por cobrar: mesas y pedidos externos con sesión abierta
    def pending(self):
        result = []
        for sesion in self.querys.sesiones_abiertas():
            if not self.can_charge_table(self.db.get(MesaModel, sesion.mesa_id), raise_error=False):
                continue
            cuenta = self.querys.get_cuenta_by_sesion(sesion.id)
            subtotal = self.querys.subtotal_de_sesion(sesion.id)
            envio = self.querys.envio_de_sesion(sesion.id)
            mesa = self.db.get(MesaModel, sesion.mesa_id)
            ordenes = self.querys.ordenes_de_sesion(sesion.id)
            result.append({
                "sesion_mesa_id": sesion.id,
                "mesa_id": mesa.id,
                "mesa": mesa.nombre,
                "mesa_tipo": mesa.tipo,
                "cliente_nombre": next((o.cliente_nombre for o in ordenes if o.cliente_nombre), None),
                "ordenes": [f"#{o.numero:03d}" for o in ordenes],
                "abierta_en": sesion.abierta_en,
                "cuenta_id": cuenta.id if cuenta else None,
                "solicitada": bool(cuenta and cuenta.solicitada),
                "subtotal": subtotal,
                "envio": envio,
                "domicilio": envio > 0 or bool(self.querys.entrega_de_sesion(sesion.id)),
                "venta_directa": bool(ordenes) and all(o.canal == "pos" for o in ordenes),
                "total": (cuenta.total if cuenta else subtotal + envio),
                "pagado": cuenta.pagado if cuenta else 0,
            })
        # Primero las cuentas que alguien pidió
        result.sort(key=lambda r: (not r["solicitada"], r["abierta_en"]))
        return self.tools.output(200, "Cuentas por cobrar." if result else "No hay nada por cobrar.", result)

    # Abre (o trae) la cuenta de una mesa. La usa caja para cobrar y el mesero para la precuenta.
    def open(self, data: dict):
        cuenta, sesion = self.get_or_create(data)
        return self.tools.output(200, "Cuenta de la mesa.", self.format(cuenta, sesion))

    # El mesero pide la cuenta: caja la ve primero en su lista (doc 10, sección 2)
    def request(self, data: dict):
        cuenta, sesion = self.get_or_create(data)
        if not cuenta.solicitada:
            cuenta.solicitada = True
            cuenta.solicitada_en = now()
            self.db.commit()
            realtime.publish(self.ctx["restaurante_id"], channels_for(sesion.zona_id),
                             {"tipo": "cuenta.solicitada", "mesa_id": sesion.mesa_id, "cuenta_id": cuenta.id})
        return self.tools.output(200, "Cuenta pedida. Caja ya la tiene.", self.format(cuenta, sesion))

    def get(self, data: dict):
        cuenta = self.querys.get_own(CuentaModel, data["cuenta_id"], "cuenta")
        sesion = self.db.get(SesionMesaModel, cuenta.sesion_mesa_id)
        self.can_see(cuenta)
        if cuenta.estado == "abierta":
            self.refresh(cuenta)
            self.db.commit()
        return self.tools.output(200, "Detalle de la cuenta.", self.format(cuenta, sesion))

    # Propina y descuento manual (con permiso y motivo, RG-14)
    def adjust(self, data: dict):

        cuenta = self.querys.get_own(CuentaModel, data["cuenta_id"], "cuenta", lock=True)
        self.can_charge_table(self.db.get(MesaModel, cuenta.mesa_id))
        if cuenta.estado != "abierta":
            raise CustomException("La cuenta ya no está abierta.", 409)
        self.refresh(cuenta)

        if "descuento" in data:
            descuento = validar_monto(data.get("descuento") or 0, "descuento", permitir_cero=True)
            if descuento != cuenta.descuento:
                if "caja.descuento" not in self.ctx["permisos"]:
                    raise CustomException("Solo un administrador puede aplicar descuentos.", 403)
                motivo = clean_text(data.get("descuento_motivo"))
                if descuento and not motivo:
                    raise CustomException("Escribe el motivo del descuento.")
                if descuento > cuenta.subtotal:
                    raise CustomException("El descuento no puede ser mayor que el subtotal.")
                # Con cupones aplicados, el descuento manual va primero y el cupón descuenta sobre lo que queda
                self.querys.audit("descuento_aplicado", "cuenta", cuenta.id, antes={"descuento": cuenta.descuento},
                                  despues={"descuento": descuento}, motivo=motivo, commit=False)
                cuenta.descuento, cuenta.descuento_motivo = descuento, motivo

        if "propina" in data:
            cuenta.propina = validar_monto(data.get("propina") or 0, "propina", permitir_cero=True)

        self.refresh(cuenta)
        if cuenta.total < cuenta.pagado:
            raise CustomException("El nuevo total quedaría por debajo de lo ya pagado.")
        self.db.commit()
        return self.tools.output(200, "Cuenta actualizada.", self.format(cuenta))

    def pay(self, data: dict):
        """ Registra uno o varios pagos (pago mixto o cuenta dividida, doc 20 sección 4).
            Al cubrir el total, la cuenta queda pagada y la mesa se libera. """

        clave = str(data["clave_idempotencia"]).strip()
        if self.querys.pagos_por_clave(clave):
            cuenta = self.querys.get_own(CuentaModel, data["cuenta_id"], "cuenta")
            return self.tools.output(200, "Este pago ya estaba registrado.", self.format(cuenta))

        cuenta = self.querys.get_own(CuentaModel, data["cuenta_id"], "cuenta", lock=True)
        self.can_charge_table(self.db.get(MesaModel, cuenta.mesa_id))
        if cuenta.estado != "abierta":
            raise CustomException("La cuenta ya no está abierta.", 409)
        if self.querys.jornada_cerrada(dia_actual(self.ctx)):
            raise CustomException("La jornada ya se cerró: no se reciben más cobros hoy.", 409)
        caja = self.querys.get_caja()
        turno = self.querys.get_turno_abierto(caja.id)
        if not turno:
            raise CustomException("No hay un turno de caja abierto. Ábrelo antes de cobrar.", 409)

        self.refresh(cuenta)
        if data.get("factura"):
            Documento(self.db, self.ctx).clean_receptor(data["factura"])
        pagos = data.get("pagos") or []
        if not pagos and cuenta.total > 0:
            raise CustomException("Indica cómo se paga.")
        if len(pagos) > MAX_PAGOS:
            raise CustomException(f"Se pueden registrar máximo {MAX_PAGOS} pagos a la vez.")

        medios = {m.id: m for m in self.querys.medios() if m.tipo not in MEDIOS_SISTEMA}
        filas, abonado = [], 0
        for posicion, pago in enumerate(pagos):
            medio = medios.get(int(pago["medio_pago_id"]))
            if not medio:
                raise CustomException("El medio de pago no está disponible.")
            monto = validar_monto(pago["monto"])
            fila = {
                "cuenta_id": cuenta.id, "turno_caja_id": turno.id, "medio_pago_id": medio.id, "monto": monto,
                "usuario_id": self.ctx["usuario_id"], "clave_idempotencia": f"{clave}:{posicion}",
                "referencia": clean_text(pago.get("referencia")),
            }
            if medio.tipo == "efectivo":
                recibido = validar_monto(pago.get("recibido") or monto, "valor recibido")
                if recibido < monto:
                    raise CustomException("El efectivo recibido es menor que el valor a pagar.")
                fila["recibido"], fila["cambio"] = recibido, recibido - monto
            if medio.pide_referencia and not fila["referencia"]:
                raise CustomException(f"Escribe la referencia del pago con {medio.nombre}.")
            filas.append(fila)
            abonado += monto

        # La suma de pagos no supera el total más la propina (RN-CAJ-04)
        saldo = cuenta.total - cuenta.pagado
        if abonado > saldo:
            raise CustomException(f"Los pagos ({self.tools.format_number(abonado)}) superan el saldo ({self.tools.format_number(saldo)}).")

        documento, aviso = None, None
        try:
            for fila in filas:
                self.db.add(PagoModel(self.querys._with_tenant(PagoModel, fila)))
            cuenta.pagado += abonado
            pagada = cuenta.pagado == cuenta.total
            if pagada:
                self.settle(cuenta, turno)
                # Documento de venta en la misma transacción: si el cobro falla, el número no se consume
                documento, aviso = Documento(self.db, self.ctx).generate_for_account(cuenta, data.get("factura"), caja.id)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            cuenta = self.querys.get_own(CuentaModel, data["cuenta_id"], "cuenta")
            return self.tools.output(200, "Este pago ya estaba registrado.", self.format(cuenta))

        self.notify(cuenta, "cuenta.pagada" if pagada else "cuenta.abonada")
        if documento:
            cola_emision.despertar()
        cambio = sum(f.get("cambio") or 0 for f in filas)
        msg = "Cuenta pagada. La mesa quedó libre." if pagada else f"Abono registrado. Falta {self.tools.format_number(cuenta.total - cuenta.pagado)}."
        if cambio:
            msg += f" Cambio: {self.tools.format_number(cambio)}."
        if aviso:
            msg += f" {aviso}"
        return self.tools.output(200, msg, self.format(cuenta))

    # Un pago no se edita: se anula con motivo (RN-CAJ-05)
    def void_payment(self, data: dict):

        pago = self.querys.get_own(PagoModel, data["pago_id"], "pago", lock=True)
        cuenta = self.querys.get_own(CuentaModel, pago.cuenta_id, "cuenta", lock=True)
        if cuenta.estado != "abierta":
            raise CustomException("La cuenta ya está pagada: anula la cuenta completa.", 409)
        if pago.estado != "aplicado":
            raise CustomException("El pago ya estaba anulado.", 409)

        motivo = clean_text(data["motivo"])
        pago.estado, pago.anulado_en, pago.anulado_por, pago.anulado_motivo = "anulado", now(), self.ctx["usuario_id"], motivo
        cuenta.pagado -= pago.monto
        self.querys.audit("pago_anulado", "pago", pago.id, antes={"monto": pago.monto}, motivo=motivo, commit=False)
        self.db.commit()
        return self.tools.output(200, "Pago anulado.", self.format(cuenta))

    # Anular una cuenta ya cobrada: solo administrador, con motivo (doc 20, sección 6)
    def void(self, data: dict):

        cuenta = self.querys.get_own(CuentaModel, data["cuenta_id"], "cuenta", lock=True)
        if cuenta.estado == "anulada":
            raise CustomException("La cuenta ya estaba anulada.", 409)
        motivo = clean_text(data["motivo"])
        if cuenta.estado == "pagada" and cuenta.jornada and self.querys.jornada_cerrada(cuenta.jornada):
            raise CustomException("La jornada de esa cuenta ya se cerró; sus totales no cambian (RN-REP-02).", 409)

        for pago in self.querys.pagos_de(cuenta.id):
            if pago.estado == "aplicado":
                pago.estado, pago.anulado_en, pago.anulado_por, pago.anulado_motivo = "anulado", now(), self.ctx["usuario_id"], motivo
        antes = cuenta.estado
        cuenta.estado, cuenta.anulada_en, cuenta.anulada_por, cuenta.anulada_motivo = "anulada", now(), self.ctx["usuario_id"], motivo
        if not cuenta.jornada:
            cuenta.jornada = dia_actual(self.ctx)
        sesion = self.db.get(SesionMesaModel, cuenta.sesion_mesa_id)
        if sesion.estado == "abierta":
            self.mesas.close_session(sesion, self.ctx["usuario_id"])
        self.querys.audit("cuenta_anulada", "cuenta", cuenta.id, antes={"estado": antes, "total": cuenta.total},
                          motivo=motivo, commit=False)
        Cupon(self.db, self.ctx).on_void(cuenta, motivo)
        notas = Documento(self.db, self.ctx).void_for_account(cuenta, motivo)
        self.db.commit()
        if notas:
            cola_emision.despertar()

        self.notify(cuenta, "cuenta.anulada")
        mensaje = "Cuenta anulada."
        # Una propina ya liquidada no se toca: se corrige con un ajuste en la próxima liquidación (RN-PRP-03)
        if cuenta.liquidacion_propina_id and cuenta.propina:
            mensaje += f" Su propina ({self.tools.format_number(cuenta.propina)}) ya se liquidó: corrígela con un ajuste."
        return self.tools.output(200, mensaje, self.format(cuenta))

    # Cuentas cobradas o anuladas de la jornada
    def list(self, data: dict):
        dia = dia_actual(self.ctx)
        cuentas = [self.format(c, resumen=True) for c in self.querys.cuentas_de_jornada(dia, data.get("estado"))]
        return self.tools.output(200, "Cuentas de la jornada." if cuentas else "Aún no hay cuentas cobradas hoy.", cuentas)

    def get_or_create(self, data: dict):
        if data.get("sesion_mesa_id"):
            sesion = self.querys.get_own(SesionMesaModel, data["sesion_mesa_id"], "sesión")
        elif data.get("mesa_id"):
            mesa = self.querys.get_own(MesaModel, data["mesa_id"], "mesa")
            if mesa.tipo == "externa":
                raise CustomException("Indica cuál pedido externo se cobra.")
            sesion = self.mesas.get_open_session(mesa.id)
            if not sesion:
                raise CustomException("La mesa no tiene nada por cobrar.", 409)
        else:
            raise CustomException("Indica la mesa o el pedido.")

        mesa = self.db.get(MesaModel, sesion.mesa_id)
        if "caja.cobrar" not in self.ctx["permisos"] and "caja.cobrar_externas" not in self.ctx["permisos"]:
            check_zone_scope(self.ctx, mesa.zona_id)
        else:
            self.can_charge_table(mesa)
        if sesion.estado != "abierta":
            raise CustomException("Esa mesa ya se cerró.", 409)

        cuenta = self.querys.get_cuenta_by_sesion(sesion.id, lock=True)
        if not cuenta:
            try:
                self.querys.insert_data(CuentaModel, {"sesion_mesa_id": sesion.id, "mesa_id": mesa.id,
                                                      "zona_id": mesa.zona_id}, commit=False)
            except CustomException:
                self.db.rollback()
            cuenta = self.querys.get_cuenta_by_sesion(sesion.id, lock=True)
        self.refresh(cuenta)
        self.db.commit()
        return cuenta, sesion

    # Mientras está abierta, la cuenta sigue lo que se pide en la mesa
    def refresh(self, cuenta):
        if cuenta.estado != "abierta":
            return
        cuenta.subtotal = self.querys.subtotal_de_sesion(cuenta.sesion_mesa_id)
        cuenta.envio = self.querys.envio_de_sesion(cuenta.sesion_mesa_id)
        cuenta.descuento = min(cuenta.descuento, cuenta.subtotal)
        Cupon(self.db, self.ctx).refresh_account(cuenta)
        self.recalc(cuenta)

    def recalc(self, cuenta):
        cuenta.total = (cuenta.subtotal - cuenta.descuento - cuenta.descuento_cupon + cuenta.envio - cuenta.descuento_envio
                        + cuenta.propina)

    def settle(self, cuenta, turno):
        cuenta.estado = "pagada"
        cuenta.numero = self.querys.next_cuenta_number()
        cuenta.jornada = dia_actual(self.ctx)
        cuenta.pagada_en = now()
        cuenta.turno_caja_id = turno.id if turno else None
        cuenta.cobrada_por = self.ctx["usuario_id"]
        # Redime los cupones aplicados y emite el de la próxima visita (doc 25A)
        Cupon(self.db, self.ctx).on_settle(cuenta)
        sesion = self.db.get(SesionMesaModel, cuenta.sesion_mesa_id)
        if sesion.estado == "abierta":
            self.mesas.close_session(sesion, self.ctx["usuario_id"])

    # El encargado de externos solo cobra pedidos externos (doc 29)
    def can_charge_table(self, mesa, raise_error=True):
        permisos = self.ctx["permisos"]
        if "caja.cobrar" in permisos:
            return True
        if "caja.cobrar_externas" in permisos and mesa.tipo == "externa":
            return True
        if raise_error:
            raise CustomException("Solo puedes cobrar pedidos externos.", 403)
        return False

    def can_see(self, cuenta):
        if not {"caja.ver", "caja.cobrar", "caja.cobrar_externas"} & self.ctx["permisos"]:
            mesa = self.db.get(MesaModel, cuenta.mesa_id)
            check_zone_scope(self.ctx, mesa.zona_id)

    def format(self, cuenta, sesion=None, resumen=False):
        restaurante = self.querys.restaurante_actual()
        data = self.querys.format_cuenta(cuenta, sesion, restaurante.propina_sugerida)
        data["restaurante"] = {"nombre": restaurante.nombre, "direccion": restaurante.direccion,
                               "telefono": restaurante.telefono}
        data["pagada_local"] = self.querys.local_time(cuenta.pagada_en) if cuenta.pagada_en else None
        data.update(Cupon(self.db, self.ctx).for_account(cuenta))
        # Documentos de venta de la cuenta (el vigente primero) para la tirilla y la caja
        documentos = Documento(self.db, self.ctx)
        data["documentos"] = [documentos.format(d, resumen=resumen)
                              for d in reversed(documentos.querys.documentos_de_cuenta(cuenta.id))]
        if resumen:
            data.pop("lineas")
        return data

    def notify(self, cuenta, tipo: str):
        realtime.publish(self.ctx["restaurante_id"], channels_for(cuenta.zona_id),
                         {"tipo": tipo, "cuenta_id": cuenta.id, "mesa_id": cuenta.mesa_id})
