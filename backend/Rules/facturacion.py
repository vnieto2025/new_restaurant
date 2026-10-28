from Rules.campo import campo

TIPOS_ID = ["CC", "CE", "NIT", "PAS", "PPT", "TI"]


def campos_impuesto(params):
    return [
        campo("string", "nombre", params["nombre"], limite={"min": 2, "max": 60}),
        campo("opcion", "tipo", params["tipo"], opciones=["iva", "consumo", "otro"]),
        campo("string", "código", params.get("codigo"), False, limite={"min": 1, "max": 10}),
        campo("bool", "por defecto", params.get("por_defecto"), False),
    ]


def val_impuesto_create(params):
    return campos_impuesto(params) + [
        campo("float", "porcentaje", params["porcentaje"]),
        campo("date", "vigente desde", params.get("vigente_desde"), False),
    ]


def val_impuesto_id(params):
    return [campo("int", "impuesto", params["impuesto_id"])]


def val_tarifa(params):
    return val_impuesto_id(params) + [
        campo("float", "porcentaje", params["porcentaje"]),
        campo("date", "vigente desde", params.get("vigente_desde"), False),
        campo("string", "motivo", params.get("motivo"), False, limite={"min": 3, "max": 200}),
    ]


def campos_resolucion(params):
    return [
        campo("opcion", "tipo de documento", params["tipo_documento"], opciones=["pos", "factura", "nota_credito"]),
        campo("string", "número de resolución", params.get("numero_resolucion"), False, limite={"min": 1, "max": 40}),
        campo("string", "prefijo", params.get("prefijo"), False, limite={"min": 1, "max": 10}),
        campo("int", "número inicial", params["desde"]),
        campo("int", "número final", params["hasta"]),
        campo("date", "vigente desde", params.get("vigente_desde"), False),
        campo("date", "vigente hasta", params.get("vigente_hasta"), False),
        campo("int", "caja", params.get("caja_id"), False),
        campo("int", "alerta de números restantes", params.get("alerta_restantes"), False),
    ]


def val_resolucion_update(params):
    return [campo("int", "resolución", params["resolucion_id"])] + campos_resolucion(params)


def val_receptor(receptor, obligatorio=True):
    receptor = receptor or {}
    return [
        campo("int", "cliente", receptor.get("cliente_id"), False),
        campo("string", "nombre del cliente", receptor.get("nombre"), False, limite={"min": 2, "max": 150}),
        campo("opcion", "tipo de documento del cliente", receptor.get("tipo_documento"), obligatorio, opciones=TIPOS_ID),
        campo("string", "documento del cliente", receptor.get("documento"), obligatorio, limite={"min": 3, "max": 30}),
        campo("email", "correo del cliente", receptor.get("correo"), False),
    ]


def val_config(params):
    return [
        campo("string", "proveedor", params["proveedor"], limite={"min": 2, "max": 30}),
        campo("opcion", "ambiente", params.get("ambiente"), False, opciones=["pruebas", "produccion"]),
        campo("opcion", "documento por defecto", params.get("documento_defecto"), False, opciones=["pos", "factura"]),
        campo("int", "días para facturar", params.get("dias_factura_posterior"), False),
        campo("bool", "activa", params.get("activo"), False),
    ]


def val_documentos(params):
    return [
        campo("opcion", "estado", params.get("estado"), False, opciones=["pendiente", "emitida", "aceptada", "rechazada", "anulada"]),
        campo("opcion", "tipo", params.get("tipo"), False, opciones=["pos", "factura", "nota_credito"]),
        campo("date", "desde", params.get("desde"), False),
        campo("date", "hasta", params.get("hasta"), False),
        campo("string", "búsqueda", params.get("buscar"), False, limite={"min": 1, "max": 60}),
    ]


RULES = {
    "/impuesto/create": val_impuesto_create,
    "/impuesto/update": lambda p: val_impuesto_id(p) + campos_impuesto(p),
    "/impuesto/change_status": lambda p: val_impuesto_id(p) + [campo("bool", "activo", p["activo"])],
    "/impuesto/tarifa": val_tarifa,
    "/resolucion/create": campos_resolucion,
    "/resolucion/update": val_resolucion_update,
    "/resolucion/change_status": lambda p: [campo("int", "resolución", p["resolucion_id"]), campo("bool", "activo", p["activo"])],
    "/facturacion/config/save": val_config,
    "/documento/list": val_documentos,
    "/documento/get": lambda p: [campo("int", "documento", p["documento_id"])],
    "/documento/facturar": lambda p: [campo("int", "cuenta", p["cuenta_id"])] + val_receptor(p.get("receptor"), bool(p.get("receptor"))),
    "/documento/corregir": lambda p: [campo("int", "documento", p["documento_id"])] + val_receptor(p.get("receptor"), False),
    "/documento/enviar": lambda p: [campo("list", "documentos", p.get("documento_ids"), False)],
    "/documento/impuestos": lambda p: [campo("date", "desde", p.get("desde"), False), campo("date", "hasta", p.get("hasta"), False)],
}
