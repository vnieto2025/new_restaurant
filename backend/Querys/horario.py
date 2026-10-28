from Querys.base import Querys
from Models.horario_model import HorarioModel
from Models.restaurante_model import RestauranteModel
from Utils.horarios import abierto, franja_actual, proxima_apertura


class HorarioQuerys(Querys):

    def franjas(self, tipo: str, zona_id=None):
        query = self.scoped(HorarioModel).filter(HorarioModel.tipo == tipo)
        query = query.filter(HorarioModel.zona_id == zona_id) if zona_id else query.filter(HorarioModel.zona_id.is_(None))
        return query.order_by(HorarioModel.dia_semana.asc(), HorarioModel.desde.asc()).all()

    def replace(self, tipo: str, zona_id, franjas: list):
        query = self.scoped(HorarioModel).filter(HorarioModel.tipo == tipo)
        query = query.filter(HorarioModel.zona_id == zona_id) if zona_id else query.filter(HorarioModel.zona_id.is_(None))
        query.delete(synchronize_session=False)
        for franja in franjas:
            self.insert_data(HorarioModel, {**franja, "tipo": tipo, "zona_id": zona_id}, commit=False)
        self.db.flush()

    def zona_horaria(self):
        restaurante = self.db.get(RestauranteModel, self.restaurante_id)
        return restaurante.zona_horaria

    def reception_status(self, zona):
        """ ¿Se reciben órdenes ahora en esta zona? Devuelve (abierto, mensaje).
            Primero el horario del restaurante y luego el de la zona (doc 08A). """
        tz = self.zona_horaria()
        restaurante = self.franjas("atencion")
        if not abierto(restaurante, tz):
            proxima = proxima_apertura(restaurante, tz)
            return False, f"Estamos cerrados. Abrimos {proxima}." if proxima else "Estamos cerrados."
        propias = self.franjas("atencion", zona.id)
        if not abierto(propias, tz):
            proxima = proxima_apertura(propias, tz)
            return False, f"{zona.nombre} no está atendiendo ahora. Abre {proxima}." if proxima else f"{zona.nombre} no está atendiendo ahora."
        return True, None

    # Carta de la zona en este momento: la de la franja vigente o la de siempre
    def current_menu(self, zona):
        franja = franja_actual(self.franjas("carta", zona.id), self.zona_horaria())
        return franja.carta_id if franja and franja.carta_id else zona.carta_id
