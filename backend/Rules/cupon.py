from Rules.campo import campo
from Models.cupon_model import TIPOS_CUPON


def val_cupon_id(params):
    return [campo("int", "cupón", params["cupon_id"])]


def val_list(params):
    return [
        campo("opcion", "estado", params.get("estado"), False, opciones=["activo", "pausado", "anulado"]),
        campo("string", "búsqueda", params.get("buscar"), False, limite={"min": 1, "max": 60}),
        campo("bool", "plantillas", params.get("plantillas"), False),
        campo("bool", "vigentes", params.get("vigentes"), False),
        campo("int", "cliente", params.get("cliente_id"), False),
    ]


def val_save(params):
    reglas = [
        campo("int", "cupón", params.get("cupon_id"), False),
        campo("string", "código", params.get("codigo"), False, limite={"min": 3, "max": 30}),
        campo("string", "nombre", params["nombre"], limite={"min": 3, "max": 100}),
        campo("string", "descripción", params.get("descripcion"), False, limite={"min": 3, "max": 200}),
        campo("opcion", "tipo", params["tipo"], opciones=TIPOS_CUPON),
        campo("int", "valor", params.get("valor"), False),
        campo("int", "tope", params.get("tope"), False),
        campo("int", "producto", params.get("producto_id"), False),
        campo("date", "fecha de inicio", params.get("inicia"), False),
        campo("date", "fecha de fin", params.get("termina"), False),
        campo("list", "canales", params.get("canales"), False),
        campo("list", "zonas", params.get("zonas"), False),
        campo("list", "productos", params.get("productos"), False),
        campo("list", "categorías", params.get("categorias"), False),
        campo("list", "días", params.get("dias"), False),
        campo("hora", "hora de inicio", params.get("hora_desde"), False),
        campo("hora", "hora de fin", params.get("hora_hasta"), False),
        campo("int", "compra mínima", params.get("monto_minimo"), False),
        campo("int", "usos totales", params.get("usos_maximos"), False),
        campo("int", "usos por cliente", params.get("usos_por_cliente"), False),
        campo("int", "cliente", params.get("cliente_id"), False),
        campo("bool", "acumulable", params.get("acumulable"), False),
        campo("bool", "plantilla", params.get("plantilla"), False),
        campo("int", "compra que emite el cupón", params.get("emitir_desde"), False),
        campo("int", "días de validez", params.get("dias_validez"), False),
    ]
    return reglas


def val_status(params):
    return val_cupon_id(params) + [
        campo("opcion", "estado", params["estado"], opciones=["activo", "pausado", "anulado"]),
        campo("string", "motivo", params.get("motivo"), False, limite={"min": 3, "max": 200}),
    ]


def val_results(params):
    return [campo("date", "desde", params.get("desde"), False), campo("date", "hasta", params.get("hasta"), False)]


def val_apply(params):
    return [
        campo("int", "cuenta", params["cuenta_id"]),
        campo("string", "código del cupón", params["codigo"], limite={"min": 3, "max": 30}),
        campo("int", "cliente", params.get("cliente_id"), False),
    ]


RULES = {
    "/cupon/list": val_list,
    "/cupon/get": val_cupon_id,
    "/cupon/save": val_save,
    "/cupon/change_status": val_status,
    "/cupon/enviar": val_cupon_id,
    "/cupon/resultados": val_results,
    "/cupon/aplicar": val_apply,
    "/cupon/quitar": lambda p: [campo("int", "cuenta", p["cuenta_id"]), campo("int", "cupón aplicado", p["redencion_id"])],
    "/cupon/cliente": lambda p: [campo("int", "cuenta", p["cuenta_id"]), campo("int", "cliente", p.get("cliente_id"), False)],
}
