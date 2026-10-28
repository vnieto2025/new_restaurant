from Querys.base import Querys
from Models.categoria_model import CategoriaModel
from Models.producto_model import ProductoModel
from Models.punto_produccion_model import PuntoProduccionModel
from sqlalchemy import func


class CategoriaQuerys(Querys):

    def list_categorias(self, incluir_inactivas=False):
        query = self.scoped(CategoriaModel)
        if not incluir_inactivas:
            query = query.filter(CategoriaModel.activo.is_(True))
        return query.order_by(CategoriaModel.orden.asc(), CategoriaModel.nombre.asc()).all()

    def name_exists(self, nombre: str, exclude_id=None):
        query = self.scoped(CategoriaModel, include_deleted=True).filter(func.lower(CategoriaModel.nombre) == nombre.lower())
        if exclude_id:
            query = query.filter(CategoriaModel.id != exclude_id)
        return query.first() is not None

    def count_productos(self, categoria_id):
        return self.scoped(ProductoModel).filter(
            ProductoModel.categoria_id == categoria_id, ProductoModel.activo.is_(True)
        ).count()

    def format_categoria(self, categoria):
        punto = self.db.get(PuntoProduccionModel, categoria.punto_produccion_id) if categoria.punto_produccion_id else None
        return {
            "id": categoria.id,
            "nombre": categoria.nombre,
            "orden": categoria.orden,
            "punto_produccion_id": categoria.punto_produccion_id,
            "punto_produccion": punto.nombre if punto else None,
            "impuesto_id": categoria.impuesto_id,
            "activo": categoria.activo,
            "productos": self.count_productos(categoria.id),
        }
