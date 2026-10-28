from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from Utils.tools import Tools, CustomException, clean_text, jornada
from Querys.restaurante import RestauranteQuerys
from Models.restaurante_model import RestauranteModel, ESTADOS_RESTAURANTE
from Models.contrato_model import ContratoModel, ESTADOS_CONTRATO
from Models.punto_produccion_model import PuntoProduccionModel
from Models.carta_model import CartaModel
from Models.zona_model import ZonaModel
from Models.mesa_model import MesaModel
from Models.qr_acceso_model import QrAccesoModel
from Class.Qr import new_token
from Models.caja_model import CajaModel
from Models.medio_pago_model import MedioPagoModel

DIAS_PRUEBA = 30

# Medios de pago con los que arranca un restaurante; se ajustan en Configuración (doc 20)
MEDIOS_INICIALES = [
    {"nombre": "Efectivo", "tipo": "efectivo", "pide_referencia": False},
    {"nombre": "Tarjeta (datáfono)", "tipo": "tarjeta", "pide_referencia": False},
    {"nombre": "Transferencia", "tipo": "transferencia", "pide_referencia": True},
    {"nombre": "Nequi", "tipo": "transferencia", "pide_referencia": True},
    {"nombre": "Daviplata", "tipo": "transferencia", "pide_referencia": True},
]


def parse_hour(value: str):
    return datetime.strptime(value or "06:00", "%H:%M").time()


def validate_timezone(value: str):
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise CustomException("La zona horaria no es válida.")
    return value


# Ordena los módulos pedidos y verifica sus dependencias (doc 02A, sección 3)
def resolve_modules(querys: RestauranteQuerys, codigos: list):
    codigos = set(codigos or []) | {m.codigo for m in querys.get_modulos() if m.obligatorio}
    modulos = querys.get_modulos(list(codigos))
    encontrados = {m.codigo for m in modulos}
    faltantes = codigos - encontrados
    if faltantes:
        raise CustomException(f"Módulos no válidos: {', '.join(sorted(faltantes))}.")
    for modulo in modulos:
        for dependencia in (modulo.depende_de or "").split(","):
            if dependencia and dependencia not in encontrados:
                raise CustomException(f"El módulo {modulo.nombre} requiere el módulo {dependencia}.")
    return modulos


def restaurant_fields(data: dict):
    fields = {
        "nombre": clean_text(data["nombre"]),
        "tipo": data.get("tipo") or "restaurante",
        "direccion": clean_text(data.get("direccion")),
        "telefono": clean_text(data.get("telefono")),
        "zona_horaria": validate_timezone(data.get("zona_horaria") or "America/Bogota"),
        "hora_inicio_jornada": parse_hour(data.get("hora_inicio_jornada")),
        "mensaje_carta": clean_text(data.get("mensaje_carta")),
    }
    if data.get("propina_sugerida") is not None:
        propina = int(data["propina_sugerida"])
        if propina < 0 or propina > 30:
            raise CustomException("La propina sugerida debe estar entre 0 % y 30 %.")
        fields["propina_sugerida"] = propina
    if "aviso_datos" in data:
        fields["aviso_datos"] = clean_text(data.get("aviso_datos"))
        fields["politica_url"] = clean_text(data.get("politica_url"))
    if "reiniciar_agotados" in data:
        fields["reiniciar_agotados"] = data["reiniciar_agotados"] is True
    if "moneda" in data and data["moneda"]:
        fields["moneda"] = data["moneda"]
    return fields


