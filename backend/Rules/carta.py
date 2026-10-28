from Rules.campo import campo


def campos_carta(params):
    return [
        campo("string", "nombre", params["nombre"], limite={"min": 2, "max": 80}),
        campo("list", "productos", params.get("productos"), False),
    ]


def val_carta_id(params):
    return [campo("int", "carta", params["carta_id"])]


def val_update(params):
    return val_carta_id(params) + campos_carta(params)


def val_change_status(params):
    return val_carta_id(params) + [campo("bool", "activo", params["activo"])]


RULES = {
    "/carta/get": val_carta_id,
    "/carta/create": campos_carta,
    "/carta/update": val_update,
    "/carta/change_status": val_change_status,
}
