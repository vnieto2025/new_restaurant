from Utils.tools import Tools, CustomException, clean_text
from Querys.carta import CartaQuerys
from Models.carta_model import CartaModel


class Carta:
    """ Una carta es el conjunto de productos que ofrece una zona (doc 11) """

    def __init__(self, db, ctx: dict):
        self.ctx = ctx
        self.tools = Tools()
        self.querys = CartaQuerys(db, ctx)

    def list(self, data: dict):
        cartas = [self.querys.format_carta(c) for c in self.querys.list_cartas(data.get("todas") is True)]
        msg = "Listado de cartas." if cartas else "Aún no hay cartas."
        return self.tools.output(200, msg, cartas)

    def get(self, data: dict):
        carta = self.querys.get_own(CartaModel, data["carta_id"], "carta")
        return self.tools.output(200, "Datos de la carta.", self.querys.format_carta(carta, con_productos=True))

    def create(self, data: dict):

        nombre = clean_text(data["nombre"])
        if self.querys.name_exists(nombre):
            raise CustomException("Ya existe una carta con ese nombre.")

        carta_id = self.querys.insert_data(CartaModel, {"nombre": nombre}, commit=False)
        self.querys.set_productos(carta_id, self.clean_products(data))
        self.querys.commit()

        carta = self.querys.get_own(CartaModel, carta_id, "carta")
        return self.tools.output(201, "Carta creada.", self.querys.format_carta(carta, con_productos=True))

    # Cambiar la carta no afecta a órdenes ya creadas (RN-ZON-05)
    def update(self, data: dict):

        carta = self.querys.get_own(CartaModel, data["carta_id"], "carta")
        nombre = clean_text(data["nombre"])
        if self.querys.name_exists(nombre, exclude_id=carta.id):
            raise CustomException("Ya existe otra carta con ese nombre.")

        self.querys.update_data(CartaModel, carta.id, {"nombre": nombre}, "carta", commit=False)
        if "productos" in data:
            self.querys.set_productos(carta.id, self.clean_products(data))
        self.querys.commit()

        return self.tools.output(200, "Carta actualizada.", self.querys.format_carta(carta, con_productos=True))

    # Una zona siempre tiene una carta activa (RN-ZON-03)
    def change_status(self, data: dict):

        carta = self.querys.get_own(CartaModel, data["carta_id"], "carta")
        activo = data["activo"] is True
        if not activo:
            zonas = self.querys.zonas_con_carta(carta.id)
            if zonas:
                nombres = ", ".join(z.nombre for z in zonas)
                raise CustomException(f"La carta está asignada a: {nombres}. Asigne otra carta a esas zonas primero.")

        self.querys.update_data(CartaModel, carta.id, {"activo": activo}, "carta")
        return self.tools.output(200, "Carta activada." if activo else "Carta desactivada.")

    def clean_products(self, data: dict):
        ids = [int(p) for p in data.get("productos") or []]
        if set(ids) - self.querys.valid_productos(ids):
            raise CustomException("Alguno de los productos no existe.")
        return list(dict.fromkeys(ids))
