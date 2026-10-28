# Arma una regla de validación para Validator.validacion_datos_entrada
def campo(tipo: str, nombre: str, valor, obligatorio: bool = True, **extra):
    regla = {
        "tipo": tipo,
        "campo": nombre,
        "valor": valor,
        "obligatorio": obligatorio,
    }
    regla.update(extra)
    return regla


# Valida que una lista de ítems de orden tenga la forma esperada
def items_orden(items):
    reglas = [campo("list", "ítems", items)]
    for posicion, item in enumerate(items or [], start=1):
        reglas += [
            campo("int", f"producto del ítem {posicion}", item["producto_id"]),
            campo("int", f"cantidad del ítem {posicion}", item["cantidad"]),
            campo("string", f"nota del ítem {posicion}", item.get("nota"), False, limite={"min": 1, "max": 200}),
            campo("list", f"modificadores del ítem {posicion}", item.get("modificadores"), False),
        ]
    return reglas
