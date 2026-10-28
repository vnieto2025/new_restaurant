from datetime import date, timedelta
from Querys.base import Querys
from Models.impuesto_model import ImpuestoModel
from Models.impuesto_tarifa_model import ImpuestoTarifaModel
from Models.resolucion_model import ResolucionModel
from Models.facturacion_config_model import FacturacionConfigModel
from Models.documento_venta_model import DocumentoVentaModel
from Models.documento_venta_linea_model import DocumentoVentaLineaModel
from Models.cuenta_model import CuentaModel
from Models.producto_model import ProductoModel
from Models.categoria_model import CategoriaModel
from Utils.tools import now
from sqlalchemy import text, func, or_, case


class FacturacionQuerys(Querys):

    # ---- Impuestos ----

    def impuestos(self, incluir_inactivos=False):
        query = self.scoped(ImpuestoModel)
        if not incluir_inactivos:
            query = query.filter(ImpuestoModel.activo.is_(True))
        return query.order_by(ImpuestoModel.por_defecto.desc(), ImpuestoModel.nombre.asc()).all()

    def tarifas(self, impuesto_id):
        return self.scoped(ImpuestoTarifaModel).filter(ImpuestoTarifaModel.impuesto_id == impuesto_id).order_by(
            ImpuestoTarifaModel.vigente_desde.desc()).all()

    # Porcentaje vigente en una fecha de cada impuesto activo: {impuesto_id: porcentaje}
    def tarifas_vigentes(self, dia: date):
        rows = self.scoped(ImpuestoTarifaModel).join(
            ImpuestoModel, ImpuestoModel.id == ImpuestoTarifaModel.impuesto_id
        ).filter(
            ImpuestoModel.activo.is_(True), ImpuestoModel.eliminado_en.is_(None),
            ImpuestoTarifaModel.vigente_desde <= dia,
            or_(ImpuestoTarifaModel.vigente_hasta.is_(None), ImpuestoTarifaModel.vigente_hasta >= dia),
        ).order_by(ImpuestoTarifaModel.vigente_desde.asc()).all()
        return {t.impuesto_id: t.porcentaje for t in rows}

    def impuesto_defecto(self):
        return self.scoped(ImpuestoModel).filter(ImpuestoModel.por_defecto.is_(True),
                                                 ImpuestoModel.activo.is_(True)).first()

    def quitar_defecto(self):
        self.scoped(ImpuestoModel).filter(ImpuestoModel.por_defecto.is_(True)).update(
            {"por_defecto": False}, synchronize_session=False)

    def en_uso(self, impuesto_id):
        productos = self.scoped(ProductoModel).filter(ProductoModel.impuesto_id == impuesto_id).count()
        categorias = self.scoped(CategoriaModel).filter(CategoriaModel.impuesto_id == impuesto_id).count()
        return productos + categorias

    # ---- Resoluciones ----

    def resoluciones(self):
        return self.scoped(ResolucionModel).order_by(ResolucionModel.activo.desc(), ResolucionModel.tipo_documento.asc(),
                                                     ResolucionModel.id.desc()).all()

    # Resolución utilizable hoy para un tipo: activa, vigente y con números libres.
    # Primero la de la caja; si no hay, la general del restaurante.
    def resolucion_para(self, tipo: str, dia: date, caja_id=None):
        query = self.scoped(ResolucionModel).filter(
            ResolucionModel.tipo_documento == tipo, ResolucionModel.activo.is_(True),
            ResolucionModel.vigente_desde <= dia,
            or_(ResolucionModel.vigente_hasta.is_(None), ResolucionModel.vigente_hasta >= dia),
            func.coalesce(ResolucionModel.ultimo, ResolucionModel.desde - 1) < ResolucionModel.hasta,
            or_(ResolucionModel.caja_id.is_(None), ResolucionModel.caja_id == caja_id),
        )
        return query.order_by(ResolucionModel.caja_id.is_(None).asc(), ResolucionModel.id.asc()).first()

    # Siguiente número del rango, atómico: dos cobros a la vez nunca reciben el mismo (RN-FAC-05).
    # Si la venta falla, el rollback devuelve el número y no queda salto.
    def siguiente_numero(self, resolucion_id):
        return self.db.execute(text(
            "UPDATE resolucion SET ultimo = COALESCE(ultimo, desde - 1) + 1 "
            "WHERE id = :id AND COALESCE(ultimo, desde - 1) < hasta RETURNING ultimo"
        ), {"id": resolucion_id}).scalar()

    # ---- Configuración ----

    def config(self, lock=False):
        query = self.scoped(FacturacionConfigModel)
        if lock:
            query = query.with_for_update()
        return query.first()

    # ---- Documentos ----

    def documentos_de_cuenta(self, cuenta_id):
        return self.scoped(DocumentoVentaModel).filter(DocumentoVentaModel.cuenta_id == cuenta_id).order_by(
            DocumentoVentaModel.id.asc()).all()

    def notas_de(self, documento_id):
        return self.scoped(DocumentoVentaModel).filter(DocumentoVentaModel.documento_origen_id == documento_id).all()

    def lineas(self, documento_id):
        return self.scoped(DocumentoVentaLineaModel).filter(DocumentoVentaLineaModel.documento_id == documento_id).order_by(
            DocumentoVentaLineaModel.id.asc()).all()

    def list_documentos(self, estado=None, tipo=None, desde=None, hasta=None, buscar=None, limite=100):
        query = self.scoped(DocumentoVentaModel)
        if estado:
            query = query.filter(DocumentoVentaModel.estado == estado)
        if tipo:
            query = query.filter(DocumentoVentaModel.tipo == tipo)
        if desde:
            query = query.filter(DocumentoVentaModel.jornada >= desde)
        if hasta:
            query = query.filter(DocumentoVentaModel.jornada <= hasta)
        if buscar:
            patron = f"%{buscar}%"
            query = query.filter(or_(
                func.concat(DocumentoVentaModel.prefijo, DocumentoVentaModel.numero).ilike(patron),
                DocumentoVentaModel.receptor_nombre.ilike(patron),
                DocumentoVentaModel.receptor_documento.ilike(patron),
            ))
        return query.order_by(DocumentoVentaModel.id.desc()).limit(limite).all()

    def conteo_por_estado(self):
        rows = self.scoped(DocumentoVentaModel).with_entities(
            DocumentoVentaModel.estado, func.count(DocumentoVentaModel.id)).group_by(DocumentoVentaModel.estado).all()
        return dict(rows)

    # Cuentas pagadas sin documento en los últimos días (p. ej. sin resolución vigente al cobrar)
    def cuentas_sin_documento(self, desde: date):
        con_documento = self.scoped(DocumentoVentaModel).with_entities(DocumentoVentaModel.cuenta_id).filter(
            DocumentoVentaModel.cuenta_id.isnot(None))
        return self.scoped(CuentaModel).filter(
            CuentaModel.estado == "pagada", CuentaModel.jornada >= desde, CuentaModel.total > 0,
            CuentaModel.id.notin_(con_documento),
        ).order_by(CuentaModel.id.asc()).all()

    # Documentos listos para enviar al proveedor, bloqueados para que nadie más los tome
    def documentos_por_enviar(self, limite=20, ids=None):
        query = self.scoped(DocumentoVentaModel).filter(
            DocumentoVentaModel.estado == "pendiente",
            or_(DocumentoVentaModel.proximo_intento_en.is_(None), DocumentoVentaModel.proximo_intento_en <= now()),
        )
        if ids:
            query = query.filter(DocumentoVentaModel.id.in_(ids))
        return query.order_by(DocumentoVentaModel.id.asc()).with_for_update(skip_locked=True).limit(limite).all()

    # Valores por impuesto en un periodo (doc 21, sección 7). Las notas crédito restan.
    def resumen_impuestos(self, desde: date, hasta: date):
        signo = case((DocumentoVentaModel.tipo == "nota_credito", -1), else_=1)
        rows = self.scoped(DocumentoVentaLineaModel).join(
            DocumentoVentaModel, DocumentoVentaModel.id == DocumentoVentaLineaModel.documento_id
        ).filter(
            DocumentoVentaModel.jornada >= desde, DocumentoVentaModel.jornada <= hasta,
        ).with_entities(
            DocumentoVentaLineaModel.impuesto_nombre, DocumentoVentaLineaModel.porcentaje,
            func.sum(DocumentoVentaLineaModel.base * signo),
            func.sum(DocumentoVentaLineaModel.impuesto_valor * signo),
            func.sum(DocumentoVentaLineaModel.total * signo),
        ).group_by(DocumentoVentaLineaModel.impuesto_nombre, DocumentoVentaLineaModel.porcentaje).all()
        return rows


def proximo_intento(intentos: int):
    """ Espera creciente entre reintentos: 1, 5, 15 minutos y luego cada hora """
    esperas = [60, 300, 900]
    segundos = esperas[intentos - 1] if 0 < intentos <= len(esperas) else 3600
    return now() + timedelta(seconds=segundos)
