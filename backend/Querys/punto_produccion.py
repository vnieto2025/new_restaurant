from Querys.base import Querys
from Models.punto_produccion_model import PuntoProduccionModel
from Models.orden_item_model import OrdenItemModel
from Utils.estados import NUEVO, EN_PROCESO, DESPACHADO
from sqlalchemy import func


class PuntoProduccionQuerys(Querys):

    def list_puntos(self, ids=None, incluir_inactivos=False):
        query = self.scoped(PuntoProduccionModel)
        if ids is not None:
            query = query.filter(PuntoProduccionModel.id.in_(ids or [0]))
        if not incluir_inactivos:
            query = query.filter(PuntoProduccionModel.activo.is_(True))
        return query.order_by(PuntoProduccionModel.id.asc()).all()

    def name_exists(self, nombre: str, exclude_id=None):
        query = self.scoped(PuntoProduccionModel).filter(func.lower(PuntoProduccionModel.nombre) == nombre.lower())
        if exclude_id:
            query = query.filter(PuntoProduccionModel.id != exclude_id)
        return query.first() is not None

    # Ítems que el punto todavía tiene en sus pestañas
    def count_items_abiertos(self, punto_id):
        return self.scoped(OrdenItemModel).filter(
            OrdenItemModel.punto_produccion_id == punto_id,
            OrdenItemModel.estado.in_([NUEVO, EN_PROCESO, DESPACHADO]),
        ).count()

    def format_punto(self, punto):
        return {
            "id": punto.id,
            "nombre": punto.nombre,
            "tipo": punto.tipo,
            "imprime_al_abrir": punto.imprime_al_abrir,
            "salta_en_proceso": punto.salta_en_proceso,
            "tiempo_objetivo": punto.tiempo_objetivo,
            "activo": punto.activo,
        }
