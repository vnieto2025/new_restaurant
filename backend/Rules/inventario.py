from Rules.campo import campo

UNIDADES = ["g", "ml", "und"]


def campos_insumo(params):
    reglas = [
        campo("string", "nombre", params["nombre"], limite={"min": 2, "max": 100}),
        campo("string", "código", params.get("codigo"), False, limite={"min": 1, "max": 30}),
        campo("string", "categoría", params.get("categoria"), False, limite={"min": 2, "max": 40}),
        campo("opcion", "unidad", params["unidad"], opciones=UNIDADES),
        campo("bool", "preparación", params.get("es_preparacion"), False),
        campo("string", "ubicación", params.get("ubicacion"), False, limite={"min": 2, "max": 40}),
        campo("list", "presentaciones", params.get("presentaciones"), False),
    ]
    for posicion, p in enumerate(params.get("presentaciones") or [], start=1):
        reglas.append(campo("string", f"nombre de la presentación {posicion}", p.get("nombre"), False, limite={"min": 1, "max": 60}))
    return reglas


def val_insumo_id(params):
    return [campo("int", "insumo", params["insumo_id"])]


def val_cantidad_movimiento(params):
    return val_insumo_id(params) + [
        campo("int", "presentación", params.get("presentacion_id"), False),
        campo("string", "motivo", params.get("motivo"), False, limite={"min": 3, "max": 200}),
    ]


def val_receta(params):
    reglas = [
        campo("int", "producto", params.get("producto_id"), False),
        campo("int", "preparación", params.get("insumo_id"), False),
        campo("list", "ingredientes", params.get("lineas")),
    ]
    for posicion, linea in enumerate(params.get("lineas") or [], start=1):
        reglas.append(campo("int", f"insumo del ingrediente {posicion}", linea["insumo_id"]))
    return reglas


def val_destino(params):
    return [campo("int", "producto", params.get("producto_id"), False), campo("int", "preparación", params.get("insumo_id"), False)]


RULES = {
    "/insumo/create": campos_insumo,
    "/insumo/update": lambda p: val_insumo_id(p) + campos_insumo(p),
    "/insumo/change_status": lambda p: val_insumo_id(p) + [campo("bool", "activo", p["activo"])],
    "/receta/get": val_destino,
    "/receta/save": val_receta,
    "/receta/delete": val_destino,
    "/receta/opcion/save": lambda p: [campo("int", "opción", p["opcion_id"]), campo("list", "insumos", p.get("lineas"), False)],
    "/inventario/movimientos": lambda p: [
        campo("int", "insumo", p.get("insumo_id"), False), campo("date", "desde", p.get("desde"), False),
        campo("date", "hasta", p.get("hasta"), False)],
    "/inventario/entrada": val_cantidad_movimiento,
    "/inventario/merma": lambda p: val_cantidad_movimiento(p) + [campo("string", "motivo", p["motivo"], limite={"min": 3, "max": 200})],
    "/inventario/ajuste": lambda p: val_insumo_id(p) + [campo("string", "motivo", p["motivo"], limite={"min": 3, "max": 200})],
    "/inventario/producir": val_cantidad_movimiento,
    "/conteo/create": lambda p: [
        campo("string", "nombre", p.get("nombre"), False, limite={"min": 2, "max": 80}),
        campo("string", "categoría", p.get("categoria"), False, limite={"min": 2, "max": 40}),
        campo("list", "insumos", p.get("insumo_ids"), False)],
    "/conteo/get": lambda p: [campo("int", "conteo", p["conteo_id"])],
    "/conteo/save": lambda p: [campo("int", "conteo", p["conteo_id"]), campo("list", "líneas", p.get("lineas"))],
    "/conteo/aplicar": lambda p: [campo("int", "conteo", p["conteo_id"])],
    "/conteo/descartar": lambda p: [campo("int", "conteo", p["conteo_id"])],
}
