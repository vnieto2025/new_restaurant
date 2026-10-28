from Rules.campo import campo


def campos_producto(params):
    return [
        campo("int", "categoría", params["categoria_id"]),
        campo("string", "nombre", params["nombre"], limite={"min": 2, "max": 100}),
        campo("string", "descripción", params.get("descripcion"), False, limite={"min": 1, "max": 500}),
        campo("int", "precio", params["precio"]),
        campo("int", "punto de producción", params.get("punto_produccion_id"), False),
        campo("int", "orden", params.get("orden"), False),
        campo("list", "cartas", params.get("cartas"), False),
        campo("list", "grupos de modificadores", params.get("grupos"), False),
    ]


def val_list(params):
    return [
        campo("int", "categoría", params.get("categoria_id"), False),
        campo("string", "búsqueda", params.get("buscar"), False, limite={"min": 1, "max": 60}),
    ]


def val_update(params):
    return [campo("int", "producto", params["producto_id"])] + campos_producto(params)


def val_change_status(params):
    return [
        campo("int", "producto", params["producto_id"]),
        campo("bool", "activo", params["activo"]),
    ]


def val_sold_out(params):
    return [
        campo("int", "producto", params["producto_id"]),
        campo("bool", "agotado", params["agotado"]),
    ]


RULES = {
    "/producto/list": val_list,
    "/producto/create": campos_producto,
    "/producto/update": val_update,
    "/producto/change_status": val_change_status,
    "/producto/agotado": val_sold_out,
}
