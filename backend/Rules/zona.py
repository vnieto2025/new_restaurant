from Rules.campo import campo
from Models.zona_model import MODOS_QR


def campos_zona(params):
    return [
        campo("string", "nombre", params["nombre"], limite={"min": 2, "max": 60}),
        campo("string", "código", params.get("codigo"), False, limite={"min": 1, "max": 10}),
        campo("int", "orden", params.get("orden"), False),
        campo("int", "carta", params.get("carta_id"), False),
        campo("int", "punto de producción", params.get("punto_produccion_id"), False),
        campo("opcion", "modo de QR", params.get("modo_qr"), False, opciones=MODOS_QR),
    ]


def val_update(params):
    return [campo("int", "zona", params["zona_id"])] + campos_zona(params)


def val_change_status(params):
    return [
        campo("int", "zona", params["zona_id"]),
        campo("bool", "activo", params["activo"]),
    ]


RULES = {
    "/zona/create": campos_zona,
    "/zona/update": val_update,
    "/zona/change_status": val_change_status,
}
