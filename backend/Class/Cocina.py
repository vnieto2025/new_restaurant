from Utils.tools import Tools, CustomException, clean_text, now
from Utils.estados import NUEVO, EN_PROCESO, DESPACHADO, ENTREGADO, CANCELADO
from Utils.notificaciones import notificar
from Utils.mensajeria import cola_mensajes
from Utils.realtime import realtime, channels_for
from Querys.cocina import CocinaQuerys
from Models.comanda_model import ComandaModel
from Models.orden_model import OrdenModel
from Models.orden_item_model import OrdenItemModel
from Models.producto_model import ProductoModel
from Models.punto_produccion_model import PuntoProduccionModel


class Cocina:
    """ Pantalla de producción (KDS) de cocina, bar o cualquier punto (doc 18).
        Cada acción se confirma con el servidor antes de verse como hecha. """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = CocinaQuerys(db, ctx)

    # Las dos pestañas de la pantalla. Pedirlas cuenta como recibir las comandas (doc 17)
    def commands(self, data: dict):

        punto = self.get_point(data["punto_produccion_id"])
        comandas = self.querys.open_commands(punto.id)
        recibidas = self.querys.mark_received(comandas)

        tarjetas = [self.querys.format_command(c) for c in comandas]
        for orden_id in {c.orden_id for c in recibidas}:
            orden = self.db.get(OrdenModel, orden_id)
            realtime.publish(orden.restaurante_id, channels_for(orden.zona_id),
                             {"tipo": "comanda.recibida", "orden_id": orden.id})

        return self.tools.output(200, "Comandas del punto.", {
            "punto": {
                "id": punto.id,
                "nombre": punto.nombre,
                "salta_en_proceso": punto.salta_en_proceso,
                "imprime_al_abrir": punto.imprime_al_abrir,
                "tiempo_objetivo": punto.tiempo_objetivo,
            },
            "en_proceso": [t for t in tarjetas if t["pestana"] == "en_proceso"],
            "listos": [t for t in tarjetas if t["pestana"] == "listos"],
            "servidor_en": now(),
        })

    # Abrir: azul claro -> amarillo. Si el punto salta "en proceso", va directo a Listos.
    def open(self, data: dict):

        comanda, punto, items = self.get_command(data["comanda_id"])
        nuevos = [i for i in items if i.estado == NUEVO]
        if not nuevos:
            raise CustomException("La comanda ya estaba abierta.", 409)

        destino = DESPACHADO if punto.salta_en_proceso else EN_PROCESO
        for item in nuevos:
            self.querys.transition(item, destino)
        self.db.commit()

        self.notify(comanda, "comanda.abierta" if destino == EN_PROCESO else "comanda.despachada")
        tarjeta = self.querys.format_command(comanda)
        tarjeta["imprimir"] = punto.imprime_al_abrir
        return self.tools.output(200, "Comanda en proceso.", tarjeta)

    # Despachar: toda la comanda o algunos ítems (despacho parcial, doc 18)
    def dispatch(self, data: dict):

        comanda, punto, items = self.get_command(data["comanda_id"])
        origen = [EN_PROCESO, NUEVO] if punto.salta_en_proceso else [EN_PROCESO]
        elegidos = [int(i) for i in data.get("orden_item_ids") or []]

        por_despachar = [i for i in items if i.estado in origen and (not elegidos or i.id in elegidos)]
        if not por_despachar:
            if any(i.estado == NUEVO for i in items):
                raise CustomException("Abra la comanda antes de despacharla.", 409)
            raise CustomException("No hay ítems por despachar en esta comanda.", 409)

        for item in por_despachar:
            self.querys.transition(item, DESPACHADO)
        en_cola = self.notify_ready(comanda.orden_id)
        self.db.commit()
        if en_cola:
            cola_mensajes.despertar()

        self.notify(comanda, "comanda.despachada")
        return self.tools.output(200, "Despachado.", self.querys.format_command(comanda))

    # Reabrir desde Listos por error: queda auditado (doc 16)
    def reopen(self, data: dict):

        comanda, punto, items = self.get_command(data["comanda_id"])
        motivo = clean_text(data["motivo"])
        listos = [i for i in items if i.estado == DESPACHADO]
        if not listos:
            raise CustomException("La comanda no tiene ítems listos para reabrir.", 409)

        for item in listos:
            self.querys.transition(item, EN_PROCESO, motivo)
        self.querys.audit("comanda_reabierta", "comanda", comanda.id, motivo=motivo,
                          despues={"items": [i.id for i in listos]}, commit=False)
        self.db.commit()

        self.notify(comanda, "comanda.reabierta")
        return self.tools.output(200, "Comanda reabierta.", self.querys.format_command(comanda))

    # Se acabó un producto con órdenes en curso: se cancela el ítem y se avisa a la zona (doc 17)
    def sold_out(self, data: dict):

        item = self.querys.get_own(OrdenItemModel, data["orden_item_id"], "ítem", lock=True)
        if not item.comanda_id:
            raise CustomException("El ítem no está en una comanda.")
        comanda, punto, items = self.get_command(item.comanda_id)
        if item.estado not in [NUEVO, EN_PROCESO]:
            raise CustomException("Solo se marca agotado un ítem que aún no se ha despachado.", 409)

        motivo = clean_text(data.get("motivo")) or "Agotado"
        self.querys.transition(item, CANCELADO, motivo)
        item.motivo_cancelacion = motivo
        item.tipo_cancelacion = "cancelacion"
        producto = self.db.get(ProductoModel, item.producto_id)
        producto.agotado = True

        orden = self.db.get(OrdenModel, item.orden_id)
        self.querys.recalc_total(orden)
        self.querys.audit("item_agotado", "orden_item", item.id, motivo=motivo,
                          despues={"producto_id": producto.id}, commit=False)
        self.db.commit()

        self.notify(comanda, "item.agotado")
        realtime.publish(orden.restaurante_id, ["ordenes"],
                         {"tipo": "producto.agotado", "producto_id": producto.id, "agotado": True})
        return self.tools.output(200, f"{producto.nombre} marcado como agotado. Se avisó al mesero.",
                                 self.querys.format_command(comanda))

    # Datos de la tirilla de comanda (sin precios, doc 18). La reimpresión queda registrada.
    def ticket(self, data: dict):

        comanda, punto, items = self.get_command(data["comanda_id"])
        if comanda.impresa_en:
            self.querys.audit("tirilla_reimpresa", "comanda", comanda.id, commit=False)
        else:
            comanda.impresa_en = now()
        self.db.commit()

        tarjeta = self.querys.format_command(comanda)
        tarjeta["items"] = [i for i in tarjeta["items"] if i["estado"] != CANCELADO]
        tarjeta["punto"] = punto.nombre
        tarjeta["restaurante"] = self.querys.restaurante().nombre
        tarjeta["hora_local"] = self.querys.local_time(comanda.creado_en)
        return self.tools.output(200, "Tirilla de la comanda.", tarjeta)

    # Producción solo ve y modifica lo de su punto (doc 19, sección 8)
    def get_point(self, punto_id):
        punto = self.querys.get_own(PuntoProduccionModel, punto_id, "punto de producción")
        if self.ctx.get("puntos") is not None and punto.id not in self.ctx["puntos"]:
            raise CustomException("No tiene asignado este punto de producción.", 403)
        return punto

    def get_command(self, comanda_id):
        comanda = self.querys.get_own(ComandaModel, comanda_id, "comanda", lock=True)
        punto = self.get_point(comanda.punto_produccion_id)
        return comanda, punto, self.querys.items_of_comanda(comanda.id, lock=True)

    def notify(self, comanda, tipo: str):
        orden = self.db.get(OrdenModel, comanda.orden_id)
        realtime.publish(orden.restaurante_id, channels_for(orden.zona_id, [comanda.punto_produccion_id]), {
            "tipo": tipo,
            "orden_id": orden.id,
            "comanda_id": comanda.id,
            "numero": orden.numero,
            "mesa_id": orden.mesa_id,
            "zona_id": orden.zona_id,
        })

    # Pedido para recoger completo: se avisa al cliente (doc 31B). Los domicilios avisan al salir
    def notify_ready(self, orden_id):
        orden = self.db.get(OrdenModel, orden_id)
        if orden.canal not in ("mostrador", "qr_rapido"):
            return False
        self.db.flush()
        items = [i for i in self.querys.items_of(orden.id) if i.estado != CANCELADO]
        if not items or any(i.estado not in (DESPACHADO, ENTREGADO) for i in items):
            return False
        return notificar(self.db, self.ctx, "orden_lista", orden)
