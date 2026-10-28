from Utils.tools import Tools, CustomException, clean_text
from Querys.facturacion import FacturacionQuerys
from Models.resolucion_model import ResolucionModel, TIPOS_DOCUMENTO
from Models.documento_venta_model import DocumentoVentaModel
from Models.caja_model import CajaModel
from Class.Impuesto import Impuesto
from Class.Caja import dia_actual

TIPOS_TEXTO = {"pos": "Documento POS electrónico", "factura": "Factura electrónica", "nota_credito": "Nota crédito"}


class Resolucion:
    """ Rangos de numeración por tipo de documento, restaurante y caja (doc 21, sección 5) """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = FacturacionQuerys(db, ctx)

    def list(self, data: dict):
        result = [self.format(r) for r in self.querys.resoluciones()]
        return self.tools.output(200, "Resoluciones de numeración." if result else "Aún no hay resoluciones.", result)

    def create(self, data: dict):
        fields = self.clean_data(data)
        resolucion_id = self.querys.insert_data(ResolucionModel, fields, commit=False)
        self.querys.audit("resolucion_creada", "resolucion", resolucion_id, despues=self.auditable(fields), commit=False)
        self.db.commit()
        return self.tools.output(201, "Resolución creada.", self.format(self.querys.get_own(ResolucionModel, resolucion_id)))

    # El rango no puede quedar por debajo de lo ya usado ni cambiar de tipo o prefijo si ya se usó
    def update(self, data: dict):
        resolucion = self.querys.get_own(ResolucionModel, data["resolucion_id"], "resolución", lock=True)
        fields = self.clean_data(data)
        if resolucion.ultimo is not None:
            if fields["tipo_documento"] != resolucion.tipo_documento or fields["prefijo"] != resolucion.prefijo \
                    or fields["desde"] != resolucion.desde:
                raise CustomException("La resolución ya tiene documentos: no se cambia el tipo, el prefijo ni el número inicial.")
            if fields["hasta"] < resolucion.ultimo:
                raise CustomException(f"Ya se usó hasta el número {resolucion.ultimo}: el rango no puede terminar antes.")
        antes = self.auditable({c: getattr(resolucion, c) for c in fields})
        for campo, valor in fields.items():
            setattr(resolucion, campo, valor)
        self.querys.audit("resolucion_editada", "resolucion", resolucion.id, antes=antes, despues=self.auditable(fields),
                          commit=False)
        self.db.commit()
        return self.tools.output(200, "Resolución actualizada.", self.format(resolucion))

    def change_status(self, data: dict):
        resolucion = self.querys.get_own(ResolucionModel, data["resolucion_id"], "resolución")
        activo = data["activo"] is True
        self.querys.update_data(ResolucionModel, resolucion.id, {"activo": activo}, "resolución")
        return self.tools.output(200, "Resolución activada." if activo else "Resolución desactivada.")

    def format(self, resolucion):
        usados = (resolucion.ultimo - resolucion.desde + 1) if resolucion.ultimo is not None else 0
        restantes = resolucion.hasta - (resolucion.ultimo if resolucion.ultimo is not None else resolucion.desde - 1)
        hoy = dia_actual(self.ctx)
        vencida = bool(resolucion.vigente_hasta and resolucion.vigente_hasta < hoy)
        caja = self.db.get(CajaModel, resolucion.caja_id) if resolucion.caja_id else None
        return {
            "id": resolucion.id,
            "tipo_documento": resolucion.tipo_documento,
            "tipo_texto": TIPOS_TEXTO[resolucion.tipo_documento],
            "numero_resolucion": resolucion.numero_resolucion,
            "prefijo": resolucion.prefijo,
            "desde": resolucion.desde,
            "hasta": resolucion.hasta,
            "ultimo": resolucion.ultimo,
            "usados": usados,
            "restantes": restantes,
            "vigente_desde": resolucion.vigente_desde,
            "vigente_hasta": resolucion.vigente_hasta,
            "caja_id": resolucion.caja_id,
            "caja": caja.nombre if caja else None,
            "alerta_restantes": resolucion.alerta_restantes,
            "activo": resolucion.activo,
            "vencida": vencida,
            "por_agotarse": resolucion.activo and restantes <= resolucion.alerta_restantes,
        }

    def clean_data(self, data: dict):
        tipo = data["tipo_documento"]
        if tipo not in TIPOS_DOCUMENTO:
            raise CustomException("El tipo de documento no es válido.")
        desde, hasta = int(data["desde"]), int(data["hasta"])
        if desde < 1 or hasta < desde:
            raise CustomException("El rango no es válido: el número final debe ser mayor o igual al inicial.")
        vigente_desde = Impuesto.parse_date(data.get("vigente_desde")) or dia_actual(self.ctx)
        vigente_hasta = Impuesto.parse_date(data.get("vigente_hasta"))
        if vigente_hasta and vigente_hasta < vigente_desde:
            raise CustomException("La fecha final de vigencia es anterior a la inicial.")
        caja_id = None
        if data.get("caja_id"):
            caja_id = self.querys.get_own(CajaModel, data["caja_id"], "caja").id
        prefijo = (clean_text(data.get("prefijo")) or "").upper().replace(" ", "")
        if self.overlaps(tipo, prefijo, desde, hasta, data.get("resolucion_id")):
            raise CustomException("Ya hay otra resolución con ese prefijo que cubre parte de ese rango.")
        return {
            "tipo_documento": tipo,
            "numero_resolucion": clean_text(data.get("numero_resolucion")),
            "prefijo": prefijo,
            "desde": desde,
            "hasta": hasta,
            "vigente_desde": vigente_desde,
            "vigente_hasta": vigente_hasta,
            "caja_id": caja_id,
            "alerta_restantes": max(0, int(data.get("alerta_restantes") or 100)),
        }

    # Dos rangos con el mismo prefijo que se cruzan darían números repetidos
    def overlaps(self, tipo, prefijo, desde, hasta, exclude_id=None):
        query = self.querys.scoped(ResolucionModel).filter(
            ResolucionModel.prefijo == prefijo, ResolucionModel.desde <= hasta, ResolucionModel.hasta >= desde)
        if exclude_id:
            query = query.filter(ResolucionModel.id != int(exclude_id))
        return query.first() is not None

    @staticmethod
    def auditable(fields: dict):
        return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in fields.items()}

    # Rango interno de notas crédito: se crea solo la primera vez que se necesita
    def ensure_credit_range(self, dia):
        resolucion = self.querys.resolucion_para("nota_credito", dia)
        if resolucion:
            return resolucion
        prefijo = "NC"
        desde = 1
        while self.overlaps("nota_credito", prefijo, desde, 999999999):
            prefijo += "X"
        resolucion_id = self.querys.insert_data(ResolucionModel, {
            "tipo_documento": "nota_credito", "prefijo": prefijo, "desde": desde, "hasta": 999999999,
            "vigente_desde": dia, "alerta_restantes": 0,
        }, commit=False)
        return self.querys.get_own(ResolucionModel, resolucion_id)


def numero_completo(documento: DocumentoVentaModel):
    return f"{documento.prefijo}{documento.numero}"
