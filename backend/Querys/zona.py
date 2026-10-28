from Querys.base import Querys
from Models.zona_model import ZonaModel
from Models.mesa_model import MesaModel
from Models.carta_model import CartaModel
from Models.punto_produccion_model import PuntoProduccionModel
from Models.sesion_mesa_model import SesionMesaModel
from sqlalchemy import func


class ZonaQuerys(Querys):

    def list_zonas(self, ids=None, incluir_inactivas=False):
        query = self.scoped(ZonaModel)
        if ids is not None:
            query = query.filter(ZonaModel.id.in_(ids or [0]))
        if not incluir_inactivas:
            query = query.filter(ZonaModel.activo.is_(True))
        return query.order_by(ZonaModel.orden.asc(), ZonaModel.id.asc()).all()

    def name_exists(self, nombre: str, exclude_id=None):
        query = self.scoped(ZonaModel).filter(func.lower(ZonaModel.nombre) == nombre.lower())
        if exclude_id:
            query = query.filter(ZonaModel.id != exclude_id)
        return query.first() is not None

    def count_mesas(self, zona_id):
        return self.scoped(MesaModel).filter(
            MesaModel.zona_id == zona_id, MesaModel.activo.is_(True), MesaModel.tipo == "normal"
        ).count()

    def count_sesiones_abiertas(self, zona_id):
        return self.scoped(SesionMesaModel).filter(
            SesionMesaModel.zona_id == zona_id, SesionMesaModel.estado == "abierta"
        ).count()

    def get_carta(self, carta_id):
        return self.get_own(CartaModel, carta_id, "carta") if carta_id else None

    def get_punto(self, punto_id):
        return self.get_own(PuntoProduccionModel, punto_id, "punto de producción") if punto_id else None

    def format_zona(self, zona):
        carta = self.db.get(CartaModel, zona.carta_id) if zona.carta_id else None
        punto = self.db.get(PuntoProduccionModel, zona.punto_produccion_id) if zona.punto_produccion_id else None
        return {
            "id": zona.id,
            "nombre": zona.nombre,
            "codigo": zona.codigo,
            "orden": zona.orden,
            "carta_id": zona.carta_id,
            "carta": carta.nombre if carta else None,
            "punto_produccion_id": zona.punto_produccion_id,
            "punto_produccion": punto.nombre if punto else None,
            "modo_qr": zona.modo_qr,
            "es_mostrador": zona.es_mostrador,
            "activo": zona.activo,
            "mesas": self.count_mesas(zona.id),
        }
