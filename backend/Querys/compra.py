from sqlalchemy import text, func
from Querys.base import Querys
from Models.proveedor_model import ProveedorModel
from Models.proveedor_insumo_model import ProveedorInsumoModel
from Models.compra_model import CompraModel
from Models.compra_linea_model import CompraLineaModel
from Models.compra_recepcion_model import CompraRecepcionModel
from Models.movimiento_inventario_model import MovimientoInventarioModel


class CompraQuerys(Querys):

    # ---- Proveedores ----

    def proveedores(self, incluir_inactivos=False, buscar=None):
        query = self.scoped(ProveedorModel)
        if not incluir_inactivos:
            query = query.filter(ProveedorModel.activo.is_(True))
        if buscar:
            patron = f"%{buscar}%"
            query = query.filter(ProveedorModel.nombre.ilike(patron) | ProveedorModel.razon_social.ilike(patron)
                                 | ProveedorModel.documento.ilike(patron))
        return query.order_by(ProveedorModel.nombre.asc()).all()

    def nombre_proveedor_existe(self, nombre, exclude_id=None):
        query = self.scoped(ProveedorModel).filter(ProveedorModel.nombre.ilike(nombre))
        if exclude_id:
            query = query.filter(ProveedorModel.id != exclude_id)
        return query.first() is not None

    def insumos_de_proveedor(self, proveedor_id):
        return self.scoped(ProveedorInsumoModel).filter(ProveedorInsumoModel.proveedor_id == proveedor_id).all()

    def proveedores_de_insumo(self, insumo_id):
        return self.scoped(ProveedorInsumoModel).filter(ProveedorInsumoModel.insumo_id == insumo_id).all()

    def proveedor_insumo(self, proveedor_id, insumo_id):
        return self.scoped(ProveedorInsumoModel).filter(ProveedorInsumoModel.proveedor_id == proveedor_id,
                                                        ProveedorInsumoModel.insumo_id == insumo_id).first()

    def preferidos(self):
        """ insumo_id -> proveedor_id preferido, para la lista de compras sugerida """
        filas = self.scoped(ProveedorInsumoModel).join(ProveedorModel, ProveedorModel.id == ProveedorInsumoModel.proveedor_id).filter(
            ProveedorInsumoModel.preferido.is_(True), ProveedorModel.activo.is_(True)).all()
        return {f.insumo_id: f for f in filas}

    def historial_precios(self, proveedor_id=None, insumo_id=None, limite=60):
        """ Precios pagados en compras recibidas, del más reciente al más antiguo (RN-PRV-02) """
        query = self.scoped(CompraLineaModel).join(CompraModel, CompraModel.id == CompraLineaModel.compra_id).filter(
            CompraLineaModel.cantidad_recibida > 0, CompraModel.estado != "anulada")
        if proveedor_id:
            query = query.filter(CompraModel.proveedor_id == proveedor_id)
        if insumo_id:
            query = query.filter(CompraLineaModel.insumo_id == insumo_id)
        return query.with_entities(CompraLineaModel, CompraModel).order_by(
            CompraModel.fecha.desc(), CompraLineaModel.id.desc()).limit(limite).all()

    def totales_por_proveedor(self, desde):
        filas = self.scoped(CompraModel).filter(CompraModel.estado != "anulada", CompraModel.fecha >= desde,
                                                CompraModel.proveedor_id.isnot(None)).with_entities(
            CompraModel.proveedor_id, func.sum(CompraModel.valor_recibido), func.count(CompraModel.id)).group_by(
            CompraModel.proveedor_id).all()
        return {proveedor_id: (int(total or 0), int(cantidad)) for proveedor_id, total, cantidad in filas}

    # ---- Compras ----

    def next_number(self):
        return self.db.execute(text(
            "INSERT INTO consecutivo_compra (restaurante_id, ultimo) VALUES (:r, 1) "
            "ON CONFLICT (restaurante_id) DO UPDATE SET ultimo = consecutivo_compra.ultimo + 1 RETURNING ultimo"
        ), {"r": self.restaurante_id}).scalar()

    def compras(self, estado=None, proveedor_id=None, desde=None, hasta=None, buscar=None, limite=100):
        query = self.scoped(CompraModel)
        if estado == "pendientes":
            query = query.filter(CompraModel.estado.in_(["solicitada", "parcial"]))
        elif estado:
            query = query.filter(CompraModel.estado == estado)
        if proveedor_id:
            query = query.filter(CompraModel.proveedor_id == int(proveedor_id))
        if desde:
            query = query.filter(CompraModel.fecha >= desde)
        if hasta:
            query = query.filter(CompraModel.fecha <= hasta)
        if buscar:
            filtro = CompraModel.proveedor_nombre.ilike(f"%{buscar}%") | CompraModel.factura_proveedor.ilike(f"%{buscar}%")
            if buscar.isdigit():
                filtro = filtro | (CompraModel.numero == int(buscar))
            query = query.filter(filtro)
        return query.order_by(CompraModel.id.desc()).limit(limite).all()

    def lineas(self, compra_id, lock=False):
        query = self.scoped(CompraLineaModel).filter(CompraLineaModel.compra_id == compra_id).order_by(CompraLineaModel.id.asc())
        if lock:
            query = query.with_for_update()
        return query.all()

    def recepciones(self, compra_id):
        return self.scoped(CompraRecepcionModel).filter(CompraRecepcionModel.compra_id == compra_id).order_by(
            CompraRecepcionModel.id.asc()).all()

    def movimientos_de_compra(self, compra_id, tipo="compra"):
        return self.scoped(MovimientoInventarioModel).filter(MovimientoInventarioModel.compra_id == compra_id,
                                                             MovimientoInventarioModel.tipo == tipo).all()
