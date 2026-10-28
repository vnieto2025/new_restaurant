from Rules.campo import campo


def val_list(params):
    return [campo("int", "zona", params.get("zona_id"), False)]


def val_regenerate(params):
    return [campo("int", "mesa", params["mesa_id"])]


RULES = {
    "/qr/list": val_list,
    "/qr/regenerar": val_regenerate,
}
