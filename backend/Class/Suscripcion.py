import calendar
from datetime import date, timedelta
from Utils.tools import Tools, CustomException, clean_text, jornada, fecha_local
from Utils.catalogo import PLANES, COMPLEMENTOS, plan_de
from Querys.restaurante import RestauranteQuerys
from Models.contrato_model import ContratoModel
from Models.pago_suscripcion_model import PagoSuscripcionModel
from Models.restaurante_model import RestauranteModel

# Días de mora antes de sugerir la suspensión: suspender nunca es automático ni sin aviso (doc 02A, sección 3)
DIAS_GRACIA = 10
DIAS_AVISO = 5
MAX_MESES = 12


def sumar_meses(fecha: date, meses: int) -> date:
    mes = fecha.month - 1 + meses
    anio, mes = fecha.year + mes // 12, mes % 12 + 1
    return fecha.replace(year=anio, month=mes, day=min(fecha.day, calendar.monthrange(anio, mes)[1]))


def estado_cuenta(contrato, hoy: date) -> dict:
    """ Situación comercial del contrato (doc 42, sección 5): prueba, al día, por vencer, en mora o cancelado """
    if contrato.estado == "cancelado":
        return {"estado": "cancelado", "texto": "Contrato cancelado"}
    if contrato.estado == "prueba":
        dias = (contrato.fecha_fin - hoy).days if contrato.fecha_fin else None
        if dias is not None and dias < 0:
            return {"estado": "prueba_vencida", "texto": "La prueba terminó", "dias": dias}
        return {"estado": "prueba", "texto": "En prueba" + (f": quedan {dias} días" if dias is not None else ""), "dias": dias}
    if not contrato.proximo_vencimiento:
        return {"estado": "sin_cobro", "texto": "Sin cobro configurado"}
    dias = (contrato.proximo_vencimiento - hoy).days
    if dias < 0:
        mora = -dias
        return {"estado": "en_mora", "texto": f"En mora hace {mora} días", "dias": dias,
                "suspender_sugerido": mora > DIAS_GRACIA and contrato.estado != "suspendido"}
    if dias <= DIAS_AVISO:
        return {"estado": "por_vencer", "texto": "Vence hoy" if dias == 0 else f"Vence en {dias} días", "dias": dias}
    return {"estado": "al_dia", "texto": "Al día", "dias": dias}


