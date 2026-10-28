from Rules.campo import campo


def val_periodo(params):
    return [
        campo("date", "fecha inicial", params.get("desde"), False),
        campo("date", "fecha final", params.get("hasta"), False),
    ]


def val_mesero(params):
    return val_periodo(params) + [campo("int", "mesero", params.get("usuario_id"), False)]


RULES = {
    "/reporte/ventas": val_periodo,
    "/reporte/cancelaciones": val_periodo,
    "/reporte/meseros": val_periodo,
    "/reporte/mesero": val_mesero,
}
