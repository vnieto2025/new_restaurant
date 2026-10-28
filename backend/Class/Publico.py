import re
from datetime import timedelta
from Utils.tools import Tools, CustomException, now
from Utils.limiter import limiter
from Utils.contexto import modulos_activos
from Utils.estados import ETIQUETAS, CANCELADO
from Querys.publico import PublicoQuerys
from Querys.carta import CartaQuerys
from Querys.horario import HorarioQuerys
from Querys.orden import OrdenQuerys, ESTADOS_ORDEN
from Models.mesa_model import MesaModel
from Models.restaurante_model import RestauranteModel
from Models.pago_linea_config_model import PagoLineaConfigModel
from Models.domicilio_web_model import DomicilioWebModel
from Models.entrega_model import EntregaModel
from Querys.entrega import EntregaQuerys
from Class.Orden import Orden

# Límites de uso de lo público (doc 10A, sección 4): por token del QR y por IP
ORDENES_POR_TOKEN = 6
ORDENES_POR_IP = 15
VENTANA_ORDENES = 600
CONSULTAS_POR_IP = 120
VENTANA_CONSULTAS = 60
# Domicilio por la web: por celular y un tope general del enlace (doc 17A, sección 5)
ORDENES_POR_TELEFONO = 3
ORDENES_POR_ENLACE = 60
VENTANA_TELEFONO = 1800
FORMAS_PAGO = ["contra_entrega", "en_linea"]

AVISO_DATOS = ("{restaurante} usará tu nombre y teléfono para gestionar este pedido y avisarte cuando esté listo. "
               "Puedes pedir que los actualicemos o eliminemos cuando quieras.")

NO_DISPONIBLE = "Este código QR no está disponible. Pide ayuda al personal del restaurante."
SIN_DOMICILIOS = "Este restaurante no está recibiendo domicilios por la web en este momento."


def telefono_valido(telefono):
    """ Celular con 7 a 15 dígitos; se aceptan espacios, guiones, paréntesis y el + del indicativo """
    texto = (telefono or "").strip()
    if not re.fullmatch(r"\+?[\d\s().-]+", texto):
        return None
    digitos = re.sub(r"\D", "", texto)
    return digitos if 7 <= len(digitos) <= 15 else None


