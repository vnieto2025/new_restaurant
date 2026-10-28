from Querys.base import Querys
from Models.orden_model import OrdenModel
from Models.orden_item_model import OrdenItemModel
from Models.orden_item_modificador_model import OrdenItemModificadorModel
from Models.comanda_model import ComandaModel
from Models.historial_estado_model import HistorialEstadoModel
from Models.producto_model import ProductoModel
from Models.categoria_model import CategoriaModel
from Models.carta_producto_model import CartaProductoModel
from Models.punto_produccion_model import PuntoProduccionModel
from Models.mesa_model import MesaModel
from Models.zona_model import ZonaModel
from Models.usuario_model import UsuarioModel
from Models.restaurante_model import RestauranteModel
from Utils.estados import validar_transicion, estado_derivado, ETIQUETAS, CANCELADO, PENDIENTES_DE_ENTREGA
from Utils.tools import now, to_local
from sqlalchemy import text
from datetime import timedelta

# Una comanda que la pantalla de producción no ha recibido en este tiempo se marca "sin confirmar" (doc 17)
SEGUNDOS_SIN_CONFIRMAR = 45

ESTADOS_ORDEN = {
    "pendiente_aprobacion": "Por aprobar",
    "nueva": "Nueva",
    "en_proceso": "En proceso",
    "lista": "Lista",
    "entregada": "Entregada",
    "cancelada": "Cancelada",
}