def bootstrap_restaurant(db, empresa_id: int, data: dict, modulos: list, estado_contrato="prueba", fecha_fin=None):
    """ Crea un restaurante con todo lo que necesita para operar desde el primer día (doc 07, sección 3):
        contrato con sus módulos, punto de producción "Cocina", carta principal,
        zona inicial "Salón" y zona de mostrador con la mesa externa y su QR para llevar.
        No hace commit: la llamada decide cuándo confirmar. """

    querys = RestauranteQuerys(db, {"empresa_id": empresa_id})
    if estado_contrato not in ESTADOS_CONTRATO:
        raise CustomException("El estado del contrato no es válido.")
    modulos = resolve_modules(querys, modulos)

    fields = restaurant_fields(data)
    restaurante_id = querys.insert_data(RestauranteModel, fields, commit=False)
    hoy = jornada(tz_name=fields["zona_horaria"], inicio=fields["hora_inicio_jornada"])

    if estado_contrato == "prueba" and not fecha_fin:
        fecha_fin = hoy + timedelta(days=DIAS_PRUEBA)

    contrato_id = querys.insert_data(ContratoModel, {
        "restaurante_id": restaurante_id,
        "estado": estado_contrato,
        "fecha_inicio": hoy,
        "fecha_fin": fecha_fin,
    }, commit=False)
    querys.set_modulos_contrato(querys.db.get(ContratoModel, contrato_id), modulos)

    local = RestauranteQuerys(db, {"empresa_id": empresa_id, "restaurante_id": restaurante_id})
    cocina_id = local.insert_data(PuntoProduccionModel, {"nombre": "Cocina", "tipo": "cocina"}, commit=False)
    carta_id = local.insert_data(CartaModel, {"nombre": "Carta principal"}, commit=False)
    local.insert_data(ZonaModel, {
        "nombre": "Salón", "orden": 1, "carta_id": carta_id,
        "punto_produccion_id": cocina_id, "modo_qr": "aprobacion",
    }, commit=False)
    mostrador_id = local.insert_data(ZonaModel, {
        "nombre": "Mostrador", "orden": 99, "carta_id": carta_id, "punto_produccion_id": cocina_id,
        "modo_qr": "libre", "es_mostrador": True,
    }, commit=False)
    # Mesa externa única por restaurante (RN-RES-02)
    externa_id = local.insert_data(MesaModel, {
        "zona_id": mostrador_id, "nombre": "Para llevar", "tipo": "externa",
    }, commit=False)
    local.insert_data(QrAccesoModel, {
        "tipo": "rapido", "zona_id": mostrador_id, "mesa_id": externa_id, "token": new_token(),
    }, commit=False)
    local.insert_data(CajaModel, {"nombre": "Caja principal"}, commit=False)
    for orden, medio in enumerate(MEDIOS_INICIALES):
        local.insert_data(MedioPagoModel, {**medio, "orden": orden}, commit=False)
    return restaurante_id


class Restaurante:

    def __init__(self, db, ctx: dict):
        self.ctx = ctx
        self.tools = Tools()
        self.querys = RestauranteQuerys(db, ctx)

    # Configuración del restaurante actual
    def get(self):
        restaurante = self.querys.get_restaurante()
        return self.tools.output(200, "Datos del restaurante.", self.querys.format_restaurante(restaurante))

    # Function for update the restaurant settings
    def update(self, data: dict):

        restaurante = self.querys.get_restaurante()
        antes = self.querys.format_restaurante(restaurante)
        fields = restaurant_fields(data)
        fields.pop("moneda", None)

        # La hora de inicio de jornada solo cambia sin mesas abiertas (RN-RES-04)
        if fields["hora_inicio_jornada"] != restaurante.hora_inicio_jornada and self.querys.count_sesiones_abiertas():
            raise CustomException("La hora de inicio de jornada solo se puede cambiar cuando no hay mesas abiertas.")

        # Si cambia el aviso de datos, sube su versión: cada consentimiento guarda la que aceptó (RN-PRI-02)
        if "aviso_datos" in fields and fields["aviso_datos"] != restaurante.aviso_datos:
            restaurante.aviso_version = (restaurante.aviso_version or 1) + 1
        for key, value in fields.items():
            setattr(restaurante, key, value)
        self.querys.db.flush()
        despues = self.querys.format_restaurante(restaurante)
        self.querys.audit("restaurante_actualizado", "restaurante", restaurante.id,
                          antes=self.tools_json(antes), despues=self.tools_json(despues))

        return self.tools.output(200, "Restaurante actualizado.", despues)

    # Pausar, reanudar o cerrar temporalmente la recepción de órdenes (doc 07, sección 4)
    def change_status(self, data: dict):

        estado = data["estado"]
        if estado not in ESTADOS_RESTAURANTE or estado == "inactivo":
            raise CustomException("El estado no es válido.")

        restaurante = self.querys.get_restaurante()
        antes = restaurante.estado
        restaurante.estado = estado
        if "mensaje_carta" in data:
            restaurante.mensaje_carta = clean_text(data.get("mensaje_carta"))
        self.querys.db.flush()
        self.querys.audit("restaurante_estado", "restaurante", restaurante.id,
                          antes={"estado": antes}, despues={"estado": estado})

        mensajes = {"activo": "Restaurante recibiendo órdenes.", "pausado": "Restaurante en pausa.",
                    "cerrado": "Restaurante cerrado temporalmente."}
        return self.tools.output(200, mensajes[estado], self.querys.format_restaurante(restaurante))

    # Las fechas no se guardan tal cual en JSONB
    def tools_json(self, data: dict):
        contrato = data.get("contrato")
        if contrato:
            contrato = {**contrato, "fecha_inicio": str(contrato["fecha_inicio"]), "fecha_fin": str(contrato["fecha_fin"])}
        return {**data, "contrato": contrato}
