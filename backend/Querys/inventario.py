from decimal import Decimal, ROUND_HALF_UP
from Querys.base import Querys
from Models.insumo_model import InsumoModel
from Models.insumo_presentacion_model import InsumoPresentacionModel
from Models.receta_model import RecetaModel
from Models.receta_linea_model import RecetaLineaModel
from Models.opcion_insumo_model import OpcionInsumoModel
from Models.movimiento_inventario_model import MovimientoInventarioModel
from Models.orden_item_modificador_model import OrdenItemModificadorModel
from Models.orden_model import OrdenModel
from Utils.tools import CustomException

CERO = Decimal("0")
# Movimientos que traen mercancía con su costo y recalculan el promedio ponderado
ENTRADAS_CON_COSTO = {"entrada", "compra", "produccion"}
# Salidas que devuelven mercancía al costo que entró: sacan ese valor del promedio (RN-COM-05)
SALIDAS_AL_COSTO = {"anulacion_compra", "devolucion"}
# Un insumo con alguno de estos movimientos lleva inventario; sin ellos su stock solo refleja consumos
CARGAS = ("entrada", "compra", "produccion", "ajuste")


def dec(valor) -> Decimal:
    return Decimal(str(valor if valor is not None else 0))


def pesos(valor) -> int:
    return int(dec(valor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class InventarioQuerys(Querys):

    # ---- Insumos ----

    def insumos(self, incluir_inactivos=False, categoria=None, buscar=None):
        query = self.scoped(InsumoModel)
        if not incluir_inactivos:
            query = query.filter(InsumoModel.activo.is_(True))
        if categoria:
            query = query.filter(InsumoModel.categoria == categoria)
        if buscar:
            query = query.filter(InsumoModel.nombre.ilike(f"%{buscar}%"))
        return query.order_by(InsumoModel.categoria.asc().nullslast(), InsumoModel.nombre.asc()).all()

    def presentaciones(self, insumo_id):
        return self.scoped(InsumoPresentacionModel).filter(InsumoPresentacionModel.insumo_id == insumo_id).order_by(
            InsumoPresentacionModel.factor.asc()).all()

    def tiene_movimientos(self, insumo_id):
        return self.scoped(MovimientoInventarioModel).filter(MovimientoInventarioModel.insumo_id == insumo_id).first() is not None

    # ---- Movimientos ----

    def mover(self, insumo_id, tipo: str, cantidad, costo_unitario=None, motivo=None, orden_item_id=None,
              conteo_id=None, referencia=None, compra_id=None):
        """ Único punto que cambia el stock: bloquea el insumo, recalcula el costo promedio en las
            entradas y deja el movimiento con el stock resultante (RN-INV-01). """
        insumo = self.scoped(InsumoModel).filter(InsumoModel.id == insumo_id).with_for_update().first()
        if not insumo:
            raise CustomException("El insumo no existe.", 404)
        cantidad = dec(cantidad)
        if cantidad == 0:
            return None
        stock_anterior = dec(insumo.stock)

        if tipo in ENTRADAS_CON_COSTO and cantidad > 0:
            costo = dec(costo_unitario)
            # Promedio ponderado; con stock en cero o negativo, el costo nuevo es el de la entrada
            if stock_anterior > 0:
                insumo.costo_promedio = ((stock_anterior * dec(insumo.costo_promedio) + cantidad * costo)
                                         / (stock_anterior + cantidad)).quantize(Decimal("0.0001"))
            else:
                insumo.costo_promedio = costo.quantize(Decimal("0.0001"))
        elif tipo in SALIDAS_AL_COSTO and cantidad < 0 and costo_unitario is not None:
            costo = dec(costo_unitario)
            restante = stock_anterior + cantidad
            valor = stock_anterior * dec(insumo.costo_promedio) + cantidad * costo
            # Si ya se consumió parte o el valor no alcanza, el promedio se deja como está
            if restante > 0 and valor > 0:
                insumo.costo_promedio = (valor / restante).quantize(Decimal("0.0001"))
        else:
            costo = dec(costo_unitario) if costo_unitario is not None else dec(insumo.costo_promedio)

        insumo.stock = stock_anterior + cantidad
        movimiento = MovimientoInventarioModel(self._with_tenant(MovimientoInventarioModel, {
            "insumo_id": insumo.id, "tipo": tipo, "cantidad": cantidad, "costo_unitario": costo,
            "costo_total": pesos(abs(cantidad) * costo), "stock_resultante": insumo.stock, "motivo": motivo,
            "orden_item_id": orden_item_id, "conteo_id": conteo_id, "referencia": referencia, "compra_id": compra_id,
            "usuario_id": self.ctx.get("usuario_id"),
        }))
        self.db.add(movimiento)
        return movimiento

    def movimientos(self, insumo_id=None, tipo=None, desde=None, hasta=None, limite=200):
        query = self.scoped(MovimientoInventarioModel)
        if insumo_id:
            query = query.filter(MovimientoInventarioModel.insumo_id == int(insumo_id))
        if tipo:
            query = query.filter(MovimientoInventarioModel.tipo == tipo)
        if desde:
            query = query.filter(MovimientoInventarioModel.creado_en >= desde)
        if hasta:
            query = query.filter(MovimientoInventarioModel.creado_en < hasta)
        return query.order_by(MovimientoInventarioModel.id.desc()).limit(limite).all()

    def consumos_de_item(self, orden_item_id):
        return self.scoped(MovimientoInventarioModel).filter(
            MovimientoInventarioModel.orden_item_id == orden_item_id, MovimientoInventarioModel.tipo == "consumo").all()

    # ---- Recetas ----

    def receta_de_producto(self, producto_id):
        return self.scoped(RecetaModel).filter(RecetaModel.producto_id == producto_id).first()

    def receta_de_insumo(self, insumo_id):
        return self.scoped(RecetaModel).filter(RecetaModel.insumo_id == insumo_id).first()

    def recetas(self):
        return self.scoped(RecetaModel).all()

    def lineas(self, receta_id):
        return self.scoped(RecetaLineaModel).filter(RecetaLineaModel.receta_id == receta_id).order_by(
            RecetaLineaModel.id.asc()).all()

    def opcion_insumos(self, opcion_ids):
        return self.scoped(OpcionInsumoModel).filter(OpcionInsumoModel.opcion_id.in_(list(opcion_ids) or [0])).all()

    def requerimientos(self, receta, unidades) -> dict:
        """ Insumos que consume producir `unidades` (porciones del producto o cantidad de la preparación):
            cantidad × (1 + merma) × unidades / rendimiento. """
        result = {}
        rendimiento = dec(receta.rendimiento) or Decimal("1")
        for linea in self.lineas(receta.id):
            cantidad = dec(linea.cantidad) * (1 + dec(linea.merma) / 100) * dec(unidades) / rendimiento
            result[linea.insumo_id] = result.get(linea.insumo_id, CERO) + cantidad
        return result

    def requerimientos_item(self, item) -> dict:
        """ Lo que consume un ítem de orden: su receta más lo que suman o restan sus modificadores.
            Sin receta y sin modificadores con insumos, no consume nada (RN-REC-05). """
        result = {}
        receta = self.receta_de_producto(item.producto_id)
        if receta:
            result = self.requerimientos(receta, item.cantidad)
        opciones = [m.opcion_id for m in self.scoped(OrdenItemModificadorModel).filter(
            OrdenItemModificadorModel.orden_item_id == item.id).all()]
        for extra in self.opcion_insumos(opciones):
            result[extra.insumo_id] = result.get(extra.insumo_id, CERO) + dec(extra.cantidad) * item.cantidad
        return {k: v.quantize(Decimal("0.001")) for k, v in result.items() if v > 0}

    # ---- Costeo ----

    def costo_unitario(self, insumo, visitados=None):
        """ Costo por unidad base. Una preparación con receta se costea con el costo actual de sus
            ingredientes, así un cambio de precio de un insumo se refleja en todo plato que la use. """
        visitados = visitados or set()
        if insumo.es_preparacion and insumo.id not in visitados:
            receta = self.receta_de_insumo(insumo.id)
            if receta:
                return self.costo_receta(receta, visitados | {insumo.id})
        return dec(insumo.costo_promedio)

    def costo_receta(self, receta, visitados=None):
        """ Costo de una unidad de rendimiento (una porción o una unidad base de la preparación) """
        total = CERO
        rendimiento = dec(receta.rendimiento) or Decimal("1")
        for linea in self.lineas(receta.id):
            insumo = self.db.get(InsumoModel, linea.insumo_id)
            total += dec(linea.cantidad) * (1 + dec(linea.merma) / 100) * self.costo_unitario(insumo, visitados)
        return total / rendimiento

    # Una preparación no puede contenerse a sí misma, ni directa ni indirectamente (RN-REC-02)
    def crea_ciclo(self, insumo_id, ingredientes: list):
        pendientes, vistos = list(ingredientes), set()
        while pendientes:
            actual = pendientes.pop()
            if actual == insumo_id:
                return True
            if actual in vistos:
                continue
            vistos.add(actual)
            receta = self.receta_de_insumo(actual)
            if receta:
                pendientes.extend(l.insumo_id for l in self.lineas(receta.id))
        return False

    def alcance_productos(self) -> list:
        """ Porciones que alcanzan de cada producto con receta según el stock actual (doc 12, sección 5).
            Solo cuentan los insumos con inventario cargado: si el restaurante nunca registró entradas,
            su stock no dice si hay o no. """
        from Models.producto_model import ProductoModel
        from Models.categoria_model import CategoriaModel
        recetas = {r.id: r for r in self.scoped(RecetaModel).filter(RecetaModel.producto_id.isnot(None)).all()}
        if not recetas:
            return []
        insumos = {i.id: i for i in self.insumos()}
        controlados = {insumo_id for (insumo_id,) in self.scoped(MovimientoInventarioModel).filter(
            MovimientoInventarioModel.tipo.in_(CARGAS)).with_entities(MovimientoInventarioModel.insumo_id).distinct()}
        por_porcion = {}
        for linea in self.scoped(RecetaLineaModel).filter(RecetaLineaModel.receta_id.in_(list(recetas))).all():
            if linea.insumo_id not in insumos or linea.insumo_id not in controlados:
                continue
            receta = recetas[linea.receta_id]
            cantidad = dec(linea.cantidad) * (1 + dec(linea.merma) / 100) / (dec(receta.rendimiento) or Decimal("1"))
            lineas = por_porcion.setdefault(receta.producto_id, {})
            lineas[linea.insumo_id] = lineas.get(linea.insumo_id, CERO) + cantidad
        productos = self.scoped(ProductoModel).filter(ProductoModel.id.in_(list(por_porcion) or [0]), ProductoModel.activo.is_(True),
                                                      ProductoModel.tipo == "simple").order_by(ProductoModel.nombre).all()
        puntos_categoria = {c.id: c.punto_produccion_id for c in self.scoped(CategoriaModel).all()}
        result = []
        for producto in productos:
            alcances = {i: max(int(dec(insumos[i].stock) // c), 0) for i, c in por_porcion[producto.id].items() if c > 0}
            if not alcances:
                continue
            alcance = min(alcances.values())
            result.append({
                "producto_id": producto.id, "nombre": producto.nombre, "agotado": producto.agotado,
                # Donde se prepara: el del producto o el de su categoría; si depende de la zona, queda en None
                "punto_produccion_id": producto.punto_produccion_id or puntos_categoria.get(producto.categoria_id), "porciones": alcance,
                # Lo que pone el límite: el insumo que alcanza para menos porciones
                "limitan": [{"insumo_id": i, "nombre": insumos[i].nombre, "unidad": insumos[i].unidad,
                             "stock": float(insumos[i].stock), "por_porcion": float(por_porcion[producto.id][i].quantize(Decimal("0.001")))}
                            for i, n in alcances.items() if n == alcance],
            })
        return result

    def productos_vendidos(self, desde):
        """ Valor vendido por producto desde una fecha, para la cobertura de recetas (doc 14, sección 6) """
        from Models.orden_item_model import OrdenItemModel
        from Utils.estados import CANCELADO
        from sqlalchemy import func
        rows = self.scoped(OrdenItemModel).join(OrdenModel, OrdenModel.id == OrdenItemModel.orden_id).filter(
            OrdenModel.jornada >= desde, OrdenItemModel.estado != CANCELADO,
        ).with_entities(OrdenItemModel.producto_id, func.sum(OrdenItemModel.total), func.sum(OrdenItemModel.cantidad)).group_by(
            OrdenItemModel.producto_id).all()
        return {producto_id: (int(total or 0), int(cantidad or 0)) for producto_id, total, cantidad in rows}


def al_cambiar_estado(db, ctx, item, nuevo: str):
    """ Descuento de inventario por estado del ítem (ADR-013, doc 14 sección 4):
        - al entrar en producción (o despacharse directo) se descuenta su receta, una sola vez;
        - si se cancela después, el consumo se reversa y queda registrado como merma con el motivo. """
    from Utils.estados import EN_PROCESO, DESPACHADO, ENTREGADO, CANCELADO
    querys = InventarioQuerys(db, ctx)
    if nuevo in (EN_PROCESO, DESPACHADO, ENTREGADO) and not item.inventario_descontado:
        orden = db.get(OrdenModel, item.orden_id)
        for insumo_id, cantidad in querys.requerimientos_item(item).items():
            querys.mover(insumo_id, "consumo", -cantidad, motivo=f"Orden {orden.numero:03d}: {item.cantidad} × {item.nombre_producto}",
                         orden_item_id=item.id)
        item.inventario_descontado = True
    elif nuevo == CANCELADO and item.inventario_descontado:
        motivo = f"Cancelado en producción: {item.nombre_producto}" + (f" ({item.motivo_cancelacion})" if item.motivo_cancelacion else "")
        for consumo in querys.consumos_de_item(item.id):
            cantidad = -dec(consumo.cantidad)
            querys.mover(consumo.insumo_id, "reverso_consumo", cantidad, costo_unitario=consumo.costo_unitario,
                         motivo="Se reclasifica como merma", orden_item_id=item.id)
            querys.mover(consumo.insumo_id, "merma", -cantidad, costo_unitario=consumo.costo_unitario,
                         motivo=motivo[:200], orden_item_id=item.id)
