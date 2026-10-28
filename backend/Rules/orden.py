from Rules.campo import campo, items_orden
from Rules.domicilio import datos_entrega


def val_menu(params):
    return [campo("int", "mesa", params["mesa_id"])]


def val_create(params):
    return [
        campo("int", "mesa", params["mesa_id"]),
        campo("string", "clave de idempotencia", params["clave_idempotencia"], limite={"min": 8, "max": 80}),
        campo("string", "notas", params.get("notas"), False, limite={"min": 1, "max": 300}),
        campo("string", "nombre del cliente", params.get("cliente_nombre"), False, limite={"min": 2, "max": 100}),
        campo("string", "teléfono del cliente", params.get("cliente_telefono"), False, limite={"min": 7, "max": 30}),
        campo("bool", "acepta tratamiento de datos", params.get("acepta_datos"), False),
    ] + items_orden(params["items"]) + datos_entrega(params.get("entrega"))


def val_add_items(params):
    return [
        campo("int", "orden", params["orden_id"]),
        campo("string", "clave de idempotencia", params["clave_idempotencia"], limite={"min": 8, "max": 80}),
    ] + items_orden(params["items"])


def val_orden_id(params):
    return [campo("int", "orden", params["orden_id"])]


def val_list(params):
    return [
        campo("int", "zona", params.get("zona_id"), False),
        campo("int", "mesa", params.get("mesa_id"), False),
        campo("opcion", "vista", params.get("vista"), False, opciones=["activas", "jornada"]),
    ]


def val_reject(params):
    return [
        campo("int", "orden", params["orden_id"]),
        campo("string", "motivo", params["motivo"], limite={"min": 3, "max": 200}),
    ]


def val_cancel_item(params):
    return [
        campo("int", "ítem", params["orden_item_id"]),
        campo("string", "motivo", params["motivo"], limite={"min": 3, "max": 200}),
        campo("opcion", "tipo", params.get("tipo"), False, opciones=["cancelacion", "perdida"]),
    ]


def val_deliver(params):
    return [
        campo("int", "orden", params.get("orden_id"), False),
        campo("list", "ítems", params.get("orden_item_ids"), False),
    ]


RULES = {
    "/orden/carta": val_menu,
    "/orden/create": val_create,
    "/orden/agregar_items": val_add_items,
    "/orden/get": val_orden_id,
    "/orden/list": val_list,
    "/orden/aprobar": val_orden_id,
    "/orden/rechazar": val_reject,
    "/orden/cancelar_item": val_cancel_item,
    "/orden/entregar": val_deliver,
    "/orden/tirilla": val_orden_id,
}
