from Utils.tools import Tools, CustomException, clean_text
from Querys.punto_produccion import PuntoProduccionQuerys
from Models.punto_produccion_model import PuntoProduccionModel, TIPOS_PUNTO


class PuntoProduccion:

    def __init__(self, db, ctx: dict):
        self.ctx = ctx
        self.tools = Tools()
        self.querys = PuntoProduccionQuerys(db, ctx)

    # Un usuario de cocina solo ve sus puntos
    def list(self, data: dict):

        incluir_inactivos = data.get("todos") is True and "estructura.gestionar" in self.ctx["permisos"]
        puntos = self.querys.list_puntos(self.ctx.get("puntos"), incluir_inactivos)
        result = [self.querys.format_punto(punto) for punto in puntos]

        msg = "Listado de puntos de producción." if result else "Aún no hay puntos de producción."
        return self.tools.output(200, msg, result)

    def create(self, data: dict):

        fields = self.clean_data(data)
        if self.querys.name_exists(fields["nombre"]):
            raise CustomException("Ya existe un punto de producción con ese nombre.")

        punto_id = self.querys.insert_data(PuntoProduccionModel, fields)
        punto = self.querys.get_own(PuntoProduccionModel, punto_id, "punto de producción")
        return self.tools.output(201, "Punto de producción creado.", self.querys.format_punto(punto))

    # Las órdenes en curso conservan el destino que tenían (doc 19, sección 3)
    def update(self, data: dict):

        punto = self.querys.get_own(PuntoProduccionModel, data["punto_produccion_id"], "punto de producción")
        fields = self.clean_data(data)
        if self.querys.name_exists(fields["nombre"], exclude_id=punto.id):
            raise CustomException("Ya existe otro punto de producción con ese nombre.")

        punto = self.querys.update_data(PuntoProduccionModel, punto.id, fields, "punto de producción")
        return self.tools.output(200, "Punto de producción actualizado.", self.querys.format_punto(punto))

    # No se desactiva con comandas abiertas sin resolver (doc 19, sección 8)
    def change_status(self, data: dict):

        punto = self.querys.get_own(PuntoProduccionModel, data["punto_produccion_id"], "punto de producción")
        activo = data["activo"] is True

        if not activo and self.querys.count_items_abiertos(punto.id):
            raise CustomException("El punto tiene comandas sin entregar. Resuélvalas antes de desactivarlo.")

        self.querys.update_data(PuntoProduccionModel, punto.id, {"activo": activo}, "punto de producción")
        return self.tools.output(200, "Punto activado." if activo else "Punto desactivado.")

    def clean_data(self, data: dict):

        tipo = data.get("tipo") or "cocina"
        if tipo not in TIPOS_PUNTO:
            raise CustomException("El tipo de punto de producción no es válido.")

        tiempo = data.get("tiempo_objetivo")
        tiempo = int(tiempo) if tiempo not in [None, ""] else None
        if tiempo is not None and tiempo <= 0:
            raise CustomException("El tiempo objetivo debe ser mayor a cero.")

        return {
            "nombre": clean_text(data["nombre"]),
            "tipo": tipo,
            "imprime_al_abrir": data.get("imprime_al_abrir") is True,
            "salta_en_proceso": data.get("salta_en_proceso") is True,
            "tiempo_objetivo": tiempo,
        }
