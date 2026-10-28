from Rules.campo import campo


def val_zona(params):
    return [
        campo("int", "zona de envío", params.get("zona_envio_id"), False),
        campo("string", "nombre", params["nombre"], limite={"min": 2, "max": 60}),
        campo("string", "barrios", params.get("barrios"), False, limite={"min": 2, "max": 500}),
        campo("int", "tarifa", params.get("tarifa"), False),
        campo("int", "pago al domiciliario", params.get("pago_domiciliario"), False),
        campo("int", "pedido mínimo", params.get("pedido_minimo"), False),
        campo("bool", "activa", params.get("activo"), False),
    ]


def val_domiciliario(params):
    return [
        campo("int", "domiciliario", params.get("domiciliario_id"), False),
        campo("string", "nombre", params["nombre"], limite={"min": 2, "max": 100}),
        campo("string", "código", params["codigo"], limite={"min": 1, "max": 10}),
        campo("string", "documento", params.get("documento"), False, limite={"min": 3, "max": 30}),
        campo("string", "teléfono", params.get("telefono"), False, limite={"min": 7, "max": 20}),
        campo("opcion", "vínculo", params.get("vinculo"), False, opciones=["propio", "independiente"]),
        campo("int", "usuario", params.get("usuario_id"), False),
    ]


def val_entrega_id(params):
    return [campo("int", "entrega", params["entrega_id"])]


# Datos de entrega al crear una orden de domicilio (RN-DOM-01)
def datos_entrega(entrega):
    if not entrega:
        return []
    return [
        campo("int", "zona de envío", entrega["zona_envio_id"]),
        campo("string", "dirección", entrega["direccion"], limite={"min": 5, "max": 200}),
        campo("string", "teléfono de entrega", entrega.get("telefono"), False, limite={"min": 7, "max": 20}),
        campo("string", "barrio", entrega.get("barrio"), False, limite={"min": 2, "max": 80}),
        campo("string", "indicaciones", entrega.get("indicaciones"), False, limite={"min": 1, "max": 250}),
        campo("bool", "guardar dirección", entrega.get("guardar_direccion"), False),
        campo("opcion", "forma de pago", entrega.get("forma_pago"), False, opciones=["contra_entrega", "en_linea"]),
    ]


def val_web(params):
    return [
        campo("bool", "activo", params["activo"]),
        campo("bool", "aprobación", params.get("aprobacion"), False),
        campo("string", "mensaje", params.get("mensaje"), False, limite={"min": 2, "max": 200}),
    ]


RULES = {
    "/domicilio/zona/save": val_zona,
    "/domicilio/zona/list": lambda p: [campo("bool", "todas", p.get("todos"), False)],
    "/domicilio/domiciliario/save": val_domiciliario,
    "/domicilio/web/save": val_web,
    "/domicilio/domiciliario/list": lambda p: [campo("bool", "todos", p.get("todos"), False)],
    "/domicilio/domiciliario/change_status": lambda p: [campo("int", "domiciliario", p["domiciliario_id"]),
                                                        campo("bool", "activo", p["activo"])],
    "/entrega/asignar": lambda p: val_entrega_id(p) + [campo("int", "domiciliario", p["domiciliario_id"])],
    "/entrega/salir": val_entrega_id,
    "/entrega/entregar": val_entrega_id,
    "/entrega/fallida": lambda p: val_entrega_id(p) + [
        campo("string", "motivo", p["motivo"], limite={"min": 3, "max": 200}),
        campo("opcion", "decisión", p["decision"], opciones=["reintento", "cancelacion", "perdida"])],
    "/entrega/rendir": lambda p: [
        campo("int", "domiciliario", p["domiciliario_id"]), campo("int", "valor entregado", p["entregado"]),
        campo("string", "notas", p.get("notas"), False, limite={"min": 1, "max": 200})],
}
