from Rules.campo import campo, items_orden


def val_sell(params):
    return items_orden(params["items"]) + [
        campo("string", "clave de idempotencia", params["clave_idempotencia"], limite={"min": 8, "max": 80}),
        campo("string", "nombre del cliente", params.get("cliente_nombre"), False, limite={"min": 2, "max": 100}),
        campo("int", "cliente", params.get("cliente_id"), False),
    ]


RULES = {
    "/pos/vender": val_sell,
    "/pos/cancelar": lambda p: [campo("int", "cuenta", p["cuenta_id"]),
                                campo("string", "motivo", p.get("motivo"), False, limite={"min": 3, "max": 200})],
}
