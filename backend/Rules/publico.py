from Rules.campo import campo, items_orden
from Rules.domicilio import datos_entrega


def val_token(params):
    return [campo("string", "código", params["token"], limite={"min": 16, "max": 64})]


def val_create(params):
    return val_token(params) + [
        campo("string", "clave de idempotencia", params["clave_idempotencia"], limite={"min": 8, "max": 80}),
        campo("string", "nombre", params.get("cliente_nombre"), False, limite={"min": 2, "max": 100}),
        campo("string", "teléfono", params.get("cliente_telefono"), False, limite={"min": 7, "max": 30}),
        campo("string", "notas", params.get("notas"), False, limite={"min": 1, "max": 300}),
        campo("bool", "acepta tratamiento de datos", params.get("acepta_datos"), False),
    ] + items_orden(params["items"]) + datos_entrega(params.get("entrega"))


def val_status(params):
    return [campo("string", "seguimiento", params["seguimiento"], limite={"min": 16, "max": 64})]


RULES = {
    "/publico/qr": val_token,
    "/publico/orden/create": val_create,
    "/publico/orden/estado": val_status,
}
