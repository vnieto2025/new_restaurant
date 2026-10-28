from datetime import datetime
from Utils.tools import Tools, CustomException
from Querys.horario import HorarioQuerys
from Models.horario_model import TIPOS_HORARIO
from Models.zona_model import ZonaModel
from Models.carta_model import CartaModel

MAX_FRANJAS = 60


class Horario:
    """ Horario de atención del restaurante y de cada zona, y carta por franja (doc 08A, sección 4) """

    def __init__(self, db, ctx: dict):
        self.ctx = ctx
        self.tools = Tools()
        self.querys = HorarioQuerys(db, ctx)

    def get(self, data: dict):
        zona_id = self.zone_id(data)
        result = {"atencion": [self.format(f) for f in self.querys.franjas("atencion", zona_id)]}
        if zona_id:
            result["carta"] = [self.format(f) for f in self.querys.franjas("carta", zona_id)]
        return self.tools.output(200, "Horario.", result)

    def set(self, data: dict):

        tipo = data["tipo"]
        if tipo not in TIPOS_HORARIO:
            raise CustomException("El tipo de horario no es válido.")
        zona_id = self.zone_id(data)
        if tipo == "carta" and not zona_id:
            raise CustomException("La carta por franja se configura en cada zona.")
        permiso = "estructura.gestionar" if zona_id else "restaurante.configurar"
        if permiso not in self.ctx["permisos"]:
            raise CustomException("No tienes permiso para cambiar este horario.", 403)

        franjas = self.clean(data.get("franjas") or [], tipo)
        self.querys.replace(tipo, zona_id, franjas)
        self.querys.audit("horario_actualizado", "zona" if zona_id else "restaurante", zona_id or self.ctx["restaurante_id"],
                          despues={"tipo": tipo, "franjas": len(franjas)})

        msg = "Horario guardado." if franjas else "Sin horario: se reciben órdenes a cualquier hora." if tipo == "atencion" \
            else "Sin cartas por franja: la zona usa siempre su carta."
        return self.tools.output(200, msg, [self.format(f) for f in self.querys.franjas(tipo, zona_id)])

    def zone_id(self, data: dict):
        if not data.get("zona_id"):
            return None
        return self.querys.get_own(ZonaModel, data["zona_id"], "zona").id

    def clean(self, franjas: list, tipo: str):
        if len(franjas) > MAX_FRANJAS:
            raise CustomException(f"Máximo {MAX_FRANJAS} franjas.")
        result = []
        for franja in franjas:
            dia = int(franja["dia_semana"])
            if dia < 0 or dia > 6:
                raise CustomException("El día de la semana no es válido.")
            try:
                desde = datetime.strptime(franja["desde"], "%H:%M").time()
                hasta = datetime.strptime(franja["hasta"], "%H:%M").time()
            except (ValueError, TypeError):
                raise CustomException("Las horas deben tener el formato HH:MM.")
            if desde == hasta:
                raise CustomException("Una franja no puede empezar y terminar a la misma hora.")
            fila = {"dia_semana": dia, "desde": desde, "hasta": hasta, "carta_id": None}
            if tipo == "carta":
                fila["carta_id"] = self.querys.get_own(CartaModel, franja.get("carta_id"), "carta").id
            result.append(fila)
        return result

    def format(self, franja):
        return {"id": franja.id, "dia_semana": franja.dia_semana, "desde": franja.desde.strftime("%H:%M"),
                "hasta": franja.hasta.strftime("%H:%M"), "carta_id": franja.carta_id}
