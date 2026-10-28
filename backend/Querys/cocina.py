from Querys.orden import OrdenQuerys
from Models.comanda_model import ComandaModel
from Models.orden_item_model import OrdenItemModel
from Models.orden_model import OrdenModel
from Models.mesa_model import MesaModel
from Models.zona_model import ZonaModel
from Models.usuario_model import UsuarioModel
from Utils.estados import NUEVO, EN_PROCESO, DESPACHADO, ETIQUETAS, estado_derivado
from Utils.tools import now


class CocinaQuerys(OrdenQuerys):

    # Comandas del punto con algo pendiente: por preparar, en proceso o listas sin entregar
    def open_commands(self, punto_id):
        abiertas = self.scoped(OrdenItemModel).with_entities(OrdenItemModel.comanda_id).filter(
            OrdenItemModel.punto_produccion_id == punto_id,
            OrdenItemModel.estado.in_([NUEVO, EN_PROCESO, DESPACHADO]),
        ).distinct()
        return self.scoped(ComandaModel).filter(
            ComandaModel.id.in_(abiertas)
        ).order_by(ComandaModel.creado_en.asc(), ComandaModel.id.asc()).all()

    def mark_received(self, comandas: list):
        sin_recibir = [c for c in comandas if c.recibida_en is None]
        for comanda in sin_recibir:
            comanda.recibida_en = now()
        if sin_recibir:
            self.db.commit()
        return sin_recibir

    def format_command(self, comanda):
        """ Tarjeta de la pantalla de producción, en el orden de prioridad del doc 18, sección 3 """
        orden = self.db.get(OrdenModel, comanda.orden_id)
        mesa = self.db.get(MesaModel, orden.mesa_id)
        zona = self.db.get(ZonaModel, orden.zona_id)
        mesero = self.db.get(UsuarioModel, orden.mesero_id) if orden.mesero_id else None
        items = self.items_of_comanda(comanda.id)
        modificadores = self.modifiers_of([i.id for i in items])
        estados = [i.estado for i in items]
        estado = estado_derivado(estados)

        return {
            "id": comanda.id,
            "orden_id": orden.id,
            "numero": orden.numero,
            "numero_texto": f"#{orden.numero:03d}",
            "mesa": mesa.nombre,
            "es_externa": mesa.tipo == "externa",
            "cliente_nombre": orden.cliente_nombre,
            "zona": zona.nombre,
            "canal": orden.canal,
            "mesero": mesero.nombre if mesero else None,
            "notas": orden.notas,
            "es_adicion": comanda.es_adicion,
            # Hubo cancelaciones después de enviarla: la cocina debe notarlo (RG-21)
            "modificada": any(i.estado == "cancelado" for i in items),
            "estado": estado,
            "pestana": "listos" if estado == "lista" else "en_proceso",
            "creado_en": comanda.creado_en,
            "impresa_en": comanda.impresa_en,
            "items": [{
                "id": i.id,
                "nombre": i.nombre_producto,
                "cantidad": i.cantidad,
                "nota": i.nota,
                "modificadores": [m["nombre"] for m in modificadores.get(i.id, [])],
                "estado": i.estado,
                "estado_etiqueta": ETIQUETAS.get(i.estado, i.estado),
                "motivo_cancelacion": i.motivo_cancelacion,
            } for i in items],
        }
