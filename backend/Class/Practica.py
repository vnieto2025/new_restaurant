from Utils.tools import Tools, CustomException
from Utils import practica
from Querys.base import Querys
from Querys.inventario import InventarioQuerys
from Models.restaurante_model import RestauranteModel
from Models.orden_model import OrdenModel

# Lo que el restaurante de práctica toma del real; el resto (alertas, resumen, asistente) arranca vacío
CAMPOS = ["tipo", "direccion", "telefono", "zona_horaria", "hora_inicio_jornada", "moneda", "mensaje_carta",
          "propina_sugerida", "reiniciar_agotados", "aviso_datos", "aviso_version", "politica_url"]


class Practica:
    """ Restaurante de práctica (doc 33, sección 7; ADR-053): el personal entrena con la carta, las mesas y
        el inventario reales sin que nada cuente en ventas, caja, inventario ni facturación del real. """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = Querys(db, ctx)

    def restaurantes(self, lock=False):
        """ (real, práctica) a partir del restaurante de la petición, que puede ser cualquiera de los dos """
        actual = self.db.get(RestauranteModel, self.ctx["restaurante_id"])
        real = self.db.get(RestauranteModel, actual.practica_de) if actual.practica_de else actual
        query = self.db.query(RestauranteModel).filter(RestauranteModel.practica_de == real.id)
        return real, (query.with_for_update() if lock else query).first()

    def get(self, data: dict = None):
        real, copia = self.restaurantes()
        return self.tools.output(200, "Restaurante de práctica.", self.format(real, copia))

    def create(self, data: dict = None):
        real, copia = self.restaurantes(lock=True)
        if copia:
            raise CustomException("Este restaurante ya tiene su práctica. Puedes reiniciarla para empezar de cero.", 409)
        copia = RestauranteModel({"empresa_id": real.empresa_id, "nombre": f"{real.nombre} · Práctica"[:150], "estado": "activo",
                                  "practica_de": real.id, **{c: getattr(real, c) for c in CAMPOS}})
        self.db.add(copia)
        self.db.flush()
        resultado = self.fill(real, copia)
        self.audit(real, "practica_creada", copia, resultado)
        self.db.commit()
        return self.tools.output(201, "Restaurante de práctica listo.", self.format(real, copia))

    def reset(self, data: dict = None):
        real, copia = self.restaurantes(lock=True)
        if not copia:
            raise CustomException("Este restaurante todavía no tiene práctica.", 404)
        practica.limpiar(self.db, copia)
        for campo in CAMPOS:
            setattr(copia, campo, getattr(real, campo))
        resultado = self.fill(real, copia)
        self.audit(real, "practica_reiniciada", copia, resultado)
        self.db.commit()
        return self.tools.output(200, "Práctica reiniciada: quedó como el restaurante real, sin órdenes ni cobros.",
                                 self.format(real, copia))

    def fill(self, real, copia):
        resultado = practica.clonar(self.db, real.id, copia.id)
        inventario = InventarioQuerys(self.db, {**self.ctx, "restaurante_id": copia.id, "practica": True})
        for insumo_id, cantidad in resultado["existencias"].items():
            inventario.mover(insumo_id, "ajuste", cantidad, motivo="Existencia copiada del restaurante real")
        return resultado["copiadas"]

    # Queda en la auditoría del real: la de la práctica se borra al reiniciar
    def audit(self, real, accion, copia, copiadas):
        Querys(self.db, {**self.ctx, "restaurante_id": real.id, "practica": False}).audit(
            accion, "restaurante", copia.id, despues={"productos": copiadas.get("producto", 0), "mesas": copiadas.get("mesa", 0)},
            commit=False)

    def format(self, real, copia):
        ordenes = self.db.query(OrdenModel).filter(OrdenModel.restaurante_id == copia.id).count() if copia else 0
        return {
            "real": {"id": real.id, "nombre": real.nombre},
            "practica": {"id": copia.id, "nombre": copia.nombre, "creada_en": copia.creado_en, "ordenes": ordenes} if copia else None,
            "en_practica": bool(self.ctx.get("practica")),
            "sin_modulos": sorted(practica.SIN_MODULOS & self.modulos_reales()),
        }

    def modulos_reales(self):
        from Utils.contexto import modulos_activos
        real, _ = self.restaurantes()
        return modulos_activos(self.db, real)[0]
