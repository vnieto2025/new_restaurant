from Querys.caja import CajaQuerys
from Models.cupon_model import CuponModel
from Models.cupon_redencion_model import CuponRedencionModel, USOS_VIGENTES
from Models.cuenta_model import CuentaModel
from Models.orden_model import OrdenModel
from Models.intento_pago_model import IntentoPagoModel
from sqlalchemy import func, or_


class CuponQuerys(CajaQuerys):

    def list_cupones(self, estado=None, buscar=None, plantillas=False, cliente_id=None, limite=200):
        query = self.scoped(CuponModel).filter(CuponModel.plantilla.is_(plantillas))
        if estado:
            query = query.filter(CuponModel.estado == estado)
        if cliente_id:
            query = query.filter(CuponModel.cliente_id == cliente_id)
        if buscar:
            patron = f"%{buscar}%"
            query = query.filter(or_(CuponModel.codigo.ilike(patron), CuponModel.nombre.ilike(patron)))
        return query.order_by(CuponModel.id.desc()).limit(limite).all()

    def by_code(self, codigo, lock=False):
        query = self.scoped(CuponModel).filter(CuponModel.codigo == codigo)
        if lock:
            query = query.with_for_update()
        return query.first()

    def code_exists(self, codigo):
        return self.scoped(CuponModel).filter(CuponModel.codigo == codigo).first() is not None

    # Usos que cuentan: aplicados en cuentas abiertas y redimidos (RN-CUP-03)
    def usos(self, cupon_id, cliente_id=None, excluir_cuenta=None):
        query = self.scoped(CuponRedencionModel).filter(CuponRedencionModel.cupon_id == cupon_id,
                                                        CuponRedencionModel.estado.in_(USOS_VIGENTES))
        if cliente_id:
            query = query.filter(CuponRedencionModel.cliente_id == cliente_id)
        if excluir_cuenta:
            query = query.filter(CuponRedencionModel.cuenta_id != excluir_cuenta)
        return query.count()

    def usos_por_cupon(self, cupon_ids):
        if not cupon_ids:
            return {}
        filas = self.scoped(CuponRedencionModel).with_entities(CuponRedencionModel.cupon_id, func.count()).filter(
            CuponRedencionModel.cupon_id.in_(cupon_ids), CuponRedencionModel.estado.in_(USOS_VIGENTES)
        ).group_by(CuponRedencionModel.cupon_id).all()
        return {cupon_id: int(n) for cupon_id, n in filas}

    def redenciones_de_cuenta(self, cuenta_id, estados=("aplicada",)):
        return self.scoped(CuponRedencionModel).filter(CuponRedencionModel.cuenta_id == cuenta_id,
                                                       CuponRedencionModel.estado.in_(estados)).order_by(
            CuponRedencionModel.id.asc()).all()

    def redencion(self, cupon_id, cuenta_id):
        return self.scoped(CuponRedencionModel).filter(CuponRedencionModel.cupon_id == cupon_id,
                                                       CuponRedencionModel.cuenta_id == cuenta_id).first()

    def redenciones_de_cupon(self, cupon_id, limite=20):
        return self.scoped(CuponRedencionModel).filter(CuponRedencionModel.cupon_id == cupon_id).order_by(
            CuponRedencionModel.id.desc()).limit(limite).all()

    def redenciones_de_cliente(self, cliente_id, limite=20):
        return self.scoped(CuponRedencionModel).filter(CuponRedencionModel.cliente_id == cliente_id).order_by(
            CuponRedencionModel.id.desc()).limit(limite).all()

    def emitidos_por_cuenta(self, cuenta_id):
        return self.scoped(CuponModel).filter(CuponModel.cuenta_origen_id == cuenta_id).all()

    def plantillas_para(self, neto):
        return self.scoped(CuponModel).filter(CuponModel.plantilla.is_(True), CuponModel.estado == "activo",
                                              CuponModel.emitir_desde <= neto).order_by(
            CuponModel.emitir_desde.desc(), CuponModel.id.asc()).all()

    # Cupón vivo de una plantilla para un cliente: activo, vigente y sin usar
    def emitido_vivo(self, plantilla_id, cliente_id, dia):
        candidatos = self.scoped(CuponModel).filter(CuponModel.plantilla_id == plantilla_id, CuponModel.cliente_id == cliente_id,
                                                    CuponModel.estado == "activo", CuponModel.termina >= dia).all()
        return next((c for c in candidatos if not self.usos(c.id)), None)

    def pago_en_curso(self, cuenta_id):
        return self.scoped(IntentoPagoModel).filter(IntentoPagoModel.cuenta_id == cuenta_id,
                                                    IntentoPagoModel.estado == "pendiente").first() is not None

    def cliente_de_sesion(self, sesion_id):
        orden = self.scoped(OrdenModel).filter(OrdenModel.sesion_mesa_id == sesion_id, OrdenModel.cliente_id.isnot(None)).order_by(
            OrdenModel.id.asc()).first()
        return orden.cliente_id if orden else None

    # ---- Resultados (doc 25A, sección 6) ----

    def redimidas(self, desde, hasta):
        return self.scoped(CuponRedencionModel).join(CuentaModel, CuentaModel.id == CuponRedencionModel.cuenta_id).filter(
            CuponRedencionModel.estado == "redimida", CuentaModel.estado == "pagada",
            CuentaModel.jornada >= desde, CuentaModel.jornada <= hasta).add_entity(CuentaModel).all()

    def cuentas_pagadas(self, desde, hasta):
        return self.scoped(CuentaModel).filter(CuentaModel.estado == "pagada", CuentaModel.jornada >= desde,
                                               CuentaModel.jornada <= hasta).all()

    # Cliente nuevo: su primera orden es de la cuenta en que usó el cupón
    def primera_orden(self, cliente_id):
        return self.scoped(OrdenModel).filter(OrdenModel.cliente_id == cliente_id).order_by(OrdenModel.id.asc()).first()
