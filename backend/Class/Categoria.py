from Utils.tools import Tools, CustomException, clean_text
from Querys.categoria import CategoriaQuerys
from Models.categoria_model import CategoriaModel
from Models.punto_produccion_model import PuntoProduccionModel
from Models.impuesto_model import ImpuestoModel


class Categoria:

    def __init__(self, db, ctx: dict):
        self.ctx = ctx
        self.tools = Tools()
        self.querys = CategoriaQuerys(db, ctx)

    def list(self, data: dict):
        categorias = [self.querys.format_categoria(c) for c in self.querys.list_categorias(data.get("todas") is True)]
        msg = "Listado de categorías." if categorias else "Aún no hay categorías."
        return self.tools.output(200, msg, categorias)

    def create(self, data: dict):

        fields = self.clean_data(data)
        if self.querys.name_exists(fields["nombre"]):
            raise CustomException("Ya existe una categoría con ese nombre.")

        categoria_id = self.querys.insert_data(CategoriaModel, fields)
        categoria = self.querys.get_own(CategoriaModel, categoria_id, "categoría")
        return self.tools.output(201, "Categoría creada.", self.querys.format_categoria(categoria))

    def update(self, data: dict):

        categoria = self.querys.get_own(CategoriaModel, data["categoria_id"], "categoría")
        fields = self.clean_data(data)
        if self.querys.name_exists(fields["nombre"], exclude_id=categoria.id):
            raise CustomException("Ya existe otra categoría con ese nombre.")

        categoria = self.querys.update_data(CategoriaModel, categoria.id, fields, "categoría")
        return self.tools.output(200, "Categoría actualizada.", self.querys.format_categoria(categoria))

    # Una categoría inactiva oculta sus productos de todas las cartas
    def change_status(self, data: dict):

        categoria = self.querys.get_own(CategoriaModel, data["categoria_id"], "categoría")
        activo = data["activo"] is True
        self.querys.update_data(CategoriaModel, categoria.id, {"activo": activo}, "categoría")
        return self.tools.output(200, "Categoría activada." if activo else "Categoría desactivada.")

    def clean_data(self, data: dict):
        punto_id = data.get("punto_produccion_id")
        if punto_id:
            punto_id = self.querys.get_own(PuntoProduccionModel, punto_id, "punto de producción").id
        fields = {
            "nombre": clean_text(data["nombre"]),
            "orden": int(data.get("orden") or 0),
            "punto_produccion_id": punto_id or None,
        }
        if "impuesto_id" in data:
            impuesto_id = data.get("impuesto_id")
            fields["impuesto_id"] = self.querys.get_own(ImpuestoModel, impuesto_id, "impuesto").id if impuesto_id else None
        return fields
