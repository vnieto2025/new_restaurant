from Rules.campo import campo


def campos_usuario(params):
    return [
        campo("string", "nombre", params["nombre"], limite={"min": 2, "max": 150}),
        campo("string", "documento", params.get("documento"), False, limite={"min": 3, "max": 30}),
        campo("email", "correo", params.get("correo"), False),
        campo("list", "roles", params["roles"]),
        campo("list", "zonas", params.get("zonas"), False),
        campo("list", "puntos de producción", params.get("puntos"), False),
    ]


def val_create(params):
    return [
        campo("string", "usuario", params["usuario"], limite={"min": 3, "max": 60}),
        campo("string", "contraseña", params["password"]),
    ] + campos_usuario(params)


def val_update(params):
    return [
        campo("int", "usuario", params["usuario_id"]),
        campo("string", "contraseña", params.get("password"), False),
    ] + campos_usuario(params)


def val_usuario_id(params):
    return [campo("int", "usuario", params["usuario_id"])]


def val_change_status(params):
    return [
        campo("int", "usuario", params["usuario_id"]),
        campo("bool", "activo", params["activo"]),
    ]


def val_pin(params):
    return [campo("int", "usuario", params["usuario_id"]), campo("string", "PIN", params.get("pin"), False)]


RULES = {
    "/usuario/pin": val_pin,
    "/usuario/create": val_create,
    "/usuario/update": val_update,
    "/usuario/get": val_usuario_id,
    "/usuario/change_status": val_change_status,
}
