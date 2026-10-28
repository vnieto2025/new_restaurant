from Rules.campo import campo


def val_config(params):
    reglas = [
        campo("opcion", "modo", params.get("modo"), False, opciones=["manual", "automatico"]),
        campo("string", "proveedor", params.get("proveedor"), False, limite={"min": 2, "max": 30}),
        campo("string", "número remitente", params.get("numero_remitente"), False, limite={"min": 7, "max": 20}),
        campo("int", "límite diario", params.get("limite_diario"), False),
    ]
    for codigo, texto in (params.get("plantillas") or {}).items():
        reglas.append(campo("string", f"texto del aviso {codigo}", texto, False, limite={"min": 5, "max": 500}))
    return reglas


def val_aviso(params):
    return [campo("int", "aviso", params["notificacion_id"])]


RULES = {
    "/notificacion/config/save": val_config,
    "/notificacion/enviada": val_aviso,
    "/notificacion/descartar": val_aviso,
    "/notificacion/reintentar": val_aviso,
    "/notificacion/list": lambda p: [campo("int", "límite", p.get("limite"), False)],
    "/notificacion/prueba": lambda p: [campo("string", "teléfono", p["telefono"], limite={"min": 7, "max": 20})],
}
