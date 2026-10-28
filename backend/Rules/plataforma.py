from Rules.campo import campo
from Rules.restaurante import campos_restaurante
from Models.empresa_model import ESTADOS_EMPRESA
from Models.contrato_model import ESTADOS_CONTRATO
from Models.pago_suscripcion_model import MEDIOS_SUSCRIPCION


def val_create_empresa(params):
    admin = params["admin"]
    return [
        campo("string", "nombre comercial", params["nombre_comercial"], limite={"min": 2, "max": 150}),
        campo("string", "razón social", params.get("razon_social"), False, limite={"min": 2, "max": 200}),
        campo("string", "documento fiscal", params.get("documento_fiscal"), False, limite={"min": 3, "max": 30}),
        campo("email", "correo de contacto", params.get("contacto_correo"), False),
        campo("string", "usuario administrador", admin["usuario"], limite={"min": 3, "max": 60}),
        campo("string", "nombre del administrador", admin["nombre"], limite={"min": 2, "max": 150}),
        campo("string", "contraseña del administrador", admin["password"]),
        campo("list", "módulos", params.get("modulos"), False),
        campo("opcion", "estado del contrato", params.get("estado_contrato"), False, opciones=ESTADOS_CONTRATO),
    ] + campos_restaurante(params["restaurante"])


def val_create_restaurante(params):
    return [
        campo("int", "empresa", params["empresa_id"]),
        campo("list", "módulos", params.get("modulos"), False),
    ] + campos_restaurante(params["restaurante"])


def val_change_status_empresa(params):
    return [
        campo("int", "empresa", params["empresa_id"]),
        campo("opcion", "estado", params["estado"], opciones=ESTADOS_EMPRESA),
    ]


def val_update_contrato(params):
    return [
        campo("int", "restaurante", params["restaurante_id"]),
        campo("opcion", "estado", params["estado"], opciones=ESTADOS_CONTRATO),
        campo("list", "módulos", params.get("modulos"), False),
        campo("date", "fecha de fin", params.get("fecha_fin"), False),
        campo("int", "mensualidad", params.get("mensualidad"), False),
        campo("date", "próximo vencimiento", params.get("proximo_vencimiento"), False),
        campo("string", "notas comerciales", params.get("notas_comerciales"), False, limite={"min": 1, "max": 300}),
    ]


RULES = {
    "/plataforma/empresa/create": val_create_empresa,
    "/plataforma/empresa/change_status": val_change_status_empresa,
    "/plataforma/restaurante/create": val_create_restaurante,
    "/plataforma/contrato/update": val_update_contrato,
    "/plataforma/suscripcion/pagos": lambda p: [campo("int", "restaurante", p["restaurante_id"])],
    "/plataforma/suscripcion/pagar": lambda p: [
        campo("int", "restaurante", p["restaurante_id"]), campo("int", "valor", p["valor"]),
        campo("int", "meses", p.get("meses"), False), campo("date", "fecha", p.get("fecha"), False),
        campo("opcion", "medio", p["medio"], opciones=MEDIOS_SUSCRIPCION),
        campo("string", "referencia", p.get("referencia"), False, limite={"min": 1, "max": 60}),
        campo("string", "factura", p.get("factura"), False, limite={"min": 1, "max": 40})],
}
