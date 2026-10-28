from datetime import timedelta
from decimal import Decimal
from Utils.tools import Tools, CustomException
from Utils.impuestos import desglosar
from Querys.inventario import InventarioQuerys, dec
from Querys.facturacion import FacturacionQuerys
from Models.receta_model import RecetaModel
from Models.receta_linea_model import RecetaLineaModel
from Models.opcion_insumo_model import OpcionInsumoModel
from Models.insumo_model import InsumoModel, UNIDADES
from Models.producto_model import ProductoModel
from Models.categoria_model import CategoriaModel
from Models.opcion_modificador_model import OpcionModificadorModel
from Class.Insumo import cantidad
from Class.Caja import dia_actual

MAX_LINEAS = 40


class Receta:
    """ Recetas de productos y preparaciones, con costo y margen (doc 14).
        Una receta nunca cambia el precio (RN-REC-01) y aplica a las órdenes futuras (RN-REC-03). """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = InventarioQuerys(db, ctx)

    def get(self, data: dict):
        producto, insumo = self.target(data)
        receta = self.querys.receta_de_producto(producto.id) if producto else self.querys.receta_de_insumo(insumo.id)
        return self.tools.output(200, "Receta." if receta else "Aún no tiene receta.", self.format(receta, producto, insumo))

    def save(self, data: dict):
        producto, insumo = self.target(data)
        lineas = data.get("lineas") or []
        if not lineas:
            raise CustomException("La receta necesita al menos un ingrediente.")
        if len(lineas) > MAX_LINEAS:
            raise CustomException(f"Máximo {MAX_LINEAS} ingredientes por receta.")

        limpias, vistos = [], set()
        for linea in lineas:
            ingrediente = self.querys.get_own(InsumoModel, linea["insumo_id"], "insumo")
            if ingrediente.id in vistos:
                raise CustomException(f"{ingrediente.nombre} está repetido en la receta.")
            vistos.add(ingrediente.id)
            merma = dec(linea.get("merma") or 0)
            if merma < 0 or merma >= 100:
                raise CustomException("La merma debe estar entre 0 y 99 %.")
            limpias.append({"insumo_id": ingrediente.id, "cantidad": cantidad(linea["cantidad"]), "merma": merma})
        if insumo and self.querys.crea_ciclo(insumo.id, list(vistos)):
            raise CustomException("La preparación no puede usarse a sí misma como ingrediente (RN-REC-02).")
        rendimiento = cantidad(data.get("rendimiento") or 1, "rendimiento")

        receta = self.querys.receta_de_producto(producto.id) if producto else self.querys.receta_de_insumo(insumo.id)
        antes = self.snapshot(receta)
        if receta:
            self.querys.scoped(RecetaLineaModel).filter(RecetaLineaModel.receta_id == receta.id).delete(synchronize_session=False)
            receta.rendimiento = rendimiento
            receta.actualizado_por = self.ctx.get("usuario_id")
        else:
            receta_id = self.querys.insert_data(RecetaModel, {
                "producto_id": producto.id if producto else None, "insumo_id": insumo.id if insumo else None,
                "rendimiento": rendimiento, "actualizado_por": self.ctx.get("usuario_id"),
            }, commit=False)
            receta = self.querys.get_own(RecetaModel, receta_id, "receta")
        for linea in limpias:
            self.querys.insert_data(RecetaLineaModel, {**linea, "receta_id": receta.id}, commit=False)
        self.db.flush()
        self.querys.audit("receta_guardada", "receta", receta.id, antes=antes, despues=self.snapshot(receta), commit=False)
        self.db.commit()
        return self.tools.output(200, "Receta guardada. Aplica a las órdenes que entren a producción desde ahora.",
                                 self.format(receta, producto, insumo))

    def delete(self, data: dict):
        producto, insumo = self.target(data)
        receta = self.querys.receta_de_producto(producto.id) if producto else self.querys.receta_de_insumo(insumo.id)
        if not receta:
            raise CustomException("No tiene receta.", 404)
        self.querys.audit("receta_eliminada", "receta", receta.id, antes=self.snapshot(receta), commit=False)
        self.querys.scoped(RecetaLineaModel).filter(RecetaLineaModel.receta_id == receta.id).delete(synchronize_session=False)
        self.db.delete(receta)
        self.db.commit()
        return self.tools.output(200, "Receta eliminada. Ese producto deja de descontar inventario.")

    # ---- Modificadores ----

    def option_supplies(self, data: dict):
        filas = self.querys.scoped(OpcionInsumoModel).all()
        result = {}
        for fila in filas:
            insumo = self.db.get(InsumoModel, fila.insumo_id)
            result.setdefault(fila.opcion_id, []).append({
                "insumo_id": fila.insumo_id, "insumo": insumo.nombre, "unidad": insumo.unidad, "cantidad": float(fila.cantidad)})
        return self.tools.output(200, "Insumos de los modificadores.", [{"opcion_id": k, "lineas": v} for k, v in result.items()])

    def save_option_supplies(self, data: dict):
        opcion = self.querys.get_own(OpcionModificadorModel, data["opcion_id"], "opción")
        self.querys.scoped(OpcionInsumoModel).filter(OpcionInsumoModel.opcion_id == opcion.id).delete(synchronize_session=False)
        vistos = set()
        for linea in data.get("lineas") or []:
            insumo = self.querys.get_own(InsumoModel, linea["insumo_id"], "insumo")
            if insumo.id in vistos:
                raise CustomException(f"{insumo.nombre} está repetido.")
            vistos.add(insumo.id)
            # Negativo resta: "Sin queso" = −30 g de queso
            self.querys.insert_data(OpcionInsumoModel, {
                "opcion_id": opcion.id, "insumo_id": insumo.id,
                "cantidad": cantidad(linea["cantidad"], permitir_negativo=True),
            }, commit=False)
        self.db.commit()
        return self.tools.output(200, f"Insumos de «{opcion.nombre}» guardados.")

    # ---- Costos y cobertura ----

    def costs(self, data: dict):
        """ Costo y margen de cada producto con su precio sin impuesto, y qué parte de lo vendido
            en los últimos 30 días tiene receta (doc 14, secciones 3 y 6). """
        hoy = dia_actual(self.ctx)
        facturacion = FacturacionQuerys(self.db, self.ctx)
        tarifas = facturacion.tarifas_vigentes(hoy)
        defecto = facturacion.impuesto_defecto()
        vendidos = self.querys.productos_vendidos(hoy - timedelta(days=30))
        meta = dec(data.get("margen_minimo") or 60)

        productos, con_receta_valor, total_valor = [], 0, 0
        for producto in self.querys.scoped(ProductoModel).filter(ProductoModel.activo.is_(True)).order_by(ProductoModel.nombre).all():
            categoria = self.db.get(CategoriaModel, producto.categoria_id)
            impuesto_id = producto.impuesto_id or categoria.impuesto_id or (defecto.id if defecto else None)
            base, _ = desglosar(producto.precio, tarifas.get(impuesto_id))
            receta = self.querys.receta_de_producto(producto.id)
            costo = int(self.querys.costo_receta(receta).quantize(Decimal("1"))) if receta else None
            margen = base - costo if costo is not None else None
            porcentaje = round(margen * 100 / base, 1) if margen is not None and base else None
            valor, unidades = vendidos.get(producto.id, (0, 0))
            total_valor += valor
            if receta:
                con_receta_valor += valor
            productos.append({
                "producto_id": producto.id, "nombre": producto.nombre, "categoria": categoria.nombre,
                "precio": producto.precio, "precio_sin_impuesto": base, "tiene_receta": bool(receta),
                "costo": costo, "margen": margen, "margen_porcentaje": porcentaje,
                "bajo_meta": porcentaje is not None and porcentaje < meta,
                "vendido_30_dias": valor, "unidades_30_dias": unidades,
            })
        # Primero lo que más pierde margen
        productos.sort(key=lambda p: (p["margen_porcentaje"] is None, p["margen_porcentaje"] if p["margen_porcentaje"] is not None else 0))
        return self.tools.output(200, "Costo y margen por producto.", {
            "productos": productos,
            "margen_minimo": float(meta),
            "cobertura": round(con_receta_valor * 100 / total_valor, 1) if total_valor else None,
            "con_receta": sum(1 for p in productos if p["tiene_receta"]),
            "sin_receta": sum(1 for p in productos if not p["tiene_receta"]),
        })

    # ---- Apoyo ----

    def target(self, data: dict):
        if data.get("producto_id"):
            return self.querys.get_own(ProductoModel, data["producto_id"], "producto"), None
        if data.get("insumo_id"):
            insumo = self.querys.get_own(InsumoModel, data["insumo_id"], "insumo")
            if not insumo.es_preparacion:
                raise CustomException("Solo las preparaciones tienen receta. Marca el insumo como preparación.")
            return None, insumo
        raise CustomException("Indica el producto o la preparación.")

    def snapshot(self, receta):
        if not receta:
            return None
        return {"rendimiento": str(receta.rendimiento),
                "lineas": [{"insumo_id": l.insumo_id, "cantidad": str(l.cantidad), "merma": str(l.merma)}
                           for l in self.querys.lineas(receta.id)]}

    def format(self, receta, producto=None, insumo=None):
        data = {
            "producto_id": producto.id if producto else None,
            "insumo_id": insumo.id if insumo else None,
            "nombre": producto.nombre if producto else insumo.nombre,
            "unidad_rendimiento": "porciones" if producto else UNIDADES[insumo.unidad],
            "existe": bool(receta),
            "rendimiento": float(receta.rendimiento) if receta else 1.0,
            "lineas": [],
            "costo": None,
        }
        if not receta:
            return data
        for linea in self.querys.lineas(receta.id):
            ingrediente = self.db.get(InsumoModel, linea.insumo_id)
            unitario = self.querys.costo_unitario(ingrediente)
            efectiva = dec(linea.cantidad) * (1 + dec(linea.merma) / 100)
            data["lineas"].append({
                "insumo_id": ingrediente.id, "insumo": ingrediente.nombre, "unidad": ingrediente.unidad,
                "cantidad": float(linea.cantidad), "merma": float(linea.merma),
                "costo": int((efectiva * unitario).quantize(Decimal("1"))),
            })
        data["costo"] = int(self.querys.costo_receta(receta).quantize(Decimal("1")))
        if producto:
            facturacion = FacturacionQuerys(self.db, self.ctx)
            categoria = self.db.get(CategoriaModel, producto.categoria_id)
            defecto = facturacion.impuesto_defecto()
            impuesto_id = producto.impuesto_id or categoria.impuesto_id or (defecto.id if defecto else None)
            base, _ = desglosar(producto.precio, facturacion.tarifas_vigentes(dia_actual(self.ctx)).get(impuesto_id))
            data["precio"] = producto.precio
            data["precio_sin_impuesto"] = base
            data["margen"] = base - data["costo"]
            data["margen_porcentaje"] = round(data["margen"] * 100 / base, 1) if base else None
        return data
