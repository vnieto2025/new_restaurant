from Utils.tools import Tools, CustomException, clean_text
from Utils.realtime import realtime
from Querys.producto import ProductoQuerys
from Querys.modificador import ModificadorQuerys
from Querys.combo import ComboQuerys
from Models.producto_model import ProductoModel
from Models.categoria_model import CategoriaModel
from Models.punto_produccion_model import PuntoProduccionModel
from Models.impuesto_model import ImpuestoModel

MAX_PRECIO = 100_000_000
MAX_COMPONENTES = 10
MAX_OPCIONES = 20
TIPOS_PRODUCTO = ["simple", "combo"]


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

        fields["tipo"] = self.clean_type(data.get("tipo") or "simple")
        producto_id = self.querys.insert_data(ProductoModel, fields, commit=False)
        self.querys.set_cartas_producto(producto_id, self.clean_menus(data))
        if fields["tipo"] == "combo":
            ComboQuerys(self.querys.db, self.ctx).set_componentes(producto_id, self.clean_components(data, producto_id))
        else:
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

        fields["tipo"] = self.clean_type(data.get("tipo") or producto.tipo)
        if fields["tipo"] == "combo" and producto.tipo != "combo":
            usado = ComboQuerys(self.querys.db, self.ctx).combos_que_usan(producto.id)
            if usado:
                raise CustomException(f"{producto.nombre} está dentro de {', '.join(usado)}: un combo no puede ir dentro de otro.")
        self.querys.update_data(ProductoModel, producto.id, fields, "producto", commit=False)
        if "cartas" in data:
            self.querys.set_cartas_producto(producto.id, self.clean_menus(data))
        combos = ComboQuerys(self.querys.db, self.ctx)
        if fields["tipo"] == "combo":
            if "componentes" in data or producto.tipo != "combo":
                combos.set_componentes(producto.id, self.clean_components(data, producto.id))
            ModificadorQuerys(self.querys.db, self.ctx).set_grupos_producto(producto.id, [])
        else:
            combos.set_componentes(producto.id, [])
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
        if "alergenos" in data:
            fields["alergenos"] = clean_text(data.get("alergenos"))
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

    def clean_type(self, tipo):
        if tipo not in TIPOS_PRODUCTO:
            raise CustomException("El tipo debe ser producto o combo.")
        return tipo

    def clean_components(self, data: dict, combo_id):
        """ Cada componente con al menos una opción. Las opciones son productos simples del restaurante:
            un combo dentro de otro haría imposible saber qué se prepara y qué se cobra. """
        componentes = data.get("componentes") or []
        if not componentes:
            raise CustomException("Un combo necesita al menos un componente, por ejemplo «Bebida».")
        if len(componentes) > MAX_COMPONENTES:
            raise CustomException(f"Un combo puede tener máximo {MAX_COMPONENTES} componentes.")
        limpios = []
        for posicion, componente in enumerate(componentes, start=1):
            nombre = clean_text(componente.get("nombre"))
            if not nombre or len(nombre) > 60:
                raise CustomException(f"Escribe el nombre del componente {posicion}, por ejemplo «Bebida».")
            cantidad = int(componente.get("cantidad") or 1)
            if not 1 <= cantidad <= 10:
                raise CustomException(f"La cantidad de {nombre} debe estar entre 1 y 10.")
            opciones = componente.get("opciones") or []
            if not opciones or len(opciones) > MAX_OPCIONES:
                raise CustomException(f"Elige de 1 a {MAX_OPCIONES} productos para {nombre}.")
            vistos, limpias = set(), []
            for opcion in opciones:
                producto = self.querys.get_own(ProductoModel, opcion.get("producto_id"), "producto")
                if producto.id == combo_id or producto.tipo == "combo":
                    raise CustomException(f"{producto.nombre} es un combo: un combo no puede ir dentro de otro.")
                if producto.id in vistos:
                    raise CustomException(f"{producto.nombre} está repetido en {nombre}.")
                extra = int(opcion.get("precio_extra") or 0)
                if extra < 0 or extra > MAX_PRECIO:
                    raise CustomException(f"El valor extra de {producto.nombre} no es válido.")
                vistos.add(producto.id)
                limpias.append({"producto_id": producto.id, "precio_extra": extra})
            limpios.append({"nombre": nombre, "cantidad": cantidad, "opciones": limpias})
        return limpios

    def clean_menus(self, data: dict):
        if data.get("cartas") is None:
            return [carta.id for carta in self.querys.get_cartas()]
        ids = [int(c) for c in data["cartas"]]
        validas = {carta.id for carta in self.querys.get_cartas(ids)}
        if set(ids) - validas:
            raise CustomException("Alguna de las cartas no existe.")
        return list(dict.fromkeys(ids))
