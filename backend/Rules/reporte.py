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
    "/reporte/analisis": val_periodo,
    "/reporte/sedes": val_periodo,
    "/reporte/mesero": val_mesero,
    "/reporte/resumen_diario": lambda p: [campo("date", "jornada", p.get("jornada"), False)],
    "/reporte/resumen_diario/config/save": lambda p: [
        campo("bool", "activo", p.get("activo"), False), campo("string", "celular", p.get("telefono"), False, limite={"min": 7, "max": 20}),
        campo("string", "nombre", p.get("nombre"), False, limite={"min": 2, "max": 60})],
    "/alerta/silenciar": lambda p: [campo("string", "alerta", p["codigo"], limite={"min": 3, "max": 40}),
                                    campo("bool", "silenciar", p.get("silenciar"), False)],
    "/alerta/config/save": lambda p: [campo("list", "alertas", p["alertas"])],
}
