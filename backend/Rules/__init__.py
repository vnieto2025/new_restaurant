from Utils.validator import Validator
from Rules import (
    auth, plataforma, restaurante, usuario, zona, mesa, punto_produccion, qr,
    categoria, producto, carta, orden, cocina, publico, auditoria, modificador, caja, cuenta, dispositivo, horario, reporte, cliente,
    facturacion, inventario, compra, domicilio, notificacion, pago_linea, cupon, liquidacion, pos,
)

# Cada módulo declara sus reglas en Rules/<modulo>.py como RULES = {path: función}
MODULES = [
    auth, plataforma, restaurante, usuario, zona, mesa, punto_produccion, qr,
    categoria, producto, carta, orden, cocina, publico, auditoria, modificador, caja, cuenta, dispositivo, horario, reporte, cliente,
    facturacion, inventario, compra, domicilio, notificacion, pago_linea, cupon, liquidacion, pos,
]

PATHS = {}
for module in MODULES:
    PATHS.update(module.RULES)


class Rules:
    """ Esta clase se encarga de validar los datos de entrada de la API
        y si hay un error, lanza una excepcion """

    val = Validator()

    def __init__(self, path: str, params: dict):
        # Se obtiene la funcion a ejecutar
        func = PATHS.get(path, None)
        if func:
            # Se ejecuta la funcion para obtener las reglas de validacion
            validacion_dict = func(params)

            # Se valida la datas
            self.val.validacion_datos_entrada(validacion_dict)
