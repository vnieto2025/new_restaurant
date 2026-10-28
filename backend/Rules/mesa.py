from Rules.campo import campo


def val_list(params):
    return [campo("int", "zona", params.get("zona_id"), False)]


def val_create(params):
    return [
        campo("int", "zona", params["zona_id"]),
        campo("string", "nombre", params["nombre"], limite={"min": 1, "max": 40}),
        campo("int", "capacidad", params.get("capacidad"), False),
    ]


def val_create_batch(params):
    return [
        campo("int", "zona", params["zona_id"]),
        campo("int", "desde", params["desde"]),
        campo("int", "hasta", params["hasta"]),
        campo("string", "prefijo", params.get("prefijo"), False, limite={"min": 1, "max": 30}),
        campo("int", "capacidad", params.get("capacidad"), False),
    ]


def val_update(params):
    return [
        campo("int", "mesa", params["mesa_id"]),
        campo("int", "zona", params.get("zona_id"), False),
        campo("string", "nombre", params["nombre"], limite={"min": 1, "max": 40}),
        campo("int", "capacidad", params.get("capacidad"), False),
    ]


def val_change_status(params):
    return [
        campo("int", "mesa", params["mesa_id"]),
        campo("bool", "activo", params.get("activo"), False),
        campo("bool", "bloqueada", params.get("bloqueada"), False),
    ]


def val_mesa_id(params):
    return [campo("int", "mesa", params["mesa_id"])]


def val_move(params):
    return [campo("int", "mesa", params["mesa_id"]), campo("int", "mesa de destino", params["destino_id"])]


def val_merge(params):
    return [campo("int", "mesa", params["mesa_id"]), campo("list", "mesas a unir", params["otras"])]


def val_reassign(params):
    return [campo("int", "mesa", params["mesa_id"]), campo("int", "mesero", params["mesero_id"])]


RULES = {
    "/mesa/trasladar": val_move,
    "/mesa/unir": val_merge,
    "/mesa/reasignar": val_reassign,
    "/mesa/meseros": val_mesa_id,
    "/mesa/list": val_list,
    "/mesa/create": val_create,
    "/mesa/create_lote": val_create_batch,
    "/mesa/update": val_update,
    "/mesa/change_status": val_change_status,
    "/mesa/abrir": val_mesa_id,
    "/mesa/cerrar": val_mesa_id,
}
