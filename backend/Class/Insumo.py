from decimal import Decimal, InvalidOperation
from Utils.tools import Tools, CustomException, clean_text
from Querys.inventario import InventarioQuerys, dec
from Models.insumo_model import InsumoModel, UNIDADES
from Models.insumo_presentacion_model import InsumoPresentacionModel

MAX_PRESENTACIONES = 6


def cantidad(valor, campo="cantidad", permitir_negativo=False, permitir_cero=False):
    """ Cantidades en unidad base con hasta 3 decimales """
    try:
        numero = Decimal(str(valor).replace(",", ".")).quantize(Decimal("0.001"))
    except (InvalidOperation, ValueError):
        raise CustomException(f"La {campo} no es válida.")
    if (numero < 0 and not permitir_negativo) or (numero == 0 and not permitir_cero) or abs(numero) > Decimal("1000000000"):
        raise CustomException(f"La {campo} no es válida.")
    return numero


class Insumo:
    """ Insumos, productos de reventa, empaques y preparaciones (doc 22) """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = InventarioQuerys(db, ctx)

    def list(self, data: dict):
        insumos = self.querys.insumos(data.get("todos") is True, data.get("categoria"), clean_text(data.get("buscar")))
        result = [self.format(i) for i in insumos]
        return self.tools.output(200, "Insumos." if result else "Aún no hay insumos.", result)

    def create(self, data: dict):
        fields = self.clean_data(data)
        if self.name_exists(fields["nombre"]):
            raise CustomException("Ya existe un insumo con ese nombre.")
        insumo_id = self.querys.insert_data(InsumoModel, fields, commit=False)
        self.set_presentations(insumo_id, data.get("presentaciones") or [])
        self.db.commit()
        return self.tools.output(201, "Insumo creado.", self.format(self.querys.get_own(InsumoModel, insumo_id, "insumo")))

    # El stock y el costo no se editan aquí: cambian solo con movimientos (RN-INV-01)
    def update(self, data: dict):
        insumo = self.querys.get_own(InsumoModel, data["insumo_id"], "insumo")
        fields = self.clean_data(data)
        if self.name_exists(fields["nombre"], exclude_id=insumo.id):
            raise CustomException("Ya existe otro insumo con ese nombre.")
        if fields["unidad"] != insumo.unidad and self.querys.tiene_movimientos(insumo.id):
            raise CustomException("El insumo ya tiene movimientos: no se puede cambiar su unidad.")
        if insumo.es_preparacion and not fields["es_preparacion"] and self.querys.receta_de_insumo(insumo.id):
            raise CustomException("Tiene receta de preparación. Elimínala antes de convertirlo en insumo comprado.")
        self.querys.update_data(InsumoModel, insumo.id, fields, "insumo", commit=False)
        if "presentaciones" in data:
            self.set_presentations(insumo.id, data.get("presentaciones") or [])
        self.db.commit()
        return self.tools.output(200, "Insumo actualizado.", self.format(insumo))

    # Un insumo con movimientos no se borra: se inactiva (RN-INV-04)
    def change_status(self, data: dict):
        insumo = self.querys.get_own(InsumoModel, data["insumo_id"], "insumo")
        activo = data["activo"] is True
        self.querys.update_data(InsumoModel, insumo.id, {"activo": activo}, "insumo")
        return self.tools.output(200, "Insumo activado." if activo else "Insumo inactivado.")

    def set_presentations(self, insumo_id, presentaciones: list):
        if len(presentaciones) > MAX_PRESENTACIONES:
            raise CustomException(f"Máximo {MAX_PRESENTACIONES} presentaciones por insumo.")
        self.querys.scoped(InsumoPresentacionModel).filter(InsumoPresentacionModel.insumo_id == insumo_id).delete(
            synchronize_session=False)
        nombres = set()
        for p in presentaciones:
            nombre = clean_text(p.get("nombre"))
            if not nombre:
                continue
            if nombre.lower() in nombres:
                raise CustomException(f"La presentación {nombre} está repetida.")
            nombres.add(nombre.lower())
            self.querys.insert_data(InsumoPresentacionModel, {
                "insumo_id": insumo_id, "nombre": nombre[:60], "factor": cantidad(p.get("factor"), "equivalencia"),
            }, commit=False)

    def format(self, insumo):
        stock, minimo = dec(insumo.stock), dec(insumo.stock_minimo)
        costo = self.querys.costo_unitario(insumo)
        return {
            "id": insumo.id,
            "nombre": insumo.nombre,
            "codigo": insumo.codigo,
            "categoria": insumo.categoria,
            "unidad": insumo.unidad,
            "unidad_texto": UNIDADES[insumo.unidad],
            "es_preparacion": insumo.es_preparacion,
            "tiene_receta": bool(insumo.es_preparacion and self.querys.receta_de_insumo(insumo.id)),
            "costo_promedio": float(insumo.costo_promedio),
            "costo_unitario": float(costo),
            "stock": float(stock),
            "stock_minimo": float(minimo),
            "valor_stock": int(max(stock, Decimal(0)) * costo),
            "alerta": "negativo" if stock < 0 else ("bajo" if minimo > 0 and stock <= minimo else None),
            "ubicacion": insumo.ubicacion,
            "activo": insumo.activo,
            "presentaciones": [{"id": p.id, "nombre": p.nombre, "factor": float(p.factor)}
                               for p in self.querys.presentaciones(insumo.id)],
        }

    def clean_data(self, data: dict):
        if data["unidad"] not in UNIDADES:
            raise CustomException("La unidad debe ser gramos, mililitros o unidades.")
        return {
            "nombre": clean_text(data["nombre"]),
            "codigo": clean_text(data.get("codigo")),
            "categoria": clean_text(data.get("categoria")),
            "unidad": data["unidad"],
            "es_preparacion": data.get("es_preparacion") is True,
            "stock_minimo": cantidad(data.get("stock_minimo") or 0, "existencia mínima", permitir_cero=True),
            "ubicacion": clean_text(data.get("ubicacion")),
        }

    def name_exists(self, nombre, exclude_id=None):
        query = self.querys.scoped(InsumoModel, include_deleted=True).filter(InsumoModel.nombre.ilike(nombre))
        if exclude_id:
            query = query.filter(InsumoModel.id != exclude_id)
        return query.first() is not None
