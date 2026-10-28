from Utils.tools import Tools, CustomException, clean_text
from Querys.modificador import ModificadorQuerys
from Models.grupo_modificador_model import GrupoModificadorModel
from Models.opcion_modificador_model import OpcionModificadorModel

MAX_OPCIONES = 30
MAX_PRECIO_EXTRA = 10_000_000


class Modificador:
    """ Grupos de modificadores: adicionales, quitar ingredientes, punto de cocción (doc 12, sección 3) """

    def __init__(self, db, ctx: dict):
        self.ctx = ctx
        self.tools = Tools()
        self.querys = ModificadorQuerys(db, ctx)

    def list(self, data: dict):
        grupos = [self.querys.format_grupo(g) for g in self.querys.list_grupos(data.get("todos") is True)]
        msg = "Listado de modificadores." if grupos else "Aún no hay grupos de modificadores."
        return self.tools.output(200, msg, grupos)

    def create(self, data: dict):

        fields = self.clean_data(data)
        if self.querys.name_exists(fields["nombre"]):
            raise CustomException("Ya existe un grupo con ese nombre.")

        grupo_id = self.querys.insert_data(GrupoModificadorModel, fields, commit=False)
        for orden, opcion in enumerate(self.clean_options(data, fields)):
            self.querys.insert_data(OpcionModificadorModel, {**opcion, "grupo_id": grupo_id, "orden": orden}, commit=False)
        self.querys.commit()

        grupo = self.querys.get_own(GrupoModificadorModel, grupo_id, "grupo")
        return self.tools.output(201, "Grupo de modificadores creado.", self.querys.format_grupo(grupo))

    # Las opciones quitadas se desactivan: las órdenes ya hechas conservan su copia (RG-13)
    def update(self, data: dict):

        grupo = self.querys.get_own(GrupoModificadorModel, data["grupo_id"], "grupo")
        fields = self.clean_data(data)
        if self.querys.name_exists(fields["nombre"], exclude_id=grupo.id):
            raise CustomException("Ya existe otro grupo con ese nombre.")
        opciones = self.clean_options(data, fields)

        self.querys.update_data(GrupoModificadorModel, grupo.id, fields, "grupo", commit=False)
        actuales = {o.id: o for o in self.querys.opciones_de(grupo.id, incluir_inactivas=True)}
        conservadas = set()
        for orden, opcion in enumerate(opciones):
            opcion_id = opcion.pop("id", None)
            if opcion_id and int(opcion_id) in actuales:
                existente = actuales[int(opcion_id)]
                existente.nombre, existente.precio_extra = opcion["nombre"], opcion["precio_extra"]
                existente.orden, existente.activo = orden, True
                conservadas.add(existente.id)
            else:
                self.querys.insert_data(OpcionModificadorModel, {**opcion, "grupo_id": grupo.id, "orden": orden},
                                        commit=False)
        for opcion_id, opcion in actuales.items():
            if opcion_id not in conservadas:
                opcion.activo = False
        self.querys.commit()

        return self.tools.output(200, "Grupo de modificadores actualizado.", self.querys.format_grupo(grupo))

    def change_status(self, data: dict):
        grupo = self.querys.get_own(GrupoModificadorModel, data["grupo_id"], "grupo")
        activo = data["activo"] is True
        self.querys.update_data(GrupoModificadorModel, grupo.id, {"activo": activo}, "grupo")
        return self.tools.output(200, "Grupo activado." if activo else "Grupo desactivado: ya no aparece en los productos.")

    def clean_data(self, data: dict):
        minimo, maximo = int(data.get("minimo") or 0), int(data.get("maximo") or 1)
        if minimo < 0 or maximo < 1 or minimo > maximo:
            raise CustomException("El mínimo debe ser menor o igual al máximo, y el máximo al menos 1.")
        return {"nombre": clean_text(data["nombre"]), "minimo": minimo, "maximo": maximo}

    def clean_options(self, data: dict, fields: dict):
        opciones = data.get("opciones") or []
        if not opciones:
            raise CustomException("El grupo necesita al menos una opción.")
        if len(opciones) > MAX_OPCIONES:
            raise CustomException(f"Un grupo puede tener máximo {MAX_OPCIONES} opciones.")

        result, nombres = [], set()
        for opcion in opciones:
            nombre = clean_text(opcion.get("nombre"))
            if not nombre:
                raise CustomException("Todas las opciones necesitan nombre.")
            if nombre.lower() in nombres:
                raise CustomException(f"La opción {nombre} está repetida.")
            nombres.add(nombre.lower())
            precio = int(opcion.get("precio_extra") or 0)
            if precio < 0 or precio > MAX_PRECIO_EXTRA:
                raise CustomException(f"El precio extra de {nombre} no es válido.")
            result.append({"id": opcion.get("id"), "nombre": nombre, "precio_extra": precio})

        if fields["minimo"] > len(result):
            raise CustomException("El mínimo no puede ser mayor que la cantidad de opciones.")
        return result
