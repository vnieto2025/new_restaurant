from Utils.tools import Tools, CustomException
from Querys.base import Querys
from Querys.producto import ProductoQuerys
from Querys.modificador import ModificadorQuerys
from Models.producto_model import ProductoModel
from Models.categoria_model import CategoriaModel
from Models.punto_produccion_model import PuntoProduccionModel
from Models.impuesto_model import ImpuestoModel
from Models.grupo_modificador_model import GrupoModificadorModel
from Models.opcion_modificador_model import OpcionModificadorModel
from Models.receta_model import RecetaModel
from Models.receta_linea_model import RecetaLineaModel
from Models.restaurante_model import RestauranteModel

MAX_NOMBRE = 100


class CopiarProductos:
    """ Duplicar un producto para crear variantes y copiar la carta a otro restaurante de la empresa (docs 07 y 12) """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = ProductoQuerys(db, ctx)

    def duplicate(self, data: dict):
        original = self.querys.get_own(ProductoModel, data["producto_id"], "producto")
        nombre = self.free_name(original.nombre)
        producto_id = self.querys.insert_data(ProductoModel, {
            "categoria_id": original.categoria_id, "nombre": nombre, "descripcion": original.descripcion, "precio": original.precio,
            "punto_produccion_id": original.punto_produccion_id, "impuesto_id": original.impuesto_id, "orden": original.orden,
        }, commit=False)
        self.querys.set_cartas_producto(producto_id, self.querys.get_cartas_producto(original.id))
        modificadores = ModificadorQuerys(self.db, self.ctx)
        modificadores.set_grupos_producto(producto_id, modificadores.grupos_de_producto(original.id))
        self.copy_recipe(original.id, producto_id)
        self.querys.commit()
        return self.tools.output(201, f"Se creó {nombre}. Ajústale el nombre y el precio.",
                                 self.querys.format_producto(self.querys.get_own(ProductoModel, producto_id, "producto")))

    def free_name(self, nombre):
        ocupados = {p.nombre.lower() for p in self.querys.scoped(ProductoModel, include_deleted=True).all()}
        for numero in range(1, 100):
            sufijo = " (copia)" if numero == 1 else f" (copia {numero})"
            candidato = nombre[:MAX_NOMBRE - len(sufijo)] + sufijo
            if candidato.lower() not in ocupados:
                return candidato
        raise CustomException("Ya hay demasiadas copias de este producto.", 409)

    def copy_recipe(self, origen_id, destino_id):
        receta = self.querys.scoped(RecetaModel).filter(RecetaModel.producto_id == origen_id).first()
        if not receta:
            return
        nueva_id = self.querys.insert_data(RecetaModel, {"producto_id": destino_id, "rendimiento": receta.rendimiento,
                                                         "actualizado_por": self.ctx.get("usuario_id")}, commit=False)
        for linea in self.querys.scoped(RecetaLineaModel).filter(RecetaLineaModel.receta_id == receta.id).all():
            self.querys.insert_data(RecetaLineaModel, {"receta_id": nueva_id, "insumo_id": linea.insumo_id, "cantidad": linea.cantidad,
                                                       "merma": linea.merma}, commit=False)

    def copy_to_branch(self, data: dict):
        """ Copia a otro restaurante de la empresa. Lo que ya existe allá por nombre no se toca, así sus precios se conservan.
            Las recetas no se copian: dependen de los insumos de cada local. """
        if "admin_empresa" not in self.ctx.get("roles", []):
            raise CustomException("Solo el administrador de la empresa copia entre restaurantes.", 403)
        destino_id = int(data["restaurante_id"])
        destino = self.db.get(RestauranteModel, destino_id)
        if not destino or destino.empresa_id != self.ctx["empresa_id"] or destino_id == self.ctx["restaurante_id"]:
            raise CustomException("Elige otro restaurante de tu empresa.", 404)
        ids = {int(i) for i in data["productos"]}
        productos = [p for p in self.querys.scoped(ProductoModel).filter(ProductoModel.id.in_(ids or [0])).all()]
        if len(productos) != len(ids) or not productos:
            raise CustomException("Alguno de los productos no existe.", 404)

        ctx_alla = {**self.ctx, "restaurante_id": destino_id}
        allá = ProductoQuerys(self.db, ctx_alla)
        categorias = self.names(allá, CategoriaModel)
        puntos = self.names(allá, PuntoProduccionModel)
        impuestos = self.names(allá, ImpuestoModel)
        grupos = self.names(allá, GrupoModificadorModel)
        existentes = {p.nombre.lower() for p in allá.scoped(ProductoModel, include_deleted=True).all()}
        cartas = [c.id for c in allá.get_cartas()]
        modificadores_aca = ModificadorQuerys(self.db, self.ctx)
        modificadores_alla = ModificadorQuerys(self.db, ctx_alla)

        creados, omitidos, categorias_nuevas = 0, [], 0
        for producto in sorted(productos, key=lambda p: (p.orden, p.nombre)):
            if producto.nombre.lower() in existentes:
                omitidos.append(producto.nombre)
                continue
            categoria = self.db.get(CategoriaModel, producto.categoria_id)
            categoria_id = categorias.get(categoria.nombre.lower())
            if not categoria_id:
                categoria_id = allá.insert_data(CategoriaModel, {"nombre": categoria.nombre, "orden": categoria.orden}, commit=False)
                categorias[categoria.nombre.lower()] = categoria_id
                categorias_nuevas += 1
            nuevo_id = allá.insert_data(ProductoModel, {
                "categoria_id": categoria_id, "nombre": producto.nombre, "descripcion": producto.descripcion, "precio": producto.precio,
                "orden": producto.orden, "activo": producto.activo,
                # Se enlaza con el punto y el impuesto del mismo nombre; si allá no existen, usa los de su categoría o el de defecto
                "punto_produccion_id": self.same_name(PuntoProduccionModel, producto.punto_produccion_id, puntos),
                "impuesto_id": self.same_name(ImpuestoModel, producto.impuesto_id, impuestos),
            }, commit=False)
            allá.set_cartas_producto(nuevo_id, cartas)
            grupo_ids = [self.copy_group(allá, g, grupos) for g in modificadores_aca.grupos_de_producto(producto.id)]
            modificadores_alla.set_grupos_producto(nuevo_id, grupo_ids)
            existentes.add(producto.nombre.lower())
            creados += 1
        self.querys.audit("productos_copiados", "restaurante", destino_id, despues={
            "hacia": destino.nombre, "creados": creados, "omitidos": len(omitidos)}, commit=False)
        self.querys.commit()
        return self.tools.output(200, f"{destino.nombre}. Copiados: {creados}. Ya existían: {len(omitidos)}.",
                                 {"creados": creados, "omitidos": omitidos, "categorias_nuevas": categorias_nuevas})

    def names(self, querys: Querys, model):
        return {f.nombre.lower(): f.id for f in querys.scoped(model).all()}

    def same_name(self, model, origen_id, destino):
        if not origen_id:
            return None
        return destino.get(self.db.get(model, origen_id).nombre.lower())

    def copy_group(self, allá, grupo_id, grupos):
        grupo = self.db.get(GrupoModificadorModel, grupo_id)
        existente = grupos.get(grupo.nombre.lower())
        if existente:
            return existente
        nuevo_id = allá.insert_data(GrupoModificadorModel, {"nombre": grupo.nombre, "minimo": grupo.minimo, "maximo": grupo.maximo,
                                                            "activo": grupo.activo}, commit=False)
        for opcion in self.querys.scoped(OpcionModificadorModel).filter(OpcionModificadorModel.grupo_id == grupo.id).all():
            allá.insert_data(OpcionModificadorModel, {"grupo_id": nuevo_id, "nombre": opcion.nombre, "precio_extra": opcion.precio_extra,
                                                      "orden": opcion.orden, "activo": opcion.activo}, commit=False)
        grupos[grupo.nombre.lower()] = nuevo_id
        return nuevo_id
