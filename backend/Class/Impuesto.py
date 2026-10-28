from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from Utils.tools import Tools, CustomException, clean_text
from Utils.impuestos import porcentaje_texto
from Querys.facturacion import FacturacionQuerys
from Models.impuesto_model import ImpuestoModel, TIPOS_IMPUESTO
from Models.impuesto_tarifa_model import ImpuestoTarifaModel
from Class.Caja import dia_actual


class Impuesto:
    """ Impuestos del restaurante con tasas por vigencia (RG-06, doc 21A sección 2).
        Ninguna tasa está escrita en el código: las configura el administrador con su contador. """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = FacturacionQuerys(db, ctx)

    def list(self, data: dict):
        hoy = dia_actual(self.ctx)
        vigentes = self.querys.tarifas_vigentes(hoy)
        result = [self.format(i, vigentes) for i in self.querys.impuestos(incluir_inactivos=data.get("todos") is True)]
        return self.tools.output(200, "Impuestos del restaurante." if result else "Aún no hay impuestos configurados.", result)

    def create(self, data: dict):
        fields = self.clean_data(data)
        if self.name_exists(fields["nombre"]):
            raise CustomException("Ya existe un impuesto con ese nombre.")
        if data.get("por_defecto") is True or not self.querys.impuestos():
            self.querys.quitar_defecto()
            fields["por_defecto"] = True
        impuesto_id = self.querys.insert_data(ImpuestoModel, fields, commit=False)
        self.add_rate(impuesto_id, data["porcentaje"], data.get("vigente_desde"))
        self.querys.audit("impuesto_creado", "impuesto", impuesto_id, despues={**fields, "porcentaje": str(data["porcentaje"])},
                          commit=False)
        self.db.commit()
        impuesto = self.querys.get_own(ImpuestoModel, impuesto_id, "impuesto")
        return self.tools.output(201, "Impuesto creado.", self.format(impuesto))

    # Nombre, tipo y código. La tasa no se edita: se programa una nueva (set_rate)
    def update(self, data: dict):
        impuesto = self.querys.get_own(ImpuestoModel, data["impuesto_id"], "impuesto")
        fields = self.clean_data(data)
        if self.name_exists(fields["nombre"], exclude_id=impuesto.id):
            raise CustomException("Ya existe otro impuesto con ese nombre.")
        if data.get("por_defecto") is True and not impuesto.por_defecto:
            self.querys.quitar_defecto()
            fields["por_defecto"] = True
        impuesto = self.querys.update_data(ImpuestoModel, impuesto.id, fields, "impuesto")
        return self.tools.output(200, "Impuesto actualizado.", self.format(impuesto))

    def change_status(self, data: dict):
        impuesto = self.querys.get_own(ImpuestoModel, data["impuesto_id"], "impuesto")
        activo = data["activo"] is True
        if not activo and self.querys.en_uso(impuesto.id):
            raise CustomException("Hay productos o categorías con este impuesto. Cámbialos antes de desactivarlo.")
        if not activo and impuesto.por_defecto:
            raise CustomException("Es el impuesto por defecto. Elige otro por defecto antes de desactivarlo.")
        self.querys.update_data(ImpuestoModel, impuesto.id, {"activo": activo}, "impuesto")
        return self.tools.output(200, "Impuesto activado." if activo else "Impuesto desactivado.")

    def set_rate(self, data: dict):
        """ Programa un cambio de tasa desde una fecha. La tarifa anterior queda vigente hasta el día antes:
            las ventas ya hechas conservan la tasa con que se vendieron. """
        impuesto = self.querys.get_own(ImpuestoModel, data["impuesto_id"], "impuesto")
        desde = self.parse_date(data.get("vigente_desde")) or dia_actual(self.ctx)
        if desde < dia_actual(self.ctx):
            raise CustomException("La nueva tasa no puede empezar en una fecha pasada.")
        anterior = self.querys.tarifas(impuesto.id)
        self.add_rate(impuesto.id, data["porcentaje"], desde)
        self.querys.audit("impuesto_tarifa", "impuesto", impuesto.id,
                          antes={"tarifas": [str(t.porcentaje) for t in anterior[:1]]},
                          despues={"porcentaje": str(data["porcentaje"]), "desde": desde.isoformat()},
                          motivo=clean_text(data.get("motivo")), commit=False)
        self.db.commit()
        return self.tools.output(200, f"Tasa programada desde el {desde.strftime('%d/%m/%Y')}.", self.format(impuesto))

    def add_rate(self, impuesto_id, porcentaje, desde=None):
        try:
            valor = Decimal(str(porcentaje).replace(",", "."))
        except InvalidOperation:
            raise CustomException("El porcentaje no es válido.")
        if valor < 0 or valor >= 100:
            raise CustomException("El porcentaje debe estar entre 0 y 99,999.")
        desde = self.parse_date(desde) or dia_actual(self.ctx)

        for tarifa in self.querys.tarifas(impuesto_id):
            # Una tarifa programada para el mismo día o después se reemplaza
            if tarifa.vigente_desde >= desde:
                self.db.delete(tarifa)
            elif tarifa.vigente_hasta is None or tarifa.vigente_hasta >= desde:
                tarifa.vigente_hasta = desde - timedelta(days=1)
        self.db.flush()
        self.querys.insert_data(ImpuestoTarifaModel, {"impuesto_id": impuesto_id, "porcentaje": valor,
                                                      "vigente_desde": desde, "creado_por": self.ctx.get("usuario_id")},
                                commit=False)

    def format(self, impuesto, vigentes=None):
        vigentes = vigentes if vigentes is not None else self.querys.tarifas_vigentes(dia_actual(self.ctx))
        porcentaje = vigentes.get(impuesto.id)
        return {
            "id": impuesto.id,
            "nombre": impuesto.nombre,
            "tipo": impuesto.tipo,
            "codigo": impuesto.codigo,
            "por_defecto": impuesto.por_defecto,
            "activo": impuesto.activo,
            "porcentaje": float(porcentaje) if porcentaje is not None else None,
            "porcentaje_texto": f"{porcentaje_texto(porcentaje)} %" if porcentaje is not None else "Sin tasa vigente",
            "tarifas": [{
                "porcentaje": float(t.porcentaje),
                "vigente_desde": t.vigente_desde,
                "vigente_hasta": t.vigente_hasta,
            } for t in self.querys.tarifas(impuesto.id)],
        }

    def clean_data(self, data: dict):
        if data["tipo"] not in TIPOS_IMPUESTO:
            raise CustomException("El tipo de impuesto no es válido.")
        return {"nombre": clean_text(data["nombre"]), "tipo": data["tipo"], "codigo": clean_text(data.get("codigo"))}

    def name_exists(self, nombre, exclude_id=None):
        query = self.querys.scoped(ImpuestoModel).filter(ImpuestoModel.nombre.ilike(nombre))
        if exclude_id:
            query = query.filter(ImpuestoModel.id != exclude_id)
        return query.first() is not None

    @staticmethod
    def parse_date(valor):
        if not valor:
            return None
        if isinstance(valor, date):
            return valor
        try:
            return date.fromisoformat(str(valor)[:10])
        except ValueError:
            raise CustomException("La fecha no es válida.")