class Publico:

    def __init__(self, db, ip: str = None, dispositivo: str = None):
        self.db = db
        self.ip = ip or "sin-ip"
        self.dispositivo = (dispositivo or "")[:250] or None
        self.tools = Tools()
        self.querys = PublicoQuerys(db)

    # Lo que ve el cliente al escanear: restaurante, zona, mesa y carta (doc 10A, sección 8)
    def qr(self, data: dict):

        limiter.check(f"publico:{self.ip}", CONSULTAS_POR_IP, VENTANA_CONSULTAS,
                      "Demasiadas consultas. Espera un momento.")
        contexto = self.resolve(data["token"])
        restaurante, zona, mesa = contexto["restaurante"], contexto["zona"], contexto["mesa"]

        motivo = self.unavailable_reason(contexto)
        es_domicilio = contexto["qr"].tipo == "domicilio"
        web = self.web_config(restaurante) if es_domicilio else None
        result = {
            "restaurante": restaurante.nombre,
            "zona": zona.nombre,
            "mesa": mesa.nombre,
            "tipo": contexto["qr"].tipo,
            "pide_nombre": mesa.tipo == "externa",
            "con_aprobacion": (web.aprobacion if web else True) if es_domicilio else zona.modo_qr == "aprobacion",
            "moneda": restaurante.moneda,
            # Aviso de tratamiento de datos visible antes de pedir nombre o teléfono (RN-PRI-01)
            "aviso_datos": restaurante.aviso_datos or AVISO_DATOS.format(restaurante=restaurante.nombre),
            "politica_url": restaurante.politica_url,
            "disponible": motivo is None,
            "mensaje": motivo,
            # La cuenta de una mesa se puede pagar desde el celular (doc 20A)
            "pago_en_linea": (es_domicilio or mesa.tipo != "externa") and self.online_payments(restaurante),
            "categorias": [],
            "domicilio": None,
        }
        if motivo is None:
            ctx = self.public_ctx(contexto)
            result["categorias"] = CartaQuerys(self.db, ctx).menu(HorarioQuerys(self.db, ctx).current_menu(zona))
            if es_domicilio:
                # Zonas con su tarifa y pedido mínimo: el cliente elige la suya (doc 15B, sección 1)
                result["domicilio"] = {"mensaje": web.mensaje, "zonas": [{
                    "id": z.id, "nombre": z.nombre, "barrios": z.barrios, "tarifa": z.tarifa, "pedido_minimo": z.pedido_minimo,
                } for z in EntregaQuerys(self.db, ctx).zonas()]}

        return self.tools.output(200, "Carta disponible." if motivo is None else motivo, result)

    # El cliente envía su orden desde el celular, sin registrarse (doc 17, flujo B)
    def create_order(self, data: dict):

        token = data["token"]
        limiter.check(f"publico:orden:ip:{self.ip}", ORDENES_POR_IP, VENTANA_ORDENES,
                      "Se enviaron demasiadas órdenes desde este dispositivo. Pide ayuda al personal.")
        contexto = self.resolve(token)
        # El enlace de domicilios lo comparten todos los clientes: su tope es un freno general, no por mesa
        if contexto["qr"].tipo == "domicilio":
            limiter.check(f"publico:orden:token:{token}", ORDENES_POR_ENLACE, VENTANA_ORDENES,
                          "El restaurante está recibiendo muchos pedidos. Intenta en unos minutos.")
        else:
            limiter.check(f"publico:orden:token:{token}", ORDENES_POR_TOKEN, VENTANA_ORDENES,
                          "Esta mesa envió demasiadas órdenes seguidas. Pide ayuda al personal.")
        motivo = self.unavailable_reason(contexto)
        if motivo:
            raise CustomException(motivo, 409)

        ctx = self.public_ctx(contexto)
        orden_class = Orden(self.db, ctx)
        mesa = orden_class.querys.get_own(MesaModel, contexto["mesa"].id, "mesa", lock=True)
        canal = "qr_rapido" if mesa.tipo == "externa" else "qr_mesa"
        entrega, aprobacion = None, None
        if contexto["qr"].tipo == "domicilio":
            canal = "domicilio"
            entrega, aprobacion = self.delivery_data(data, ctx)

        orden, creada = orden_class.create_order(
            mesa=mesa,
            canal=canal,
            items=data["items"],
            clave=data["clave_idempotencia"],
            notas=data.get("notas"),
            cliente_nombre=data.get("cliente_nombre"),
            cliente_telefono=entrega["telefono"] if entrega else data.get("cliente_telefono"),
            acepta_datos=data.get("acepta_datos") is True,
            entrega=entrega,
            aprobacion=aprobacion,
        )

        estado = self.public_order(OrdenQuerys(self.db, ctx), orden)
        if not creada:
            return self.tools.output(200, "Tu pedido ya estaba registrado.", estado)
        quien = "El restaurante" if canal == "domicilio" else "El mesero"
        msg = f"Pedido enviado. {quien} lo confirmará en un momento." if estado["estado"] == "pendiente_aprobacion" \
            else "Pedido enviado a preparación."
        return self.tools.output(201, msg, estado)

    def delivery_data(self, data: dict, ctx: dict):
        """ Datos de entrega del pedido web: nombre, celular y dirección obligatorios, con autorización de datos.
            Límite de domicilios por celular para frenar el spam (doc 17A, sección 5): cuenta los pedidos
            creados, no los intentos, para que un cliente que corrige su pedido no quede bloqueado. """
        restaurante = self.db.get(RestauranteModel, ctx["restaurante_id"])
        entrega = dict(data.get("entrega") or {})
        if not entrega.get("zona_envio_id") or not (entrega.get("direccion") or "").strip():
            raise CustomException("Elige tu zona y escribe la dirección de entrega.")
        telefono = telefono_valido(data.get("cliente_telefono") or entrega.get("telefono"))
        if not telefono:
            raise CustomException("Escribe un celular válido: lo usamos para confirmar el pedido y avisarte.")
        if not (data.get("cliente_nombre") or "").strip():
            raise CustomException("Escribe tu nombre para la entrega.")
        if data.get("acepta_datos") is not True:
            raise CustomException("Para llevarte el pedido necesitamos tu nombre, celular y dirección: acepta el aviso de datos.")
        forma_pago = entrega.get("forma_pago") or "contra_entrega"
        if forma_pago not in FORMAS_PAGO or (forma_pago == "en_linea" and not self.online_payments(restaurante)):
            raise CustomException("Elige cómo vas a pagar.")
        querys = OrdenQuerys(self.db, ctx)
        recientes = querys.scoped(EntregaModel).filter(
            EntregaModel.telefono == telefono, EntregaModel.creado_en >= now() - timedelta(seconds=VENTANA_TELEFONO)).count()
        # Un reintento del mismo pedido (misma clave) no es un pedido nuevo
        if recientes >= ORDENES_POR_TELEFONO and not querys.get_orden_by_clave(str(data["clave_idempotencia"]).strip()):
            raise CustomException("Ya recibimos varios pedidos con este celular. Si necesitas algo más, llama al restaurante.", 429)
        entrega.update({"telefono": telefono, "guardar_direccion": True, "forma_pago": forma_pago})
        return entrega, self.web_config(restaurante).aprobacion

    # Seguimiento del pedido con el token de seguimiento (sin exponer el id interno)
    def status(self, data: dict):

        limiter.check(f"publico:{self.ip}", CONSULTAS_POR_IP, VENTANA_CONSULTAS,
                      "Demasiadas consultas. Espera un momento.")
        orden = OrdenQuerys(self.db).get_orden_by_seguimiento(data["seguimiento"])
        if not orden:
            raise CustomException("No encontramos este pedido.", 404)

        ctx = {"empresa_id": orden.empresa_id, "restaurante_id": orden.restaurante_id}
        estado = self.public_order(OrdenQuerys(self.db, ctx), orden)
        # Un pedido por confirmar todavía no se paga: el restaurante puede rechazarlo
        estado["pago_en_linea"] = estado["estado"] != "pendiente_aprobacion" and \
            self.online_payments(self.db.get(RestauranteModel, orden.restaurante_id))
        return self.tools.output(200, "Estado del pedido.", estado)

    def online_payments(self, restaurante):
        modulos, _ = modulos_activos(self.db, restaurante)
        if "pagos_linea" not in modulos:
            return False
        config = self.db.query(PagoLineaConfigModel).filter(PagoLineaConfigModel.restaurante_id == restaurante.id).first()
        return bool(config and config.activo)

    def web_config(self, restaurante):
        return self.db.query(DomicilioWebModel).filter(DomicilioWebModel.restaurante_id == restaurante.id).first()

    def resolve(self, token: str):
        contexto = self.querys.resolve_token(token)
        if not contexto:
            raise CustomException(NO_DISPONIBLE, 404)
        return contexto

    # Motivo por el que no se puede pedir ahora; None si se puede
    def unavailable_reason(self, contexto: dict):
        empresa, restaurante, zona, mesa = (contexto["empresa"], contexto["restaurante"],
                                            contexto["zona"], contexto["mesa"])
        modulos, _ = modulos_activos(self.db, restaurante)
        if empresa.estado in ["suspendida", "cancelada"] or "pedidos" not in modulos:
            return "Este restaurante no está recibiendo pedidos por QR en este momento."
        if contexto["qr"].tipo == "domicilio":
            web = self.web_config(restaurante)
            if "domicilios" not in modulos or not web or not web.activo or \
                    not EntregaQuerys(self.db, self.public_ctx(contexto)).zonas():
                return SIN_DOMICILIOS
        if restaurante.estado != "activo":
            return restaurante.mensaje_carta or "El restaurante no está recibiendo pedidos en este momento."
        if not zona.activo or zona.eliminado_en:
            return "Esta zona no está recibiendo pedidos en este momento."
        if not mesa.activo or mesa.bloqueada or mesa.eliminado_en:
            return "Esta mesa no está recibiendo pedidos. Pide ayuda al personal."
        ctx = self.public_ctx(contexto)
        abierta, mensaje = HorarioQuerys(self.db, ctx).reception_status(zona)
        if not abierta:
            return mensaje
        if not HorarioQuerys(self.db, ctx).current_menu(zona):
            return "La carta de esta zona aún no está lista."
        return None

    def public_ctx(self, contexto: dict):
        restaurante = contexto["restaurante"]
        return {
            "empresa_id": restaurante.empresa_id,
            "restaurante_id": restaurante.id,
            "zona_horaria": restaurante.zona_horaria,
            "hora_inicio_jornada": restaurante.hora_inicio_jornada,
            "usuario_id": None,
            "permisos": set(),
            "modulos": modulos_activos(self.db, restaurante)[0],
            "publico": True,
            "ip": self.ip,
            "dispositivo": self.dispositivo,
        }

    # Lo que el cliente puede ver de su orden: sin ids internos (RN-API-04)
    def public_order(self, querys: OrdenQuerys, orden):
        detalle = querys.format_orden(orden)
        entrega = querys.scoped(EntregaModel).filter(EntregaModel.orden_id == orden.id).first() \
            if orden.canal == "domicilio" else None
        return {
            "seguimiento": orden.token_seguimiento,
            "numero_texto": detalle["numero_texto"],
            "estado": detalle["estado"],
            "estado_etiqueta": ESTADOS_ORDEN.get(detalle["estado"], detalle["estado"]),
            "restaurante": querys.restaurante().nombre,
            "mesa": detalle["mesa"],
            "mesa_tipo": detalle["mesa_tipo"],
            "zona": detalle["zona"],
            "cliente_nombre": detalle["cliente_nombre"],
            "total": detalle["total"],
            "moneda": detalle["moneda"],
            "creado_en": detalle["creado_en"],
            # Domicilio: el estado de la entrega completa el de la cocina (salió, llegó o no se pudo)
            "entrega": {
                "estado": entrega.estado, "direccion": entrega.direccion, "barrio": entrega.barrio,
                "tarifa": entrega.tarifa, "forma_pago": entrega.forma_pago,
            } if entrega else None,
            "items": [{
                "nombre": item["nombre"],
                "cantidad": item["cantidad"],
                "total": item["total"],
                "nota": item["nota"],
                "modificadores": [m["nombre"] for m in item["modificadores"]],
                "estado": item["estado"],
                "estado_etiqueta": ETIQUETAS.get(item["estado"], item["estado"]),
                "motivo": item["motivo_cancelacion"] if item["estado"] == CANCELADO else None,
            } for item in detalle["items"]],
        }
