from Rules.campo import campo
from Models.restaurante_model import TIPOS_RESTAURANTE


def campos_restaurante(params):
    return [
        campo("string", "nombre del restaurante", params["nombre"], limite={"min": 2, "max": 150}),
        campo("opcion", "tipo de restaurante", params.get("tipo"), False, opciones=TIPOS_RESTAURANTE),
        campo("string", "dirección", params.get("direccion"), False, limite={"min": 3, "max": 200}),
        campo("string", "teléfono", params.get("telefono"), False, limite={"min": 7, "max": 30}),
        campo("string", "zona horaria", params.get("zona_horaria"), False),
        campo("hora", "hora de inicio de jornada", params.get("hora_inicio_jornada"), False),
        campo("string", "mensaje de la carta", params.get("mensaje_carta"), False, limite={"min": 1, "max": 250}),
        campo("int", "propina sugerida", params.get("propina_sugerida"), False),
        campo("bool", "reiniciar agotados", params.get("reiniciar_agotados"), False),
        campo("string", "aviso de tratamiento de datos", params.get("aviso_datos"), False, limite={"min": 20, "max": 600}),
        campo("string", "enlace a la política de datos", params.get("politica_url"), False, limite={"min": 8, "max": 250}),
    ]


def val_change_status(params):
    return [
        campo("opcion", "estado", params["estado"], opciones=["activo", "pausado", "cerrado"]),
        campo("string", "mensaje de la carta", params.get("mensaje_carta"), False, limite={"min": 1, "max": 250}),
    ]


RULES = {
    "/restaurante/update": campos_restaurante,
    "/restaurante/change_status": val_change_status,
    "/restaurante/puesta_en_marcha/marcar": lambda p: [campo("string", "paso", p["paso"], limite={"min": 2, "max": 20}),
                                                       campo("bool", "hecho", p["hecho"])],
}
