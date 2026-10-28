from Rules.campo import campo
from Models.movimiento_caja_model import TIPOS_MOVIMIENTO
from Models.medio_pago_model import TIPOS_MEDIO


def val_open_shift(params):
    return [campo("int", "fondo inicial", params.get("fondo_inicial"), False)]


def val_close_shift(params):
    return [
        campo("int", "efectivo contado", params["efectivo_contado"]),
        campo("string", "observación", params.get("observacion"), False, limite={"min": 1, "max": 250}),
        campo("bool", "confirmar pendientes", params.get("confirmar_pendientes"), False),
    ]


def val_turno_id(params):
    return [campo("int", "turno", params["turno_id"])]


def val_movement(params):
    return [
        campo("opcion", "tipo", params["tipo"], opciones=TIPOS_MOVIMIENTO),
        campo("int", "monto", params["monto"]),
        campo("string", "concepto", params["concepto"], limite={"min": 3, "max": 200}),
    ]


def val_payment_method(params):
    return [
        campo("int", "medio de pago", params.get("medio_pago_id"), False),
        campo("string", "nombre", params["nombre"], limite={"min": 2, "max": 40}),
        campo("opcion", "tipo", params.get("tipo"), False, opciones=TIPOS_MEDIO),
        campo("bool", "pide referencia", params.get("pide_referencia"), False),
        campo("bool", "activo", params.get("activo"), False),
    ]


RULES = {
    "/caja/turno/abrir": val_open_shift,
    "/caja/turno/cerrar": val_close_shift,
    "/caja/turno/get": val_turno_id,
    "/caja/movimiento/create": val_movement,
    "/caja/medio_pago/save": val_payment_method,
}
