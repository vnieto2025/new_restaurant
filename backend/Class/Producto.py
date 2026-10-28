from Utils.tools import Tools, CustomException, clean_text
from Utils.realtime import realtime
from Querys.producto import ProductoQuerys
from Querys.modificador import ModificadorQuerys
from Models.producto_model import ProductoModel
from Models.categoria_model import CategoriaModel
from Models.punto_produccion_model import PuntoProduccionModel
from Models.impuesto_model import ImpuestoModel

MAX_PRECIO = 100_000_000


class Producto:

    def __init__(self, db, ctx: dict):
        self.ctx = ctx
        self.tools = Tools()
        self.querys = ProductoQuerys(db, ctx)

    def list(self, data: dict):
        productos = self.querys.list_productos(data.get("categoria_id"), data.get("buscar"), data.get("todos") is True)
        result = [self.querys.format_producto(p) for p in productos]
        msg = "Listado de productos." if result else "No hay productos que mostrar."
        return self.tools.output(200, msg, result)

    # Function for create a product. Si no se indican cartas, queda en todas.
    def create(self, data: dict):

        fields = self.clean_data(data)
        if self.querys.name_exists(fields["nombre"]):
            raise CustomException("Ya existe un producto con ese nombre.")

        producto_id = self.querys.insert_data(ProductoModel, fields, commit=False)
        self.querys.set_cartas_producto(producto_id, self.clean_menus(data))
        self.set_groups(producto_id, data)
        self.querys.commit()

        producto = self.querys.get_own(ProductoModel, producto_id, "producto")
        return self.tools.output(201, "Producto creado.", self.querys.format_producto(producto))

    # Las órdenes ya creadas conservan nombre y precio (RG-13)
    def update(self, data: dict):

        producto = self.querys.get_own(ProductoModel, data["producto_id"], "producto")
        fields = self.clean_data(data)
        if self.querys.name_exists(fields["nombre"], exclude_id=producto.id):
            raise CustomException("Ya existe otro producto con ese nombre.")

        precio_anterior = producto.precio
        impuesto_anterior = producto.impuesto_id
        if fields["precio"] != precio_anterior and "catalogo.precios" not in self.ctx["permisos"]:
            raise CustomException("No tiene permiso para cambiar precios.", 403)

        self.querys.update_data(ProductoModel, producto.id, fields, "producto", commit=False)
        if "cartas" in data:
            self.querys.set_cartas_producto(producto.id, self.clean_menus(data))
        if "grupos" in data:
            self.set_groups(producto.id, data)

        # Los cambios de precio se auditan siempre (RG-14)
        if fields["precio"] != precio_anterior:
            self.querys.audit("precio_cambiado", "producto", producto.id,
                              antes={"precio": precio_anterior}, despues={"precio": fields["precio"]}, commit=False)
        if fields.get("impuesto_id", impuesto_anterior) != impuesto_anterior:
            self.querys.audit("impuesto_producto", "producto", producto.id, antes={"impuesto_id": impuesto_anterior},
                              despues={"impuesto_id": fields["impuesto_id"]}, commit=False)
        self.querys.commit()

        return self.tools.output(200, "Producto actualizado.", self.querys.format_producto(producto))

    def change_status(self, data: dict):

        producto = self.querys.get_own(ProductoModel, data["producto_id"], "producto")
        activo = data["activo"] is True
        self.querys.update_data(ProductoModel, producto.id, {"activo": activo}, "producto")
        return self.tools.output(200, "Producto activado." if activo else "Producto desactivado.")

    # Producto agotado: deja de poder pedirse en todas las cartas (doc 11)
    def sold_out(self, data: dict):

        producto = self.querys.get_own(ProductoModel, data["producto_id"], "producto")
        agotado = data["agotado"] is True
        self.querys.update_data(ProductoModel, producto.id, {"agotado": agotado}, "producto", commit=False)
        self.querys.audit("producto_agotado" if agotado else "producto_disponible", "producto", producto.id)
        realtime.publish(self.ctx["restaurante_id"], ["ordenes"],
                         {"tipo": "producto.agotado", "producto_id": producto.id, "agotado": agotado})

        msg = f"{producto.nombre} marcado como agotado." if agotado else f"{producto.nombre} disponible de nuevo."
        return self.tools.output(200, msg, self.querys.format_producto(producto))

    def clean_data(self, data: dict):

        precio = int(data["precio"])
        if precio < 0 or precio > MAX_PRECIO:
            raise CustomException("El precio no es válido.")

        categoria = self.querys.get_own(CategoriaModel, data["categoria_id"], "categoría")
        punto_id = data.get("punto_produccion_id")
        if punto_id:
            punto_id = self.querys.get_own(PuntoProduccionModel, punto_id, "punto de producción").id

        fields = {
            "categoria_id": categoria.id,
            "nombre": clean_text(data["nombre"]),
            "descripcion": clean_text(data.get("descripcion")),
            "precio": precio,
            "punto_produccion_id": punto_id or None,
            "orden": int(data.get("orden") or 0),
        }
        # Vacío = el de la categoría o el impuesto por defecto (doc 21A, sección 2)
        if "impuesto_id" in data:
            impuesto_id = data.get("impuesto_id")
            fields["impuesto_id"] = self.querys.get_own(ImpuestoModel, impuesto_id, "impuesto").id if impuesto_id else None
        return fields

    # Grupos de modificadores que se ofrecen con el producto, en el orden indicado
    def set_groups(self, producto_id, data: dict):
        ids = list(dict.fromkeys(int(g) for g in data.get("grupos") or []))
        modificadores = ModificadorQuerys(self.querys.db, self.ctx)
        if set(ids) - modificadores.valid_grupos(ids):
            raise CustomException("Alguno de los grupos de modificadores no existe.")
        modificadores.set_grupos_producto(producto_id, ids)

    def clean_menus(self, data: dict):
        if data.get("cartas") is None:
            return [carta.id for carta in self.querys.get_cartas()]
        ids = [int(c) for c in data["cartas"]]
        validas = {carta.id for carta in self.querys.get_cartas(ids)}
        if set(ids) - validas:
            raise CustomException("Alguna de las cartas no existe.")
        return list(dict.fromkeys(ids))
