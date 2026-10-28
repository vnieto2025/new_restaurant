from Rules.campo import campo
from Rules.facturacion import val_receptor


def val_open(params):
    return [
        campo("int", "sesión", params.get("sesion_mesa_id"), False),
        campo("int", "mesa", params.get("mesa_id"), False),
    ]


def val_cuenta_id(params):
    return [campo("int", "cuenta", params["cuenta_id"])]


def val_adjust(params):
    return val_cuenta_id(params) + [
        campo("int", "descuento", params.get("descuento"), False),
        campo("string", "motivo del descuento", params.get("descuento_motivo"), False, limite={"min": 3, "max": 200}),
        campo("int", "propina", params.get("propina"), False),
    ]


def val_pay(params):
    reglas = val_cuenta_id(params) + [
        campo("string", "clave de idempotencia", params["clave_idempotencia"], limite={"min": 8, "max": 80}),
        campo("list", "pagos", params.get("pagos"), False),
    ]
    for posicion, pago in enumerate(params.get("pagos") or [], start=1):
        reglas += [
            campo("int", f"medio del pago {posicion}", pago["medio_pago_id"]),
            campo("int", f"valor del pago {posicion}", pago["monto"]),
            campo("int", f"recibido del pago {posicion}", pago.get("recibido"), False),
            campo("string", f"referencia del pago {posicion}", pago.get("referencia"), False, limite={"min": 1, "max": 60}),
        ]
    # Factura a nombre del cliente (opcional)
    if params.get("factura"):
        reglas += val_receptor(params["factura"])
    return reglas


def val_void_payment(params):
    return [
        campo("int", "pago", params["pago_id"]),
        campo("string", "motivo", params["motivo"], limite={"min": 3, "max": 200}),
    ]


def val_void(params):
    return val_cuenta_id(params) + [campo("string", "motivo", params["motivo"], limite={"min": 3, "max": 200})]


RULES = {
    "/cuenta/abrir": val_open,
    "/cuenta/solicitar": val_open,
    "/cuenta/get": val_cuenta_id,
    "/cuenta/ajustar": val_adjust,
    "/cuenta/pagar": val_pay,
    "/cuenta/anular_pago": val_void_payment,
    "/cuenta/anular": val_void,
}
