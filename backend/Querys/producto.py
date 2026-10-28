from Querys.base import Querys
from Models.producto_model import ProductoModel
from Models.categoria_model import CategoriaModel
from Models.carta_model import CartaModel
from Models.carta_producto_model import CartaProductoModel
from Models.punto_produccion_model import PuntoProduccionModel
from Utils.tools import normalize_text
from Querys.modificador import ModificadorQuerys
from sqlalchemy import func


class ProductoQuerys(Querys):

    def list_productos(self, categoria_id=None, buscar=None, incluir_inactivos=False):
        query = self.scoped(ProductoModel)
        if categoria_id:
            query = query.filter(ProductoModel.categoria_id == int(categoria_id))
        if not incluir_inactivos:
            query = query.filter(ProductoModel.activo.is_(True))
        productos = query.order_by(ProductoModel.orden.asc(), ProductoModel.nombre.asc()).all()
        if buscar:
            needle = normalize_text(buscar)
            productos = [p for p in productos if needle in normalize_text(p.nombre)]
        return productos

    def name_exists(self, nombre: str, exclude_id=None):
        query = self.scoped(ProductoModel, include_deleted=True).filter(func.lower(ProductoModel.nombre) == nombre.lower())
        if exclude_id:
            query = query.filter(ProductoModel.id != exclude_id)
        return query.first() is not None

    def get_cartas(self, ids=None):
        query = self.scoped(CartaModel)
        if ids is not None:
            query = query.filter(CartaModel.id.in_(ids or [0]))
        return query.all()

    def get_cartas_producto(self, producto_id):
        return [c for (c,) in self.scoped(CartaProductoModel).with_entities(CartaProductoModel.carta_id).filter(
            CartaProductoModel.producto_id == producto_id).all()]

    # Reemplaza las cartas en las que aparece un producto
    def set_cartas_producto(self, producto_id, carta_ids: list):
        self.scoped(CartaProductoModel).filter(
            CartaProductoModel.producto_id == producto_id
        ).delete(synchronize_session=False)
        for carta_id in carta_ids:
            self.insert_data(CartaProductoModel, {"carta_id": carta_id, "producto_id": producto_id}, commit=False)
        self.db.flush()

    def format_producto(self, producto):
        categoria = self.db.get(CategoriaModel, producto.categoria_id)
        punto = self.db.get(PuntoProduccionModel, producto.punto_produccion_id) if producto.punto_produccion_id else None
        return {
            "id": producto.id,
            "categoria_id": producto.categoria_id,
            "categoria": categoria.nombre if categoria else None,
            "nombre": producto.nombre,
            "descripcion": producto.descripcion,
            "precio": producto.precio,
            "punto_produccion_id": producto.punto_produccion_id,
            "punto_produccion": punto.nombre if punto else None,
            "impuesto_id": producto.impuesto_id,
            "orden": producto.orden,
            "agotado": producto.agotado,
            "activo": producto.activo,
            "cartas": self.get_cartas_producto(producto.id),
            "grupos": ModificadorQuerys(self.db, self.ctx).grupos_de_producto(producto.id),
        }
