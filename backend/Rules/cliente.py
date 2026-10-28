from Rules.campo import campo


def campos_cliente(params):
    return [
        campo("string", "nombre", params["nombre"], limite={"min": 2, "max": 120}),
        campo("string", "teléfono", params.get("telefono"), False, limite={"min": 7, "max": 20}),
        campo("email", "correo", params.get("correo"), False),
        campo("string", "documento", params.get("documento"), False, limite={"min": 3, "max": 30}),
        campo("string", "notas", params.get("notas"), False, limite={"min": 1, "max": 500}),
        campo("bool", "acepta tratamiento de datos", params.get("acepta_datos"), False),
        campo("bool", "acepta comunicaciones comerciales", params.get("acepta_comercial"), False),
        campo("bool", "recibe avisos de sus órdenes", params.get("acepta_avisos"), False),
    ]


def val_cliente_id(params):
    return [campo("int", "cliente", params["cliente_id"])]


def val_update(params):
    return val_cliente_id(params) + campos_cliente(params)


def val_search(params):
    return [campo("string", "búsqueda", params.get("texto"), False, limite={"min": 1, "max": 60})]


def val_status(params):
    return val_cliente_id(params) + [campo("opcion", "estado", params["estado"], opciones=["activo", "inactivo", "bloqueado"])]


def val_address(params):
    return val_cliente_id(params) + [
        campo("int", "dirección", params.get("direccion_id"), False),
        campo("string", "nombre de la dirección", params.get("nombre"), False, limite={"min": 1, "max": 40}),
        campo("string", "dirección", params["direccion"], limite={"min": 5, "max": 200}),
        campo("string", "indicaciones", params.get("indicaciones"), False, limite={"min": 1, "max": 250}),
        campo("string", "barrio", params.get("barrio"), False, limite={"min": 2, "max": 80}),
    ]


def val_anonymize(params):
    return val_cliente_id(params) + [campo("string", "motivo", params["motivo"], limite={"min": 3, "max": 200})]


RULES = {
    "/cliente/buscar": val_search,
    "/cliente/get": val_cliente_id,
    "/cliente/create": campos_cliente,
    "/cliente/update": val_update,
    "/cliente/change_status": val_status,
    "/cliente/direccion/save": val_address,
    "/cliente/direccion/delete": lambda p: [campo("int", "dirección", p["direccion_id"])],
    "/cliente/exportar": val_cliente_id,
    "/cliente/anonimizar": val_anonymize,
}
