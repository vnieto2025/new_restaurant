from Querys.base import Querys
from Models.grupo_modificador_model import GrupoModificadorModel
from Models.opcion_modificador_model import OpcionModificadorModel
from Models.producto_grupo_model import ProductoGrupoModel
from sqlalchemy import func


class ModificadorQuerys(Querys):

    def list_grupos(self, incluir_inactivos=False):
        query = self.scoped(GrupoModificadorModel)
        if not incluir_inactivos:
            query = query.filter(GrupoModificadorModel.activo.is_(True))
        return query.order_by(GrupoModificadorModel.nombre.asc()).all()

    def name_exists(self, nombre: str, exclude_id=None):
        query = self.scoped(GrupoModificadorModel, include_deleted=True).filter(
            func.lower(GrupoModificadorModel.nombre) == nombre.lower())
        if exclude_id:
            query = query.filter(GrupoModificadorModel.id != exclude_id)
        return query.first() is not None

    def opciones_de(self, grupo_id, incluir_inactivas=False):
        query = self.scoped(OpcionModificadorModel).filter(OpcionModificadorModel.grupo_id == grupo_id)
        if not incluir_inactivas:
            query = query.filter(OpcionModificadorModel.activo.is_(True))
        return query.order_by(OpcionModificadorModel.orden.asc(), OpcionModificadorModel.id.asc()).all()

    def count_productos(self, grupo_id):
        return self.scoped(ProductoGrupoModel).filter(ProductoGrupoModel.grupo_id == grupo_id).count()

    def valid_grupos(self, ids: list):
        return {g.id for g in self.scoped(GrupoModificadorModel).filter(GrupoModificadorModel.id.in_(ids or [0])).all()}

    def grupos_de_producto(self, producto_id):
        return [g for (g,) in self.scoped(ProductoGrupoModel).with_entities(ProductoGrupoModel.grupo_id).filter(
            ProductoGrupoModel.producto_id == producto_id).order_by(ProductoGrupoModel.orden.asc()).all()]

    def set_grupos_producto(self, producto_id, grupo_ids: list):
        self.scoped(ProductoGrupoModel).filter(ProductoGrupoModel.producto_id == producto_id).delete(synchronize_session=False)
        for orden, grupo_id in enumerate(grupo_ids):
            self.insert_data(ProductoGrupoModel, {"producto_id": producto_id, "grupo_id": grupo_id, "orden": orden},
                             commit=False)
        self.db.flush()

    def for_products(self, producto_ids: list):
        """ Grupos activos con sus opciones activas por producto, en dos consultas.
            Lo usan la carta (para mostrar) y la orden (para validar y cobrar). """
        relaciones = self.scoped(ProductoGrupoModel).join(
            GrupoModificadorModel, GrupoModificadorModel.id == ProductoGrupoModel.grupo_id
        ).filter(
            ProductoGrupoModel.producto_id.in_(producto_ids or [0]),
            GrupoModificadorModel.activo.is_(True),
            GrupoModificadorModel.eliminado_en.is_(None),
        ).add_columns(GrupoModificadorModel).order_by(ProductoGrupoModel.orden.asc()).all()

        grupo_ids = {grupo.id for _, grupo in relaciones}
        opciones = {}
        for opcion in self.scoped(OpcionModificadorModel).filter(
            OpcionModificadorModel.grupo_id.in_(grupo_ids or [0]),
            OpcionModificadorModel.activo.is_(True),
        ).order_by(OpcionModificadorModel.orden.asc(), OpcionModificadorModel.id.asc()).all():
            opciones.setdefault(opcion.grupo_id, []).append({
                "id": opcion.id, "nombre": opcion.nombre, "precio_extra": opcion.precio_extra,
            })

        result = {}
        for relacion, grupo in relaciones:
            if not opciones.get(grupo.id):
                continue
            result.setdefault(relacion.producto_id, []).append({
                "id": grupo.id,
                "nombre": grupo.nombre,
                "minimo": grupo.minimo,
                "maximo": grupo.maximo,
                "opciones": opciones[grupo.id],
            })
        return result

    def format_grupo(self, grupo):
        return {
            "id": grupo.id,
            "nombre": grupo.nombre,
            "minimo": grupo.minimo,
            "maximo": grupo.maximo,
            "activo": grupo.activo,
            "productos": self.count_productos(grupo.id),
            "opciones": [
                {"id": o.id, "nombre": o.nombre, "precio_extra": o.precio_extra, "orden": o.orden}
                for o in self.opciones_de(grupo.id)
            ],
        }
