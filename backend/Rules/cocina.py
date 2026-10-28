from Rules.campo import campo


def val_commands(params):
    return [campo("int", "punto de producción", params["punto_produccion_id"])]


def val_comanda_id(params):
    return [campo("int", "comanda", params["comanda_id"])]


def val_dispatch(params):
    return val_comanda_id(params) + [campo("list", "ítems", params.get("orden_item_ids"), False)]


def val_reopen(params):
    return val_comanda_id(params) + [campo("string", "motivo", params["motivo"], limite={"min": 3, "max": 200})]


def val_sold_out(params):
    return [
        campo("int", "ítem", params["orden_item_id"]),
        campo("string", "motivo", params.get("motivo"), False, limite={"min": 3, "max": 200}),
    ]


RULES = {
    "/cocina/comandas": val_commands,
    "/cocina/abrir": val_comanda_id,
    "/cocina/despachar": val_dispatch,
    "/cocina/reabrir": val_reopen,
    "/cocina/agotado": val_sold_out,
    "/cocina/tirilla": val_comanda_id,
}
