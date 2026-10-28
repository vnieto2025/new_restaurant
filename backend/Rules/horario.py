from Rules.campo import campo
from Models.horario_model import TIPOS_HORARIO


def val_get(params):
    return [campo("int", "zona", params.get("zona_id"), False)]


def val_set(params):
    reglas = [
        campo("int", "zona", params.get("zona_id"), False),
        campo("opcion", "tipo", params["tipo"], opciones=TIPOS_HORARIO),
        campo("list", "franjas", params.get("franjas"), False),
    ]
    for posicion, franja in enumerate(params.get("franjas") or [], start=1):
        reglas += [
            campo("int", f"día de la franja {posicion}", franja["dia_semana"]),
            campo("hora", f"inicio de la franja {posicion}", franja["desde"]),
            campo("hora", f"fin de la franja {posicion}", franja["hasta"]),
            campo("int", f"carta de la franja {posicion}", franja.get("carta_id"), False),
        ]
    return reglas


RULES = {
    "/horario/get": val_get,
    "/horario/set": val_set,
}
