from Rules.campo import campo


def val_generar(params):
    return [
        campo("string", "datos", params["conjunto"], limite={"min": 2, "max": 40}),
        campo("opcion", "formato", params["formato"], opciones=["csv", "xlsx"]),
        campo("date", "fecha inicial", params.get("desde"), False),
        campo("date", "fecha final", params.get("hasta"), False),
    ]


RULES = {
    "/exportacion/generar": val_generar,
}
