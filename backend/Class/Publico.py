from Utils.tools import Tools, CustomException
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
from Class.Orden import Orden

# Límites de uso de lo público (doc 10A, sección 4): por token del QR y por IP
ORDENES_POR_TOKEN = 6
ORDENES_POR_IP = 15
VENTANA_ORDENES = 600
CONSULTAS_POR_IP = 120
VENTANA_CONSULTAS = 60

AVISO_DATOS = ("{restaurante} usará tu nombre y teléfono para gestionar este pedido y avisarte cuando esté listo. "
               "Puedes pedir que los actualicemos o eliminemos cuando quieras.")

NO_DISPONIBLE = "Este código QR no está disponible. Pide ayuda al personal del restaurante."


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
        result = {
            "restaurante": restaurante.nombre,
            "zona": zona.nombre,
            "mesa": mesa.nombre,
            "tipo": contexto["qr"].tipo,
            "pide_nombre": mesa.tipo == "externa",
            "con_aprobacion": zona.modo_qr == "aprobacion",
            "moneda": restaurante.moneda,
            # Aviso de tratamiento de datos visible antes de pedir nombre o teléfono (RN-PRI-01)
            "aviso_datos": restaurante.aviso_datos or AVISO_DATOS.format(restaurante=restaurante.nombre),
            "politica_url": restaurante.politica_url,
            "disponible": motivo is None,
            "mensaje": motivo,
            # La cuenta de una mesa se puede pagar desde el celular (doc 20A)
            "pago_en_linea": mesa.tipo != "externa" and self.online_payments(restaurante),
            "categorias": [],
        }
        if motivo is None:
            ctx = self.public_ctx(contexto)
            result["categorias"] = CartaQuerys(self.db, ctx).menu(HorarioQuerys(self.db, ctx).current_menu(zona))

        return self.tools.output(200, "Carta disponible." if motivo is None else motivo, result)

    # El cliente envía su orden desde el celular, sin registrarse (doc 17, flujo B)
    def create_order(self, data: dict):

        token = data["token"]
        limiter.check(f"publico:orden:ip:{self.ip}", ORDENES_POR_IP, VENTANA_ORDENES,
                      "Se enviaron demasiadas órdenes desde este dispositivo. Pide ayuda al personal.")
        limiter.check(f"publico:orden:token:{token}", ORDENES_POR_TOKEN, VENTANA_ORDENES,
                      "Esta mesa envió demasiadas órdenes seguidas. Pide ayuda al personal.")

        contexto = self.resolve(token)
        motivo = self.unavailable_reason(contexto)
        if motivo:
            raise CustomException(motivo, 409)

        ctx = self.public_ctx(contexto)
        orden_class = Orden(self.db, ctx)
        mesa = orden_class.querys.get_own(MesaModel, contexto["mesa"].id, "mesa", lock=True)
        canal = "qr_rapido" if mesa.tipo == "externa" else "qr_mesa"

        orden, creada = orden_class.create_order(
            mesa=mesa,
            canal=canal,
            items=data["items"],
            clave=data["clave_idempotencia"],
            notas=data.get("notas"),
            cliente_nombre=data.get("cliente_nombre"),
            cliente_telefono=data.get("cliente_telefono"),
            acepta_datos=data.get("acepta_datos") is True,
        )

        estado = self.public_order(OrdenQuerys(self.db, ctx), orden)
        if not creada:
            return self.tools.output(200, "Tu pedido ya estaba registrado.", estado)
        msg = "Pedido enviado. El mesero lo confirmará en un momento." if estado["estado"] == "pendiente_aprobacion" \
            else "Pedido enviado a preparación."
        return self.tools.output(201, msg, estado)

    # Seguimiento del pedido con el token de seguimiento (sin exponer el id interno)
    def status(self, data: dict):

        limiter.check(f"publico:{self.ip}", CONSULTAS_POR_IP, VENTANA_CONSULTAS,
                      "Demasiadas consultas. Espera un momento.")
        orden = OrdenQuerys(self.db).get_orden_by_seguimiento(data["seguimiento"])
        if not orden:
            raise CustomException("No encontramos este pedido.", 404)

        ctx = {"empresa_id": orden.empresa_id, "restaurante_id": orden.restaurante_id}
        estado = self.public_order(OrdenQuerys(self.db, ctx), orden)
        estado["pago_en_linea"] = self.online_payments(self.db.get(RestauranteModel, orden.restaurante_id))
        return self.tools.output(200, "Estado del pedido.", estado)

    def online_payments(self, restaurante):
        modulos, _ = modulos_activos(self.db, restaurante)
        if "pagos_linea" not in modulos:
            return False
        config = self.db.query(PagoLineaConfigModel).filter(PagoLineaConfigModel.restaurante_id == restaurante.id).first()
        return bool(config and config.activo)

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
            "publico": True,
            "ip": self.ip,
            "dispositivo": self.dispositivo,
        }

    # Lo que el cliente puede ver de su orden: sin ids internos (RN-API-04)
    def public_order(self, querys: OrdenQuerys, orden):
        detalle = querys.format_orden(orden)
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
