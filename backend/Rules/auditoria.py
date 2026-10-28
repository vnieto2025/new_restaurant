from Rules.campo import campo


def val_list(params):
    return [
        campo("string", "acción", params.get("accion"), False, limite={"min": 2, "max": 60}),
        campo("int", "límite", params.get("limite"), False),
    ]


RULES = {
    "/auditoria/list": val_list,
}
