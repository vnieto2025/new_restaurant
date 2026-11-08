from Rules.campo import campo


# Validate data login
def val_login(params):
    return [
        campo("string", "usuario", params["usuario"]),
        campo("string", "contraseña", params["password"]),
        campo("int", "restaurante", params.get("restaurante_id"), False),
        campo("string", "código", params.get("codigo"), False, limite={"min": 6, "max": 12}),
    ]


def val_cambiar_restaurante(params):
    return [campo("int", "restaurante", params["restaurante_id"])]


def val_cambiar_password(params):
    return [
        campo("string", "contraseña actual", params["password_actual"]),
        campo("string", "contraseña nueva", params["password_nueva"], limite={"min": 8, "max": 100}),
    ]


def val_codigo(params):
    return [campo("string", "código", params["codigo"], limite={"min": 6, "max": 12})]


RULES = {
    "/auth/2fa/iniciar": lambda p: [campo("string", "clave", p["password"], limite={"min": 1, "max": 100})],
    "/auth/2fa/activar": val_codigo,
    "/auth/2fa/codigos": val_codigo,
    "/auth/2fa/desactivar": lambda p: val_codigo(p) + [campo("string", "clave", p["password"], limite={"min": 1, "max": 100})],
    "/login": val_login,
    "/auth/cambiar_restaurante": val_cambiar_restaurante,
    "/auth/cambiar_password": val_cambiar_password,
}
