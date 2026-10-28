from Rules.campo import campo
from Models.punto_produccion_model import TIPOS_PUNTO


def campos_punto(params):
    return [
        campo("string", "nombre", params["nombre"], limite={"min": 2, "max": 60}),
        campo("opcion", "tipo", params.get("tipo"), False, opciones=TIPOS_PUNTO),
        campo("bool", "imprime al abrir", params.get("imprime_al_abrir"), False),
        campo("bool", "salta en proceso", params.get("salta_en_proceso"), False),
        campo("int", "tiempo objetivo", params.get("tiempo_objetivo"), False),
    ]


def val_update(params):
    return [campo("int", "punto de producción", params["punto_produccion_id"])] + campos_punto(params)


def val_change_status(params):
    return [
        campo("int", "punto de producción", params["punto_produccion_id"]),
        campo("bool", "activo", params["activo"]),
    ]


RULES = {
    "/punto_produccion/create": campos_punto,
    "/punto_produccion/update": val_update,
    "/punto_produccion/change_status": val_change_status,
}
