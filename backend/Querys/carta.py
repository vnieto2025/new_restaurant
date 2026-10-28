from Querys.base import Querys
from Models.carta_model import CartaModel
from Models.carta_producto_model import CartaProductoModel
from Models.producto_model import ProductoModel
from Models.categoria_model import CategoriaModel
from Models.zona_model import ZonaModel
from Querys.modificador import ModificadorQuerys
from sqlalchemy import func


class CartaQuerys(Querys):

    def list_cartas(self, incluir_inactivas=False):
        query = self.scoped(CartaModel)
        if not incluir_inactivas:
            query = query.filter(CartaModel.activo.is_(True))
        return query.order_by(CartaModel.id.asc()).all()

    def name_exists(self, nombre: str, exclude_id=None):
        query = self.scoped(CartaModel, include_deleted=True).filter(func.lower(CartaModel.nombre) == nombre.lower())
        if exclude_id:
            query = query.filter(CartaModel.id != exclude_id)
        return query.first() is not None

    def get_producto_ids(self, carta_id):
        return [p for (p,) in self.scoped(CartaProductoModel).with_entities(CartaProductoModel.producto_id).filter(
            CartaProductoModel.carta_id == carta_id).all()]

    def valid_productos(self, ids: list):
        return {p.id for p in self.scoped(ProductoModel).filter(ProductoModel.id.in_(ids or [0])).all()}

    def set_productos(self, carta_id, producto_ids: list):
        self.scoped(CartaProductoModel).filter(CartaProductoModel.carta_id == carta_id).delete(synchronize_session=False)
        for producto_id in producto_ids:
            self.insert_data(CartaProductoModel, {"carta_id": carta_id, "producto_id": producto_id}, commit=False)
        self.db.flush()

    def zonas_con_carta(self, carta_id):
        return self.scoped(ZonaModel).filter(ZonaModel.carta_id == carta_id, ZonaModel.activo.is_(True)).all()

    def menu(self, carta_id):
        """ Carta lista para pedir: categorías activas con sus productos activos.
            Los agotados se incluyen marcados para que el cliente vea que existen (doc 11). """
        if not carta_id:
            return []
        carta = self.scoped(CartaModel).filter(CartaModel.id == carta_id, CartaModel.activo.is_(True)).first()
        if not carta:
            return []

        rows = self.scoped(ProductoModel).join(
            CartaProductoModel, CartaProductoModel.producto_id == ProductoModel.id
        ).join(
            CategoriaModel, CategoriaModel.id == ProductoModel.categoria_id
        ).filter(
            CartaProductoModel.carta_id == carta.id,
            ProductoModel.activo.is_(True),
            CategoriaModel.activo.is_(True),
            CategoriaModel.eliminado_en.is_(None),
        ).add_columns(CategoriaModel).order_by(
            CategoriaModel.orden.asc(), CategoriaModel.nombre.asc(), ProductoModel.orden.asc(), ProductoModel.nombre.asc()
        ).all()

        grupos = ModificadorQuerys(self.db, self.ctx).for_products([producto.id for producto, _ in rows])
        categorias = {}
        for producto, categoria in rows:
            grupo = categorias.setdefault(categoria.id, {"id": categoria.id, "nombre": categoria.nombre, "productos": []})
            grupo["productos"].append({
                "id": producto.id,
                "nombre": producto.nombre,
                "descripcion": producto.descripcion,
                "precio": producto.precio,
                "agotado": producto.agotado,
                "grupos": grupos.get(producto.id, []),
            })
        return list(categorias.values())

    def format_carta(self, carta, con_productos=False):
        data = {
            "id": carta.id,
            "nombre": carta.nombre,
            "activo": carta.activo,
            "productos_total": len(self.get_producto_ids(carta.id)),
            "zonas": [z.nombre for z in self.zonas_con_carta(carta.id)],
        }
        if con_productos:
            data["productos"] = self.get_producto_ids(carta.id)
        return data
