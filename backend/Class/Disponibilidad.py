from decimal import Decimal
from Utils.tools import Tools, CustomException
from Querys.inventario import InventarioQuerys
from Querys.combo import ComboQuerys
from Models.punto_produccion_model import PuntoProduccionModel
from Models.zona_model import ZonaModel

# Desde cuántas porciones se avisa que un plato se está acabando
POCAS_PORCIONES = 5


def medida(valor, unidad: str) -> str:
    """ 1500 g -> "1.500 g"; 2,5 und -> "2,5 und" """
    numero = Decimal(str(valor)).quantize(Decimal("0.1"))
    entero, _, decimal = f"{abs(numero):,.1f}".partition(".")
    texto = entero.replace(",", ".") + ("" if decimal == "0" else f",{decimal}")
    return f"{'-' if numero < 0 else ''}{texto} {unidad}"


class Disponibilidad:
    """ Sugerir agotados con el inventario y las recetas (doc 12, sección 5). Solo sugiere: marcar agotado
        sigue siendo una decisión de cocina o del administrador, porque el stock del sistema puede no
        coincidir con lo que hay en la nevera. """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = InventarioQuerys(db, ctx)

    def suggest(self, data: dict):
        punto_id = data.get("punto_produccion_id")
        if punto_id:
            punto = self.querys.get_own(PuntoProduccionModel, punto_id, "punto de producción")
            if self.ctx.get("puntos") is not None and punto.id not in self.ctx["puntos"]:
                raise CustomException("No tiene asignado este punto de producción.", 403)

        # Un plato que va al punto de la zona puede llegar a cualquier pantalla: se muestra en todas. Y un punto
        # que recibe pedidos enteros de una zona (ADR-056) prepara cualquier producto
        de_zona = {z.punto_produccion_id for z in self.querys.scoped(ZonaModel).filter(
            ZonaModel.activo.is_(True), ZonaModel.reparto == "zona")}
        alcance = [p for p in self.querys.alcance_productos()
                   if not punto_id or int(punto_id) in de_zona or p["punto_produccion_id"] in (None, int(punto_id))]
        combos = ComboQuerys(self.db, self.ctx)
        for producto in alcance:
            producto["motivo"] = "; ".join(
                f"{i['nombre']}: quedan {medida(max(i['stock'], 0), i['unidad'])} y cada uno lleva {medida(i['por_porcion'], i['unidad'])}"
                for i in producto["limitan"])

        sugeridos = [p for p in alcance if not p["agotado"] and p["porciones"] == 0]
        for producto in sugeridos:
            # Al agotarlo, el combo que lo trae como parte fija también deja de ofrecerse
            producto["combos"] = combos.combos_que_usan(producto["producto_id"])
        return self.tools.output(200, "Sugerencias de agotados.", {
            "sugeridos": sugeridos,
            "por_acabarse": [p for p in alcance if not p["agotado"] and 0 < p["porciones"] <= POCAS_PORCIONES],
            # Agotados que ya tienen con qué prepararse, por ejemplo después de recibir una compra
            "con_insumos": [p for p in alcance if p["agotado"] and p["porciones"] > 0],
            "pocas_porciones": POCAS_PORCIONES,
        })
