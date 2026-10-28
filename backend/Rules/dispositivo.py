from Rules.campo import campo
from Models.dispositivo_model import TIPOS_DISPOSITIVO


def val_create(params):
    return [
        campo("string", "nombre", params["nombre"], limite={"min": 2, "max": 60}),
        campo("opcion", "tipo", params["tipo"], opciones=TIPOS_DISPOSITIVO),
        campo("int", "zona", params.get("zona_id"), False),
        campo("int", "punto de producción", params.get("punto_produccion_id"), False),
    ]


def val_dispositivo_id(params):
    return [campo("int", "dispositivo", params["dispositivo_id"])]


def val_change_status(params):
    return val_dispositivo_id(params) + [campo("bool", "activo", params["activo"])]


def val_pair(params):
    return [campo("string", "código", params["codigo"], limite={"min": 6, "max": 6})]


def val_token(params):
    return [campo("string", "dispositivo", params["token"], limite={"min": 20, "max": 100})]


def val_pin(params):
    return val_token(params) + [campo("string", "PIN", params["pin"], limite={"min": 4, "max": 6})]


RULES = {
    "/dispositivo/create": val_create,
    "/dispositivo/codigo": val_dispositivo_id,
    "/dispositivo/change_status": val_change_status,
    "/dispositivo/emparejar": val_pair,
    "/dispositivo/info": val_token,
    "/dispositivo/pin": val_pin,
}
