from Rules.campo import campo


def campos_grupo(params):
    reglas = [
        campo("string", "nombre", params["nombre"], limite={"min": 2, "max": 60}),
        campo("int", "mínimo", params.get("minimo"), False),
        campo("int", "máximo", params.get("maximo"), False),
        campo("list", "opciones", params["opciones"]),
    ]
    for posicion, opcion in enumerate(params["opciones"] or [], start=1):
        reglas += [
            campo("string", f"nombre de la opción {posicion}", opcion["nombre"], limite={"min": 1, "max": 60}),
            campo("int", f"precio extra de la opción {posicion}", opcion.get("precio_extra"), False),
        ]
    return reglas


def val_update(params):
    return [campo("int", "grupo", params["grupo_id"])] + campos_grupo(params)


def val_change_status(params):
    return [campo("int", "grupo", params["grupo_id"]), campo("bool", "activo", params["activo"])]


RULES = {
    "/modificador/create": campos_grupo,
    "/modificador/update": val_update,
    "/modificador/change_status": val_change_status,
}
