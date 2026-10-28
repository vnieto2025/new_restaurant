from Rules.campo import campo

FORMAS_PAGO = ["contado", "credito", "caja"]
ESTADOS = ["borrador", "solicitada", "parcial", "recibida", "cerrada", "anulada", "pendientes"]


def campos_proveedor(params):
    return [
        campo("string", "nombre", params["nombre"], limite={"min": 2, "max": 100}),
        campo("string", "razón social", params.get("razon_social"), False, limite={"min": 2, "max": 150}),
        campo("string", "documento", params.get("documento"), False, limite={"min": 3, "max": 30}),
        campo("string", "contacto", params.get("contacto"), False, limite={"min": 2, "max": 100}),
        campo("string", "teléfono", params.get("telefono"), False, limite={"min": 7, "max": 20}),
        campo("string", "WhatsApp", params.get("whatsapp"), False, limite={"min": 7, "max": 20}),
        campo("email", "correo", params.get("correo"), False),
        campo("string", "dirección", params.get("direccion"), False, limite={"min": 5, "max": 200}),
        campo("opcion", "forma de pago", params.get("forma_pago"), False, opciones=["contado", "credito"]),
        campo("int", "plazo", params.get("plazo_dias"), False),
        campo("string", "días de entrega", params.get("dias_entrega"), False, limite={"min": 2, "max": 80}),
        campo("int", "pedido mínimo", params.get("pedido_minimo"), False),
        campo("string", "notas", params.get("notas"), False, limite={"min": 1, "max": 500}),
    ]


def val_proveedor_id(params):
    return [campo("int", "proveedor", params["proveedor_id"])]


def val_insumos_proveedor(params):
    reglas = val_proveedor_id(params) + [campo("list", "insumos", params.get("insumos"), False)]
    for posicion, fila in enumerate(params.get("insumos") or [], start=1):
        reglas += [campo("int", f"insumo {posicion}", fila["insumo_id"]),
                   campo("int", f"presentación del insumo {posicion}", fila.get("presentacion_id"), False),
                   campo("bool", f"preferido del insumo {posicion}", fila.get("preferido"), False)]
    return reglas


def campos_compra(params):
    reglas = [
        campo("int", "proveedor", params.get("proveedor_id"), False),
        campo("string", "proveedor", params.get("proveedor_nombre"), False, limite={"min": 2, "max": 100}),
        campo("date", "fecha", params.get("fecha"), False),
        campo("date", "entrega esperada", params.get("entrega_esperada"), False),
        campo("opcion", "forma de pago", params.get("forma_pago"), False, opciones=FORMAS_PAGO),
        campo("string", "notas", params.get("notas"), False, limite={"min": 1, "max": 500}),
        campo("list", "insumos", params["lineas"]),
    ]
    for posicion, linea in enumerate(params.get("lineas") or [], start=1):
        reglas += [campo("int", f"insumo de la línea {posicion}", linea["insumo_id"]),
                   campo("int", f"presentación de la línea {posicion}", linea.get("presentacion_id"), False),
                   campo("int", f"valor de la línea {posicion}", linea.get("total"), False)]
    return reglas


def val_compra_id(params):
    return [campo("int", "compra", params["compra_id"])]


def val_recepcion(params):
    reglas = val_compra_id(params) + [
        campo("list", "insumos recibidos", params["lineas"]),
        campo("string", "notas", params.get("notas"), False, limite={"min": 1, "max": 200}),
        campo("string", "factura del proveedor", params.get("factura_proveedor"), False, limite={"min": 1, "max": 40}),
    ]
    for posicion, linea in enumerate(params.get("lineas") or [], start=1):
        reglas += [campo("int", f"línea {posicion}", linea["compra_linea_id"]),
                   campo("string", f"novedad de la línea {posicion}", linea.get("novedad"), False, limite={"min": 1, "max": 200})]
    return reglas


RULES = {
    "/proveedor/list": lambda p: [campo("string", "búsqueda", p.get("buscar"), False, limite={"min": 1, "max": 60})],
    "/proveedor/get": val_proveedor_id,
    "/proveedor/create": campos_proveedor,
    "/proveedor/update": lambda p: val_proveedor_id(p) + campos_proveedor(p),
    "/proveedor/change_status": lambda p: val_proveedor_id(p) + [campo("bool", "activo", p["activo"])],
    "/proveedor/insumos": val_insumos_proveedor,
    "/compra/list": lambda p: [
        campo("opcion", "estado", p.get("estado"), False, opciones=ESTADOS),
        campo("int", "proveedor", p.get("proveedor_id"), False),
        campo("date", "desde", p.get("desde"), False), campo("date", "hasta", p.get("hasta"), False),
        campo("string", "búsqueda", p.get("buscar"), False, limite={"min": 1, "max": 60})],
    "/compra/get": val_compra_id,
    "/compra/create": lambda p: campos_compra(p) + [campo("bool", "solicitar", p.get("solicitar"), False)],
    "/compra/update": lambda p: val_compra_id(p) + campos_compra(p),
    "/compra/solicitar": val_compra_id,
    "/compra/recibir": val_recepcion,
    "/compra/rapida": lambda p: campos_compra(p) + [
        campo("string", "factura del proveedor", p.get("factura_proveedor"), False, limite={"min": 1, "max": 40})],
    "/compra/cerrar": lambda p: val_compra_id(p) + [
        campo("string", "factura del proveedor", p.get("factura_proveedor"), False, limite={"min": 1, "max": 40}),
        campo("string", "notas", p.get("notas"), False, limite={"min": 1, "max": 200}),
        campo("bool", "cerrar con pendiente", p.get("cerrar_con_pendiente"), False)],
    "/compra/anular": lambda p: val_compra_id(p) + [
        campo("string", "motivo", p["motivo"], limite={"min": 3, "max": 200}),
        campo("bool", "reintegrar a caja", p.get("reintegrar_caja"), False)],
}
