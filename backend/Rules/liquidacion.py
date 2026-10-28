from Rules.campo import campo
from Models.liquidacion_model import TIPOS_LIQUIDACION
from Models.liquidacion_config_model import (PERIODOS, MODELOS_PROPINA, METODOS_REPARTO, DESTINOS_PROPINA_DOMICILIO,
                                             MODELOS_PAGO_DOMICILIO)
from Class.Liquidacion import MEDIOS_PAGO


def val_tipo(params):
    return [campo("opcion", "tipo", params["tipo"], opciones=TIPOS_LIQUIDACION),
            campo("date", "fecha", params.get("fecha"), False)]


def val_liquidacion_id(params):
    return [campo("int", "liquidación", params["liquidacion_id"])]


def val_config(params):
    return [
        campo("opcion", "periodo", params.get("periodo"), False, opciones=PERIODOS),
        campo("opcion", "modelo de propinas", params.get("modelo"), False, opciones=MODELOS_PROPINA),
        campo("int", "porcentaje individual", params.get("porcentaje_individual"), False),
        campo("opcion", "método de reparto", params.get("metodo"), False, opciones=METODOS_REPARTO),
        campo("bool", "reparto por zona", params.get("por_zona"), False),
        campo("float", "retención", params.get("retencion"), False),
        campo("opcion", "propina de domicilios", params.get("propina_domicilio"), False, opciones=DESTINOS_PROPINA_DOMICILIO),
        campo("opcion", "pago a domiciliarios", params.get("pago_domicilio"), False, opciones=MODELOS_PAGO_DOMICILIO),
        campo("float", "porcentaje del envío", params.get("pago_porcentaje"), False),
        campo("int", "base por entrega", params.get("pago_base"), False),
    ]


RULES = {
    "/liquidacion/config/save": val_config,
    "/liquidacion/list": lambda p: [campo("opcion", "tipo", p["tipo"], opciones=TIPOS_LIQUIDACION)],
    "/liquidacion/periodo": val_tipo,
    "/liquidacion/calcular": lambda p: val_tipo(p) + [campo("int", "liquidación", p.get("liquidacion_id"), False)],
    "/liquidacion/get": val_liquidacion_id,
    "/liquidacion/linea": lambda p: [
        campo("int", "línea", p["linea_id"]), campo("float", "horas", p.get("horas"), False),
        campo("bool", "participa", p.get("participa"), False),
        campo("string", "motivo", p.get("motivo"), False, limite={"min": 3, "max": 200})],
    "/liquidacion/ajustar": lambda p: val_liquidacion_id(p) + [
        campo("int", "línea", p["linea_id"]), campo("string", "valor", str(p["valor"]), limite={"min": 1, "max": 12}),
        campo("string", "motivo", p["motivo"], limite={"min": 3, "max": 200})],
    "/liquidacion/descartar": val_liquidacion_id,
    "/liquidacion/aprobar": val_liquidacion_id,
    "/liquidacion/pagar": lambda p: [
        campo("int", "línea", p["linea_id"]), campo("opcion", "medio de pago", p["medio_pago"], opciones=MEDIOS_PAGO),
        campo("string", "referencia", p.get("referencia"), False, limite={"min": 1, "max": 60})],
}