class Suscripcion:
    """ Planes y cobro del servicio (doc 42). El proveedor registra los pagos a mano; el restaurante ve su plan,
        sus módulos y el estado de su cuenta. """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = RestauranteQuerys(db, ctx)

    # ---- Consola de plataforma ----

    def plans(self):
        modulos = {m.codigo: m for m in self.querys.get_modulos()}
        return self.tools.output(200, "Planes.", {
            "planes": [{**p, "modulos_nombres": [modulos[c].nombre for c in p["modulos"] if c in modulos]} for p in PLANES],
            "complementos": [{"codigo": c, "nombre": modulos[c].nombre, "depende_de": modulos[c].depende_de}
                             for c in COMPLEMENTOS if c in modulos],
            "dias_gracia": DIAS_GRACIA,
        })

    def payments(self, data: dict):
        restaurante, contrato = self.contract_of(data["restaurante_id"])
        return self.tools.output(200, "Pagos del servicio.", {
            "restaurante": restaurante.nombre, "suscripcion": self.account(restaurante, contrato),
            "pagos": [self.format_payment(p) for p in self.list_payments(contrato.id)],
        })

    def register_payment(self, data: dict):
        """ Registra un pago y corre el vencimiento por los meses pagados """
        restaurante, contrato = self.contract_of(data["restaurante_id"], lock=True)
        if contrato.estado == "cancelado":
            raise CustomException("El contrato está cancelado.", 409)
        valor = int(data["valor"])
        if valor <= 0:
            raise CustomException("El valor del pago no es válido.")
        meses = int(data.get("meses") or 1)
        if not 1 <= meses <= MAX_MESES:
            raise CustomException(f"Se pueden pagar de 1 a {MAX_MESES} meses.")
        hoy = self.today(restaurante)
        fecha = date.fromisoformat(data["fecha"]) if data.get("fecha") else hoy
        if fecha > fecha_local(restaurante.zona_horaria):
            raise CustomException("La fecha del pago no puede ser futura.")
        desde = contrato.proximo_vencimiento or fecha
        hasta = sumar_meses(desde, meses)
        self.querys.insert_data(PagoSuscripcionModel, {
            "empresa_id": restaurante.empresa_id, "restaurante_id": restaurante.id, "contrato_id": contrato.id,
            "valor": valor, "fecha": fecha, "periodo_desde": desde, "periodo_hasta": hasta - timedelta(days=1),
            "medio": data["medio"], "referencia": clean_text(data.get("referencia")), "factura": clean_text(data.get("factura")),
            "registrado_por": self.ctx.get("usuario_id"),
        }, commit=False)
        antes = str(contrato.proximo_vencimiento)
        contrato.proximo_vencimiento = hasta
        self.querys.audit("pago_suscripcion", "contrato", contrato.id, antes={"proximo_vencimiento": antes},
                          despues={"proximo_vencimiento": str(hasta), "valor": valor, "meses": meses}, commit=False)
        self.db.commit()
        mensaje = f"Pago registrado. Próximo vencimiento: {hasta.strftime('%d/%m/%Y')}."
        if contrato.estado in ("suspendido", "prueba"):
            mensaje += " El contrato sigue " + ("suspendido" if contrato.estado == "suspendido" else "en prueba") + \
                       ": cámbialo a activo si corresponde."
        return self.tools.output(201, mensaje, {"suscripcion": self.account(restaurante, contrato),
                                                "pagos": [self.format_payment(p) for p in self.list_payments(contrato.id)]})

    # ---- Lo que ve el restaurante ----

    def my_plan(self):
        restaurante = self.db.get(RestauranteModel, self.ctx["restaurante_id"])
        contrato = self.querys.get_contrato(restaurante.id)
        if not contrato:
            raise CustomException("El restaurante no tiene contrato.", 404)
        modulos = {m.codigo: m for m in self.querys.get_modulos()}
        contratados = self.querys.get_modulos_contrato(contrato.id)
        return self.tools.output(200, "Tu plan.", {
            **self.account_summary(contrato, contratados, restaurante),
            "modulos": [{"codigo": c, "nombre": modulos[c].nombre} for c in contratados if c in modulos],
            "complementos_disponibles": [
                {"codigo": c, "nombre": modulos[c].nombre} for c in COMPLEMENTOS
                if c in modulos and c not in contratados
                and all(d in contratados for d in (modulos[c].depende_de or "").split(",") if d)],
            "pagos": [self.format_payment(p) for p in self.list_payments(contrato.id, limite=12)],
        })

    # ---- Apoyo ----

    def account(self, restaurante, contrato):
        return self.account_summary(contrato, self.querys.get_modulos_contrato(contrato.id), restaurante)

    def account_summary(self, contrato, contratados, restaurante):
        codigo = plan_de(contratados)
        plan = next((p for p in PLANES if p["codigo"] == codigo), None)
        return {
            "plan": codigo, "plan_nombre": plan["nombre"] if plan else "Personalizado",
            "complementos": [c for c in contratados if c in COMPLEMENTOS],
            "estado_contrato": contrato.estado, "fecha_inicio": contrato.fecha_inicio, "fecha_fin": contrato.fecha_fin,
            "mensualidad": contrato.mensualidad, "proximo_vencimiento": contrato.proximo_vencimiento,
            "cuenta": estado_cuenta(contrato, self.today(restaurante)),
        }

    def contract_of(self, restaurante_id, lock=False):
        restaurante = self.querys.get_restaurante(int(restaurante_id))
        query = self.db.query(ContratoModel).filter(ContratoModel.restaurante_id == restaurante.id)
        contrato = (query.with_for_update() if lock else query).first()
        if not contrato:
            raise CustomException("El restaurante no tiene contrato.", 404)
        return restaurante, contrato

    def list_payments(self, contrato_id, limite=50):
        return self.db.query(PagoSuscripcionModel).filter(PagoSuscripcionModel.contrato_id == contrato_id).order_by(
            PagoSuscripcionModel.fecha.desc(), PagoSuscripcionModel.id.desc()).limit(limite).all()

    def format_payment(self, pago):
        return {"id": pago.id, "valor": pago.valor, "fecha": pago.fecha, "periodo_desde": pago.periodo_desde,
                "periodo_hasta": pago.periodo_hasta, "medio": pago.medio, "referencia": pago.referencia,
                "factura": pago.factura}

    def today(self, restaurante):
        return jornada(tz_name=restaurante.zona_horaria, inicio=restaurante.hora_inicio_jornada)
