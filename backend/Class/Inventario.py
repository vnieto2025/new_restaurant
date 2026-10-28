from datetime import datetime, timedelta, time
from decimal import Decimal
from Utils.tools import Tools, CustomException, clean_text, to_local
from Querys.inventario import InventarioQuerys, dec
from Models.insumo_model import InsumoModel
from Models.movimiento_inventario_model import TIPOS_MOVIMIENTO
from Models.conteo_model import ConteoModel
from Class.Insumo import Insumo, cantidad
from Class.Impuesto import Impuesto
from Class.Caja import dia_actual

TIPOS_TEXTO = {
    "entrada": "Entrada", "compra": "Compra", "anulacion_compra": "Anulación de compra", "consumo": "Consumo por venta", "reverso_consumo": "Reverso de consumo",
    "merma": "Merma", "ajuste": "Ajuste", "produccion": "Producción", "devolucion": "Devolución",
}
MOTIVOS_MERMA = ["Se dañó", "Se venció", "Se cayó o se quemó", "Prueba o degustación", "Consumo del personal"]


class Inventario:
    """ Existencias y movimientos (doc 22). El stock solo cambia con movimientos y todo ajuste
        o merma lleva motivo y usuario (RN-INV-01, RN-INV-02). """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = InventarioQuerys(db, ctx)

    def status(self, data: dict = None):
        """ Resumen: valor del inventario, alertas de stock bajo o negativo y antigüedad del último conteo """
        insumo = Insumo(self.db, self.ctx)
        insumos = [insumo.format(i) for i in self.querys.insumos()]
        ultimo = self.querys.scoped(ConteoModel).filter(ConteoModel.estado == "aplicado").order_by(
            ConteoModel.aplicado_en.desc()).first()
        return self.tools.output(200, "Estado del inventario.", {
            "valor": sum(i["valor_stock"] for i in insumos),
            "insumos": len(insumos),
            "negativos": [i for i in insumos if i["alerta"] == "negativo"],
            "bajos": [i for i in insumos if i["alerta"] == "bajo"],
            "ultimo_conteo": ultimo.aplicado_en if ultimo else None,
            "motivos_merma": MOTIVOS_MERMA,
        })

    def movements(self, data: dict):
        desde = Impuesto.parse_date(data.get("desde"))
        hasta = Impuesto.parse_date(data.get("hasta"))
        if data.get("tipo") and data["tipo"] not in TIPOS_MOVIMIENTO:
            raise CustomException("El tipo de movimiento no es válido.")
        tz = self.ctx.get("zona_horaria")
        filas = self.querys.movimientos(
            insumo_id=data.get("insumo_id"), tipo=data.get("tipo"),
            desde=self.local_start(desde) if desde else None,
            hasta=self.local_start(hasta + timedelta(days=1)) if hasta else None,
            limite=min(int(data.get("limite") or 200), 500))
        nombres = {i.id: (i.nombre, i.unidad) for i in self.querys.insumos(incluir_inactivos=True)}
        result = [{
            "id": m.id, "insumo_id": m.insumo_id, "insumo": nombres.get(m.insumo_id, ("?", ""))[0],
            "unidad": nombres.get(m.insumo_id, ("", ""))[1], "tipo": m.tipo, "tipo_texto": TIPOS_TEXTO[m.tipo],
            "cantidad": float(m.cantidad), "costo_unitario": float(m.costo_unitario), "costo_total": m.costo_total,
            "stock_resultante": float(m.stock_resultante), "motivo": m.motivo, "referencia": m.referencia,
            "usuario": self.nombre_usuario(m.usuario_id), "creado_en": m.creado_en, "hora_local": to_local(m.creado_en, tz),
        } for m in filas]
        return self.tools.output(200, "Movimientos." if result else "No hay movimientos con ese filtro.", result)

    # Entrada manual: carga inicial o mercancía que llegó sin compra registrada
    def entry(self, data: dict):
        insumo = self.get_insumo(data["insumo_id"])
        unidades = self.quantity_in_base(insumo, data)
        costo = dec(data.get("costo_unitario") or 0)
        if data.get("costo_total") not in (None, ""):
            costo = dec(data["costo_total"]) / unidades
        if costo < 0:
            raise CustomException("El costo no es válido.")
        self.querys.mover(insumo.id, "entrada", unidades, costo_unitario=costo,
                          motivo=clean_text(data.get("motivo")) or "Entrada manual")
        self.db.commit()
        return self.tools.output(200, f"Entrada de {self.fmt(unidades)} {insumo.unidad} de {insumo.nombre}.",
                                 Insumo(self.db, self.ctx).format(insumo))

    def waste(self, data: dict):
        insumo = self.get_insumo(data["insumo_id"])
        unidades = self.quantity_in_base(insumo, data)
        motivo = clean_text(data["motivo"])
        self.querys.mover(insumo.id, "merma", -unidades, motivo=motivo)
        self.querys.audit("merma_registrada", "insumo", insumo.id, despues={"cantidad": str(unidades)}, motivo=motivo, commit=False)
        self.db.commit()
        return self.tools.output(200, f"Merma de {self.fmt(unidades)} {insumo.unidad} de {insumo.nombre} registrada.",
                                 Insumo(self.db, self.ctx).format(insumo))

    # Ajuste puntual a una existencia real contada (el conteo completo va por Conteo)
    def adjust(self, data: dict):
        insumo = self.get_insumo(data["insumo_id"])
        real = cantidad(data["existencia_real"], "existencia real", permitir_negativo=False, permitir_cero=True)
        diferencia = real - dec(insumo.stock)
        if diferencia == 0:
            return self.tools.output(200, "La existencia ya coincide; no hay nada que ajustar.", Insumo(self.db, self.ctx).format(insumo))
        motivo = clean_text(data["motivo"])
        self.querys.mover(insumo.id, "ajuste", diferencia, motivo=motivo)
        self.querys.audit("inventario_ajustado", "insumo", insumo.id, antes={"stock": str(real - diferencia)},
                          despues={"stock": str(real)}, motivo=motivo, commit=False)
        self.db.commit()
        return self.tools.output(200, f"{insumo.nombre} ajustado a {self.fmt(real)} {insumo.unidad}.",
                                 Insumo(self.db, self.ctx).format(insumo))

    def produce(self, data: dict):
        """ Elaborar una preparación: descuenta sus ingredientes y entra la preparación al costo
            de lo que se usó (doc 22, movimiento de producción). """
        insumo = self.get_insumo(data["insumo_id"])
        if not insumo.es_preparacion:
            raise CustomException("Solo se producen preparaciones.")
        receta = self.querys.receta_de_insumo(insumo.id)
        if not receta:
            raise CustomException(f"{insumo.nombre} no tiene receta: créala antes de registrar la producción.")
        unidades = cantidad(data["cantidad"])
        costo_total = Decimal(0)
        referencia = f"Producción de {insumo.nombre}"
        for ingrediente_id, requerido in self.querys.requerimientos(receta, unidades).items():
            movimiento = self.querys.mover(ingrediente_id, "produccion", -requerido.quantize(Decimal("0.001")),
                                           motivo=referencia, referencia=referencia[:60])
            if movimiento:
                costo_total += abs(dec(movimiento.cantidad)) * dec(movimiento.costo_unitario)
        self.querys.mover(insumo.id, "produccion", unidades, costo_unitario=costo_total / unidades,
                          motivo=clean_text(data.get("motivo")) or "Producción", referencia=referencia[:60])
        self.db.commit()
        return self.tools.output(200, f"Se produjeron {self.fmt(unidades)} {insumo.unidad} de {insumo.nombre}.",
                                 Insumo(self.db, self.ctx).format(insumo))

    # ---- Apoyo ----

    def get_insumo(self, insumo_id):
        insumo = self.querys.get_own(InsumoModel, insumo_id, "insumo")
        if not insumo.activo:
            raise CustomException(f"{insumo.nombre} está inactivo.")
        return insumo

    def quantity_in_base(self, insumo, data: dict):
        """ Cantidad en unidad base; si viene una presentación ("3 bultos"), se multiplica por su factor """
        unidades = cantidad(data["cantidad"])
        if data.get("presentacion_id"):
            presentacion = next((p for p in self.querys.presentaciones(insumo.id) if p.id == int(data["presentacion_id"])), None)
            if not presentacion:
                raise CustomException("La presentación no es de este insumo.")
            unidades = (unidades * dec(presentacion.factor)).quantize(Decimal("0.001"))
        return unidades

    def local_start(self, dia):
        from zoneinfo import ZoneInfo
        return datetime.combine(dia, time.min, tzinfo=ZoneInfo(self.ctx.get("zona_horaria") or "America/Bogota"))

    def nombre_usuario(self, usuario_id):
        from Models.usuario_model import UsuarioModel
        usuario = self.db.get(UsuarioModel, usuario_id) if usuario_id else None
        return usuario.nombre if usuario else "Sistema"

    @staticmethod
    def fmt(valor):
        texto = format(dec(valor).normalize(), "f")
        return texto.replace(".", ",")
