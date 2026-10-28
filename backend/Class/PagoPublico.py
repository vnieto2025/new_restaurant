from Utils.tools import Tools, CustomException
from Utils.limiter import limiter
from Utils.estados import PENDIENTE
from Utils.contexto import modulos_activos
from Utils.cifrado import descifrar
from Utils.pasarelas import PasarelaSimulada
from Querys.publico import PublicoQuerys
from Querys.orden import OrdenQuerys
from Querys.mesa import MesaQuerys
from Models.intento_pago_model import IntentoPagoModel
from Models.cuenta_model import CuentaModel
from Models.sesion_mesa_model import SesionMesaModel
from Models.restaurante_model import RestauranteModel
from Class.PagoLinea import PagoLinea, ESTADOS_TEXTO, registrar_webhook
from Class.Cupon import Cupon

CONSULTAS_POR_IP = 120
INTENTOS_POR_IP = 10
VENTANA = 600
# Pocos intentos de código: adivinar cupones no debe ser práctico
CUPONES_POR_IP = 8


class PagoPublico:
    """ Lo que ve el cliente para pagar desde su celular (doc 20A): con el QR de su mesa o con el enlace
        de su pedido. Sin sesión: el contexto sale del token, como en la carta digital (doc 10A). """

    def __init__(self, db, ip: str = None):
        self.db = db
        self.ip = ip or "sin-ip"
        self.tools = Tools()

    def info(self, data: dict):
        limiter.check(f"publico:{self.ip}", CONSULTAS_POR_IP, 60, "Demasiadas consultas. Espera un momento.")
        return self.tools.output(200, "Cuenta.", self.account_data(data))

    def account_data(self, data: dict):
        sesion, restaurante, pagos = self.resolve(data)
        config = pagos.config()
        disponible = "pagos_linea" in pagos.ctx["modulos"] and bool(config and config.activo)
        cuenta = None
        if sesion.estado == "abierta":
            cuenta = pagos.account_for(sesion)
            self.db.commit()
        else:
            cuenta = pagos.querys.get_cuenta_by_sesion(sesion.id)
        detalle = pagos.querys.format_cuenta(cuenta, sesion, restaurante.propina_sugerida) if cuenta else None
        cupones = Cupon(self.db, pagos.ctx).for_account(cuenta)["cupones"] if cuenta else []
        ultimo = pagos.querys.scoped(IntentoPagoModel).filter(IntentoPagoModel.cuenta_id == cuenta.id).order_by(
            IntentoPagoModel.id.desc()).first() if cuenta else None
        por_confirmar = self.awaiting_confirmation(data)
        return {
            "restaurante": restaurante.nombre,
            "disponible": disponible and bool(cuenta) and cuenta.estado == "abierta" and not por_confirmar,
            "mensaje": "El restaurante aún no confirma tu pedido. Podrás pagar cuando lo confirme." if por_confirmar
            else None if disponible else "Este restaurante no recibe pagos en línea. Paga en caja.",
            "estado": cuenta.estado if cuenta else "sin_cuenta",
            "titulo": (detalle["cliente_nombre"] if detalle and detalle["mesa_tipo"] == "externa" else detalle["mesa"]) if detalle else None,
            "lineas": [{"nombre": l["nombre"], "cantidad": l["cantidad"], "total": l["total"],
                        "modificadores": [m["nombre"] for m in l["modificadores"]]} for l in detalle["lineas"]] if detalle else [],
            "subtotal": cuenta.subtotal if cuenta else 0, "descuento": cuenta.descuento if cuenta else 0,
            "cupones": [{"codigo": c["codigo"], "nombre": c["nombre"], "valor": c["valor"], "nota": c["nota"]} for c in cupones],
            "acepta_cupones": "fidelizacion" in pagos.ctx["modulos"],
            "envio": cuenta.envio if cuenta else 0, "propina": cuenta.propina if cuenta else 0,
            "total": cuenta.total if cuenta else 0, "pagado": cuenta.pagado if cuenta else 0,
            "saldo": (cuenta.total - cuenta.pagado) if cuenta else 0,
            "permitir_propina": bool(config and config.permitir_propina),
            "propina_porcentaje": restaurante.propina_sugerida,
            "ultimo_pago": {"pago": ultimo.token, "estado": ultimo.estado, "estado_texto": ESTADOS_TEXTO[ultimo.estado]}
            if ultimo else None,
        }

    def apply_coupon(self, data: dict):
        """ El cliente escribe su código antes de pagar. La validación es la misma de caja (RN-CUP-05). """
        limiter.check(f"publico:cupon:{self.ip}", CUPONES_POR_IP, VENTANA,
                      "Se probaron demasiados códigos desde este dispositivo. Pídele el cupón a caja.")
        sesion, _, pagos = self.resolve(data)
        if "fidelizacion" not in pagos.ctx["modulos"]:
            raise CustomException("Este restaurante no recibe cupones en línea. Muéstralo en caja.", 409)
        if sesion.estado != "abierta":
            raise CustomException("Esta cuenta ya no tiene nada por pagar.", 409)
        cuenta = pagos.account_for(sesion, lock=True)
        cupon = Cupon(self.db, pagos.ctx).apply_code(cuenta, data["codigo"])
        self.db.commit()
        return self.tools.output(200, f"Cupón {cupon.codigo} aplicado.", self.account_data(data))

    def create(self, data: dict):
        limiter.check(f"publico:pago:{self.ip}", INTENTOS_POR_IP, VENTANA,
                      "Se intentaron demasiados pagos desde este dispositivo. Paga en caja o espera unos minutos.")
        sesion, _, pagos = self.resolve(data)
        if self.awaiting_confirmation(data):
            raise CustomException("El restaurante aún no confirma tu pedido. Podrás pagar cuando lo confirme.", 409)
        propina = int(data.get("propina") or 0)
        intento = pagos.create_attempt(sesion, propina, str(data["clave_idempotencia"]).strip(),
                                       "qr" if data.get("token") else "enlace")
        self.db.commit()
        return self.tools.output(201, "Pago iniciado. Termina en la página de la pasarela.",
                                 {"pago": intento.token, "url": intento.url_pago, "monto": intento.monto})

    def status(self, data: dict):
        limiter.check(f"publico:{self.ip}", CONSULTAS_POR_IP, 60, "Demasiadas consultas. Espera un momento.")
        intento, pagos = self.attempt_by(IntentoPagoModel.token == data["pago"])
        pagos.expire_old()
        self.db.commit()
        self.db.refresh(intento)
        cuenta = self.db.get(CuentaModel, intento.cuenta_id)
        ordenes = pagos.querys.ordenes_de_sesion(cuenta.sesion_mesa_id)
        return self.tools.output(200, "Estado del pago.", {
            "estado": intento.estado, "estado_texto": ESTADOS_TEXTO[intento.estado], "monto": intento.monto,
            "propina": intento.propina, "cuenta_pagada": cuenta.estado == "pagada", "excedente": intento.excedente,
            "restaurante": pagos.querys.restaurante_actual().nombre,
            "seguimiento": ordenes[-1].token_seguimiento if ordenes else None,
        })

    # ---- Pasarela simulada: su "página segura" de pruebas ----

    def simulated_view(self, data: dict):
        intento, pagos = self.simulated(data["referencia"])
        return self.tools.output(200, "Pago de prueba.", {
            "referencia": intento.referencia, "monto": intento.monto, "estado": intento.estado,
            "restaurante": pagos.querys.restaurante_actual().nombre, "pago": intento.token,
        })

    def simulated_answer(self, data: dict):
        """ El cliente decide en la página de pruebas; la "pasarela" avisa al sistema con su webhook firmado """
        intento, pagos = self.simulated(data["referencia"])
        if intento.estado == "pendiente":
            config = pagos.config()
            pasarela = PasarelaSimulada(descifrar(config.credenciales), config.ambiente)
            cuerpo, cabeceras = pasarela.aviso(intento.referencia, intento.monto, data["decision"] == "aprobar")
            token = intento.token
            registrar_webhook(self.db, "simulada", cuerpo, cabeceras)
            return self.tools.output(200, "Respuesta enviada.", {"pago": token})
        return self.tools.output(200, "Este pago ya tiene respuesta.", {"pago": intento.token})

    # ---- Apoyo ----

    def resolve(self, data: dict):
        """ Sesión a pagar: la mesa del QR (mesa normal) o el pedido del enlace de seguimiento """
        if data.get("seguimiento"):
            orden = OrdenQuerys(self.db).get_orden_by_seguimiento(data["seguimiento"])
            if not orden:
                raise CustomException("No encontramos este pedido.", 404)
            sesion = self.db.get(SesionMesaModel, orden.sesion_mesa_id)
            restaurante = self.db.get(RestauranteModel, orden.restaurante_id)
        elif data.get("token"):
            contexto = PublicoQuerys(self.db).resolve_token(data["token"])
            if not contexto:
                raise CustomException("Este código QR no está disponible.", 404)
            if contexto["mesa"].tipo == "externa":
                raise CustomException("Para pagar un pedido para llevar usa el enlace de seguimiento de tu pedido.", 409)
            restaurante = contexto["restaurante"]
            sesion = MesaQuerys(self.db, self.ctx_of(restaurante)).get_open_session(contexto["mesa"].id)
            if not sesion:
                raise CustomException("Esta mesa no tiene una cuenta abierta.", 404)
        else:
            raise CustomException("Indica la mesa o el pedido.")
        return sesion, restaurante, PagoLinea(self.db, self.ctx_of(restaurante))

    def awaiting_confirmation(self, data: dict):
        """ Un pedido por enlace de seguimiento que espera confirmación no se cobra todavía """
        if not data.get("seguimiento"):
            return False
        orden = OrdenQuerys(self.db).get_orden_by_seguimiento(data["seguimiento"])
        return bool(orden) and any(i.estado == PENDIENTE for i in OrdenQuerys(
            self.db, {"empresa_id": orden.empresa_id, "restaurante_id": orden.restaurante_id}).items_of(orden.id))

    def attempt_by(self, condicion):
        intento = self.db.query(IntentoPagoModel).filter(condicion).first()
        if not intento:
            raise CustomException("No encontramos este pago.", 404)
        restaurante = self.db.get(RestauranteModel, intento.restaurante_id)
        return intento, PagoLinea(self.db, self.ctx_of(restaurante))

    def simulated(self, referencia):
        intento, pagos = self.attempt_by(IntentoPagoModel.referencia == referencia)
        config = pagos.config()
        if intento.pasarela != "simulada" or not config or config.ambiente != "pruebas":
            raise CustomException("Esta página de pruebas no está disponible.", 404)
        return intento, pagos

    def ctx_of(self, restaurante):
        modulos, _ = modulos_activos(self.db, restaurante)
        return {"empresa_id": restaurante.empresa_id, "restaurante_id": restaurante.id, "usuario_id": None,
                "zona_horaria": restaurante.zona_horaria, "hora_inicio_jornada": restaurante.hora_inicio_jornada,
                "publico": True, "permisos": set(), "modulos": set(modulos), "ip": self.ip}
