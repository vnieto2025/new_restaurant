from Rules.campo import campo


# Validate data login
def val_login(params):
    return [
        campo("string", "usuario", params["usuario"]),
        campo("string", "contraseña", params["password"]),
        campo("int", "restaurante", params.get("restaurante_id"), False),
    ]


def val_cambiar_restaurante(params):
    return [campo("int", "restaurante", params["restaurante_id"])]


def val_cambiar_password(params):
    return [
        campo("string", "contraseña actual", params["password_actual"]),
        campo("string", "contraseña nueva", params["password_nueva"], limite={"min": 8, "max": 100}),
    ]


RULES = {
    "/login": val_login,
    "/auth/cambiar_restaurante": val_cambiar_restaurante,
    "/auth/cambiar_password": val_cambiar_password,
}
