from Rules.campo import campo


def campos_categoria(params):
    return [
        campo("string", "nombre", params["nombre"], limite={"min": 2, "max": 60}),
        campo("int", "orden", params.get("orden"), False),
        campo("int", "punto de producción", params.get("punto_produccion_id"), False),
    ]


def val_update(params):
    return [campo("int", "categoría", params["categoria_id"])] + campos_categoria(params)


def val_change_status(params):
    return [
        campo("int", "categoría", params["categoria_id"]),
        campo("bool", "activo", params["activo"]),
    ]


RULES = {
    "/categoria/create": campos_categoria,
    "/categoria/update": val_update,
    "/categoria/change_status": val_change_status,
}
