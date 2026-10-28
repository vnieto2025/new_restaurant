from Utils.tools import Tools, CustomException, clean_text
from Querys.zona import ZonaQuerys
from Models.zona_model import ZonaModel, MODOS_QR


class Zona:

    def __init__(self, db, ctx: dict):
        self.ctx = ctx
        self.tools = Tools()
        self.querys = ZonaQuerys(db, ctx)

    # Function for list zones. Un mesero solo ve las suyas
    def list(self, data: dict):

        incluir_inactivas = data.get("todas") is True and "estructura.gestionar" in self.ctx["permisos"]
        zonas = self.querys.list_zonas(self.ctx.get("zonas"), incluir_inactivas)
        result = [self.querys.format_zona(zona) for zona in zonas]

        msg = "Listado de zonas." if result else "Aún no hay zonas."
        return self.tools.output(200, msg, result)

    # Function for create a zone
    def create(self, data: dict):

        fields = self.clean_data(data)
        if self.querys.name_exists(fields["nombre"]):
            raise CustomException("Ya existe una zona con ese nombre.")

        zona_id = self.querys.insert_data(ZonaModel, fields)
        zona = self.querys.get_own(ZonaModel, zona_id, "zona")
        return self.tools.output(201, "Zona creada.", self.querys.format_zona(zona))

    # Function for update a zone. Las órdenes ya creadas no cambian (RN-ZON-05)
    def update(self, data: dict):

        zona = self.querys.get_own(ZonaModel, data["zona_id"], "zona")
        fields = self.clean_data(data)
        if self.querys.name_exists(fields["nombre"], exclude_id=zona.id):
            raise CustomException("Ya existe otra zona con ese nombre.")

        zona = self.querys.update_data(ZonaModel, zona.id, fields, "zona")
        return self.tools.output(200, "Zona actualizada.", self.querys.format_zona(zona))

    # Function for change status (RN-ZON-02)
    def change_status(self, data: dict):

        zona = self.querys.get_own(ZonaModel, data["zona_id"], "zona")
        activo = data["activo"] is True

        if not activo:
            if zona.es_mostrador:
                raise CustomException("La zona de mostrador no se puede desactivar: atiende las órdenes externas.")
            if self.querys.count_sesiones_abiertas(zona.id):
                raise CustomException("La zona tiene mesas abiertas. Ciérrelas antes de desactivarla.")

        self.querys.update_data(ZonaModel, zona.id, {"activo": activo}, "zona")
        return self.tools.output(200, "Zona activada." if activo else "Zona desactivada.")

    def clean_data(self, data: dict):

        modo_qr = data.get("modo_qr") or "aprobacion"
        if modo_qr not in MODOS_QR:
            raise CustomException("El modo de aceptación de QR no es válido.")

        carta = self.querys.get_carta(data.get("carta_id"))
        punto = self.querys.get_punto(data.get("punto_produccion_id"))
        return {
            "nombre": clean_text(data["nombre"]),
            "codigo": clean_text(data.get("codigo")),
            "orden": int(data.get("orden") or 0),
            "carta_id": carta.id if carta else None,
            "punto_produccion_id": punto.id if punto else None,
            "modo_qr": modo_qr,
        }