class OrdenQuerys(Querys):

    def get_orden_by_clave(self, clave: str):
        return self.scoped(OrdenModel).filter(OrdenModel.clave_idempotencia == clave).first()

    def get_orden_by_seguimiento(self, token: str):
        return self.db.query(OrdenModel).filter(OrdenModel.token_seguimiento == token).first()

    # Consecutivo por restaurante y jornada, atómico aunque lleguen dos órdenes a la vez
    def next_number(self, jornada):
        return self.db.execute(text(
            "INSERT INTO consecutivo_orden (restaurante_id, jornada, ultimo) VALUES (:r, :j, 1) "
            "ON CONFLICT (restaurante_id, jornada) DO UPDATE SET ultimo = consecutivo_orden.ultimo + 1 "
            "RETURNING ultimo"
        ), {"r": self.restaurante_id, "j": jornada}).scalar()

    # Productos pedibles en una carta: activos, de categoría activa y presentes en ella
    def products_in_menu(self, carta_id, producto_ids: list):
        rows = self.scoped(ProductoModel).join(
            CartaProductoModel, CartaProductoModel.producto_id == ProductoModel.id
        ).join(
            CategoriaModel, CategoriaModel.id == ProductoModel.categoria_id
        ).filter(
            CartaProductoModel.carta_id == carta_id,
            ProductoModel.id.in_(producto_ids or [0]),
            ProductoModel.activo.is_(True),
            CategoriaModel.activo.is_(True),
        ).add_columns(CategoriaModel).all()
        return {producto.id: (producto, categoria) for producto, categoria in rows}

    def get_product_names(self, producto_ids: list):
        rows = self.scoped(ProductoModel, include_deleted=True).filter(ProductoModel.id.in_(producto_ids or [0])).all()
        return {p.id: p.nombre for p in rows}

    def active_points(self):
        return {p.id for p in self.scoped(PuntoProduccionModel).filter(PuntoProduccionModel.activo.is_(True)).all()}

    def items_of(self, orden_id, lock=False):
        query = self.scoped(OrdenItemModel).filter(OrdenItemModel.orden_id == orden_id)
        if lock:
            query = query.with_for_update()
        return query.order_by(OrdenItemModel.id.asc()).all()

    def items_of_comanda(self, comanda_id, lock=False):
        query = self.scoped(OrdenItemModel).filter(OrdenItemModel.comanda_id == comanda_id)
        if lock:
            query = query.with_for_update()
        return query.order_by(OrdenItemModel.id.asc()).all()

    def items_by_lote(self, orden_id, lote: str):
        return self.scoped(OrdenItemModel).filter(
            OrdenItemModel.orden_id == orden_id, OrdenItemModel.lote == lote
        ).all()

    # Modificadores elegidos de varios ítems: {orden_item_id: [{grupo, nombre, precio_extra}]}
    def modifiers_of(self, item_ids: list):
        result = {}
        for m in self.scoped(OrdenItemModificadorModel).filter(
            OrdenItemModificadorModel.orden_item_id.in_(item_ids or [0])
        ).order_by(OrdenItemModificadorModel.id.asc()).all():
            result.setdefault(m.orden_item_id, []).append(
                {"grupo": m.grupo_nombre, "nombre": m.nombre, "precio_extra": m.precio_extra})
        return result

    def comandas_of(self, orden_id):
        return self.scoped(ComandaModel).filter(ComandaModel.orden_id == orden_id).order_by(ComandaModel.id.asc()).all()

    # Cambia el estado de un ítem respetando la máquina de estados y deja el historial (doc 16)
    def transition(self, item, nuevo: str, motivo: str = None):
        validar_transicion(item.estado, nuevo)
        anterior = item.estado
        item.estado = nuevo
        self.add_history(item, anterior, nuevo, motivo)
        # Con inventario contratado, producir descuenta insumos y cancelar después es merma (ADR-013)
        if "inventario" in (self.ctx.get("modulos") or set()):
            from Querys.inventario import al_cambiar_estado
            if nuevo == "cancelado" and motivo and not item.motivo_cancelacion:
                item.motivo_cancelacion = motivo
            al_cambiar_estado(self.db, self.ctx, item, nuevo)

    def add_history(self, item, anterior, nuevo, motivo=None):
        self.insert_data(HistorialEstadoModel, {
            "orden_item_id": item.id,
            "estado_anterior": anterior,
            "estado_nuevo": nuevo,
            "usuario_id": self.ctx.get("usuario_id"),
            "dispositivo": self.ctx.get("dispositivo"),
            "motivo": motivo,
        }, commit=False)

    def recalc_total(self, orden):
        orden.total = sum(i.total for i in self.items_of(orden.id) if i.estado != CANCELADO)

    def list_ordenes(self, jornada=None, zona_ids=None, zona_id=None, sesion_mesa_id=None, solo_activas=True):
        query = self.scoped(OrdenModel)
        if jornada:
            query = query.filter(OrdenModel.jornada == jornada)
        if zona_ids is not None:
            query = query.filter(OrdenModel.zona_id.in_(zona_ids or [0]))
        if zona_id:
            query = query.filter(OrdenModel.zona_id == int(zona_id))
        if sesion_mesa_id:
            query = query.filter(OrdenModel.sesion_mesa_id == sesion_mesa_id)
        if solo_activas:
            activas = self.scoped(OrdenItemModel).with_entities(OrdenItemModel.orden_id).filter(
                OrdenItemModel.estado.in_(PENDIENTES_DE_ENTREGA))
            query = query.filter(OrdenModel.id.in_(activas))
        return query.order_by(OrdenModel.id.desc()).limit(200).all()

    def get_nombre(self, model, record_id):
        if not record_id:
            return None
        record = self.db.get(model, record_id)
        return getattr(record, "nombre", None) if record else None

    def format_item(self, item, puntos: dict = None, modificadores: dict = None):
        return {
            "id": item.id,
            "producto_id": item.producto_id,
            "nombre": item.nombre_producto,
            "cantidad": item.cantidad,
            "precio_unitario": item.precio_unitario,
            "total": item.total,
            "nota": item.nota,
            "modificadores": (modificadores or {}).get(item.id, []),
            "estado": item.estado,
            "estado_etiqueta": ETIQUETAS.get(item.estado, item.estado),
            "punto_produccion_id": item.punto_produccion_id,
            "punto_produccion": (puntos or {}).get(item.punto_produccion_id) if item.punto_produccion_id else "Despacho directo",
            "comanda_id": item.comanda_id,
            "motivo_cancelacion": item.motivo_cancelacion,
            "tipo_cancelacion": item.tipo_cancelacion,
            "actualizado_en": item.actualizado_en,
        }

    def format_orden(self, orden):
        items = self.items_of(orden.id)
        comandas = self.comandas_of(orden.id)
        modificadores = self.modifiers_of([i.id for i in items])
        puntos = {p.id: p.nombre for p in self.scoped(PuntoProduccionModel, include_deleted=True).all()}
        mesa = self.db.get(MesaModel, orden.mesa_id)
        estado = estado_derivado([i.estado for i in items])
        limite = now() - timedelta(seconds=SEGUNDOS_SIN_CONFIRMAR)

        formatted_comandas = []
        for comanda in comandas:
            propios = [i for i in items if i.comanda_id == comanda.id]
            estado_comanda = estado_derivado([i.estado for i in propios])
            formatted_comandas.append({
                "id": comanda.id,
                "punto_produccion_id": comanda.punto_produccion_id,
                "punto_produccion": puntos.get(comanda.punto_produccion_id),
                "es_adicion": comanda.es_adicion,
                "estado": estado_comanda,
                "creado_en": comanda.creado_en,
                "recibida_en": comanda.recibida_en,
                "sin_confirmar": comanda.recibida_en is None and comanda.creado_en < limite
                and estado_comanda not in ["cancelada", "entregada"],
            })

        return {
            "id": orden.id,
            "numero": orden.numero,
            "numero_texto": f"#{orden.numero:03d}",
            "jornada": orden.jornada,
            "canal": orden.canal,
            "estado": estado,
            "estado_etiqueta": ESTADOS_ORDEN.get(estado, estado),
            "mesa_id": orden.mesa_id,
            "mesa": mesa.nombre if mesa else None,
            "mesa_tipo": mesa.tipo if mesa else None,
            "zona_id": orden.zona_id,
            "zona": self.get_nombre(ZonaModel, orden.zona_id),
            "sesion_mesa_id": orden.sesion_mesa_id,
            "mesero_id": orden.mesero_id,
            "mesero": self.get_nombre(UsuarioModel, orden.mesero_id),
            "cliente_id": orden.cliente_id,
            "cliente_nombre": orden.cliente_nombre,
            "cliente_telefono": orden.cliente_telefono,
            "notas": orden.notas,
            "total": orden.total,
            "moneda": orden.moneda,
            "token_seguimiento": orden.token_seguimiento,
            "creado_en": orden.creado_en,
            "aprobada_en": orden.aprobada_en,
            "items": [self.format_item(i, puntos, modificadores) for i in items],
            "comandas": formatted_comandas,
        }

    def restaurante(self):
        return self.db.get(RestauranteModel, self.restaurante_id)

    def local_time(self, value):
        restaurante = self.restaurante()
        return to_local(value, restaurante.zona_horaria if restaurante else None)
