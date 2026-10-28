from Querys.orden import OrdenQuerys
from Models.caja_model import CajaModel
from Models.turno_caja_model import TurnoCajaModel
from Models.medio_pago_model import MedioPagoModel
from Models.cuenta_model import CuentaModel
from Models.pago_model import PagoModel
from Models.movimiento_caja_model import MovimientoCajaModel
from Models.cierre_jornada_model import CierreJornadaModel
from Models.sesion_mesa_model import SesionMesaModel
from Models.orden_model import OrdenModel
from Models.orden_item_model import OrdenItemModel
from Models.mesa_model import MesaModel
from Models.zona_model import ZonaModel
from Models.usuario_model import UsuarioModel
from Models.restaurante_model import RestauranteModel
from Models.producto_model import ProductoModel
from Models.entrega_model import EntregaModel
from Models.rendicion_model import RendicionModel
from Utils.estados import CANCELADO, PENDIENTES_DE_ENTREGA
from Utils.tools import CustomException
from sqlalchemy import text, func


class CajaQuerys(OrdenQuerys):

    # Caja principal del restaurante (en el MVP hay una)
    def get_caja(self):
        caja = self.scoped(CajaModel).filter(CajaModel.activo.is_(True)).order_by(CajaModel.id.asc()).first()
        if not caja:
            raise CustomException("El restaurante no tiene caja configurada.", 409)
        return caja

    def get_turno_abierto(self, caja_id, lock=False):
        query = self.scoped(TurnoCajaModel).filter(TurnoCajaModel.caja_id == caja_id, TurnoCajaModel.estado == "abierto")
        if lock:
            query = query.with_for_update()
        return query.first()

    def list_turnos(self, limite=20):
        return self.scoped(TurnoCajaModel).order_by(TurnoCajaModel.id.desc()).limit(limite).all()

    def medios(self, incluir_inactivos=False):
        query = self.scoped(MedioPagoModel)
        if not incluir_inactivos:
            query = query.filter(MedioPagoModel.activo.is_(True))
        return query.order_by(MedioPagoModel.orden.asc(), MedioPagoModel.id.asc()).all()

    def jornada_cerrada(self, jornada):
        return self.scoped(CierreJornadaModel).filter(CierreJornadaModel.jornada == jornada).first() is not None

    def get_cierre(self, jornada):
        return self.scoped(CierreJornadaModel).filter(CierreJornadaModel.jornada == jornada).first()

    # Consecutivo de comprobantes por restaurante, atómico
    def next_cuenta_number(self):
        return self.db.execute(text(
            "INSERT INTO consecutivo_cuenta (restaurante_id, ultimo) VALUES (:r, 1) "
            "ON CONFLICT (restaurante_id) DO UPDATE SET ultimo = consecutivo_cuenta.ultimo + 1 RETURNING ultimo"
        ), {"r": self.restaurante_id}).scalar()

    def get_cuenta_by_sesion(self, sesion_id, lock=False):
        query = self.scoped(CuentaModel).filter(CuentaModel.sesion_mesa_id == sesion_id)
        if lock:
            query = query.with_for_update()
        return query.first()

    def ordenes_de_sesion(self, sesion_id):
        return self.scoped(OrdenModel).filter(OrdenModel.sesion_mesa_id == sesion_id).order_by(OrdenModel.id.asc()).all()

    def items_de_sesion(self, sesion_id):
        return self.scoped(OrdenItemModel).join(OrdenModel, OrdenModel.id == OrdenItemModel.orden_id).filter(
            OrdenModel.sesion_mesa_id == sesion_id).add_columns(OrdenModel.numero).order_by(OrdenItemModel.id.asc()).all()

    def subtotal_de_sesion(self, sesion_id):
        value = self.scoped(OrdenItemModel).join(OrdenModel, OrdenModel.id == OrdenItemModel.orden_id).with_entities(
            func.coalesce(func.sum(OrdenItemModel.total), 0)
        ).filter(OrdenModel.sesion_mesa_id == sesion_id, OrdenItemModel.estado != CANCELADO).scalar()
        return int(value or 0)

    # Tarifa de domicilio de la sesión; una entrega fallida sin reintento no se cobra
    def envio_de_sesion(self, sesion_id):
        value = self.scoped(EntregaModel).with_entities(func.coalesce(func.sum(EntregaModel.tarifa), 0)).filter(
            EntregaModel.sesion_mesa_id == sesion_id, EntregaModel.estado != "fallida").scalar()
        return int(value or 0)

    def entrega_de_sesion(self, sesion_id):
        return self.scoped(EntregaModel).filter(EntregaModel.sesion_mesa_id == sesion_id).first()

    def rendiciones_de_turno(self, turno_id):
        return self.scoped(RendicionModel).filter(RendicionModel.turno_caja_id == turno_id).all()

    def pagos_de(self, cuenta_id):
        return self.scoped(PagoModel).filter(PagoModel.cuenta_id == cuenta_id).order_by(PagoModel.id.asc()).all()

    def pagos_por_clave(self, clave: str):
        return self.scoped(PagoModel).filter(PagoModel.clave_idempotencia.like(f"{clave}:%")).all()

    def sesiones_abiertas(self):
        return self.scoped(SesionMesaModel).filter(SesionMesaModel.estado == "abierta").order_by(SesionMesaModel.abierta_en.asc()).all()

    def cuentas_de_jornada(self, jornada, estado=None):
        query = self.scoped(CuentaModel).filter(CuentaModel.jornada == jornada)
        if estado:
            query = query.filter(CuentaModel.estado == estado)
        return query.order_by(CuentaModel.id.desc()).all()

    def cuentas_abiertas_con_pagos(self):
        return self.scoped(CuentaModel).filter(CuentaModel.estado == "abierta", CuentaModel.pagado > 0).all()

    def pagos_de_turno(self, turno_id):
        return self.scoped(PagoModel).filter(PagoModel.turno_caja_id == turno_id).all()

    def movimientos_de_turno(self, turno_id):
        return self.scoped(MovimientoCajaModel).filter(MovimientoCajaModel.turno_caja_id == turno_id).order_by(
            MovimientoCajaModel.id.asc()).all()

    def cuentas_de_turno(self, turno_id):
        return self.scoped(CuentaModel).filter(CuentaModel.turno_caja_id == turno_id).all()

    def turnos_abiertos(self):
        return self.scoped(TurnoCajaModel).filter(TurnoCajaModel.estado == "abierto").all()

    def nombre_usuario(self, usuario_id):
        usuario = self.db.get(UsuarioModel, usuario_id) if usuario_id else None
        return usuario.nombre if usuario else None

    def restaurante_actual(self):
        return self.db.get(RestauranteModel, self.restaurante_id)

    def reset_agotados(self):
        return self.scoped(ProductoModel).filter(ProductoModel.agotado.is_(True)).update(
            {"agotado": False}, synchronize_session=False)

    # Resumen de pagos y movimientos de un turno (informe de cierre, doc 20 sección 2)
    def resumen_turno(self, turno):
        medios = {m.id: m for m in self.medios(incluir_inactivos=True)}
        pagos = self.pagos_de_turno(turno.id)
        aplicados = [p for p in pagos if p.estado == "aplicado"]
        por_medio = {}
        for pago in aplicados:
            medio = medios.get(pago.medio_pago_id)
            fila = por_medio.setdefault(pago.medio_pago_id, {"medio": medio.nombre if medio else "?",
                                                             "tipo": medio.tipo if medio else "otro", "monto": 0, "pagos": 0})
            fila["monto"] += pago.monto
            fila["pagos"] += 1

        movimientos = self.movimientos_de_turno(turno.id)
        suma = {tipo: sum(m.monto for m in movimientos if m.tipo == tipo) for tipo in ["gasto", "retiro", "aporte"]}
        efectivo = sum(p.monto for p in aplicados if medios.get(p.medio_pago_id) and medios[p.medio_pago_id].tipo == "efectivo")
        cuentas = [c for c in self.cuentas_de_turno(turno.id) if c.estado == "pagada"]
        # Los pagos contra entrega entran como efectivo al rendir; el faltante lo debe el domiciliario
        faltantes = sum(-r.diferencia for r in self.rendiciones_de_turno(turno.id) if r.diferencia < 0)
        sobrantes = sum(r.diferencia for r in self.rendiciones_de_turno(turno.id) if r.diferencia > 0)

        return {
            "por_medio": list(por_medio.values()),
            "cobrado": sum(p.monto for p in aplicados),
            "efectivo_ventas": efectivo,
            "cuentas": len(cuentas),
            "ventas": sum(c.subtotal - c.descuento - c.descuento_cupon for c in cuentas),
            "propinas": sum(c.propina for c in cuentas),
            "descuentos": sum(c.descuento + c.descuento_cupon for c in cuentas),
            "cupones": sum(c.descuento_cupon + c.descuento_envio for c in cuentas),
            "domicilios": sum(c.envio - c.descuento_envio for c in cuentas),
            "faltantes_domiciliarios": faltantes,
            "sobrantes_domiciliarios": sobrantes,
            "pagos_anulados": sum(1 for p in pagos if p.estado == "anulado"),
            "gastos": suma["gasto"],
            "retiros": suma["retiro"],
            "aportes": suma["aporte"],
            "movimientos": [{"id": m.id, "tipo": m.tipo, "monto": m.monto, "concepto": m.concepto,
                             "usuario": self.nombre_usuario(m.usuario_id), "creado_en": m.creado_en} for m in movimientos],
            # Lo que debería haber en el cajón (RN-CAJ-06)
            "efectivo_esperado": turno.fondo_inicial + efectivo + suma["aporte"] - suma["retiro"] - suma["gasto"]
            - faltantes + sobrantes,
        }

    def format_turno(self, turno, con_resumen=True):
        data = {
            "id": turno.id,
            "estado": turno.estado,
            "jornada": turno.jornada,
            "usuario": self.nombre_usuario(turno.usuario_id),
            "abierto_en": turno.abierto_en,
            "fondo_inicial": turno.fondo_inicial,
            "cerrado_en": turno.cerrado_en,
            "cerrado_por": self.nombre_usuario(turno.cerrado_por),
            "efectivo_esperado": turno.efectivo_esperado,
            "efectivo_contado": turno.efectivo_contado,
            "diferencia": turno.diferencia,
            "observacion": turno.observacion,
        }
        if con_resumen:
            data["resumen"] = self.resumen_turno(turno)
        return data

    def format_cuenta(self, cuenta, sesion=None, propina_sugerida=0):
        sesion = sesion or self.db.get(SesionMesaModel, cuenta.sesion_mesa_id)
        mesa = self.db.get(MesaModel, cuenta.mesa_id)
        zona = self.db.get(ZonaModel, cuenta.zona_id)
        ordenes = self.ordenes_de_sesion(cuenta.sesion_mesa_id)
        filas = self.items_de_sesion(cuenta.sesion_mesa_id)
        modificadores = self.modifiers_of([item.id for item, _ in filas])
        medios = {m.id: m.nombre for m in self.medios(incluir_inactivos=True)}

        return {
            "id": cuenta.id,
            "numero": cuenta.numero,
            "numero_texto": f"C-{cuenta.numero:05d}" if cuenta.numero else None,
            "estado": cuenta.estado,
            "solicitada": cuenta.solicitada,
            "sesion_mesa_id": cuenta.sesion_mesa_id,
            "mesa_id": cuenta.mesa_id,
            "mesa": mesa.nombre if mesa else None,
            "mesa_tipo": mesa.tipo if mesa else None,
            "zona": zona.nombre if zona else None,
            "cliente_nombre": next((o.cliente_nombre for o in ordenes if o.cliente_nombre), None),
            # Venta directa de caja (POS de mostrador, ADR-007)
            "venta_directa": bool(ordenes) and all(o.canal == "pos" for o in ordenes),
            "mesero": self.nombre_usuario(sesion.mesero_id) if sesion else None,
            "abierta_en": sesion.abierta_en if sesion else None,
            "ordenes": [f"#{o.numero:03d}" for o in ordenes],
            "lineas": [{
                "id": item.id,
                "orden": f"#{numero:03d}",
                "nombre": item.nombre_producto,
                "modificadores": modificadores.get(item.id, []),
                "cantidad": item.cantidad,
                "precio_unitario": item.precio_unitario,
                "total": item.total,
                "estado": item.estado,
            } for item, numero in filas if item.estado != CANCELADO],
            "items_pendientes": sum(1 for item, _ in filas if item.estado in PENDIENTES_DE_ENTREGA),
            "subtotal": cuenta.subtotal,
            "descuento": cuenta.descuento,
            "descuento_motivo": cuenta.descuento_motivo,
            "descuento_cupon": cuenta.descuento_cupon,
            "descuento_envio": cuenta.descuento_envio,
            "propina": cuenta.propina,
            "propina_sugerida": round((cuenta.subtotal - cuenta.descuento - cuenta.descuento_cupon) * propina_sugerida / 100),
            "propina_porcentaje": propina_sugerida,
            "envio": cuenta.envio,
            "entrega": self.format_entrega_corta(self.entrega_de_sesion(cuenta.sesion_mesa_id)),
            "total": cuenta.total,
            "pagado": cuenta.pagado,
            "saldo": cuenta.total - cuenta.pagado,
            "jornada": cuenta.jornada,
            "pagada_en": cuenta.pagada_en,
            "cobrada_por": self.nombre_usuario(cuenta.cobrada_por),
            "anulada_motivo": cuenta.anulada_motivo,
            "pagos": [{
                "id": p.id,
                "medio": medios.get(p.medio_pago_id),
                "monto": p.monto,
                "recibido": p.recibido,
                "cambio": p.cambio,
                "referencia": p.referencia,
                "estado": p.estado,
                "usuario": self.nombre_usuario(p.usuario_id),
                "creado_en": p.creado_en,
                "anulado_motivo": p.anulado_motivo,
            } for p in self.pagos_de(cuenta.id)],
        }

    def format_entrega_corta(self, entrega):
        if not entrega:
            return None
        from Models.zona_envio_model import ZonaEnvioModel
        zona = self.db.get(ZonaEnvioModel, entrega.zona_envio_id)
        return {"id": entrega.id, "estado": entrega.estado, "zona_envio": zona.nombre if zona else None,
                "direccion": entrega.direccion, "barrio": entrega.barrio, "indicaciones": entrega.indicaciones,
                "telefono": entrega.telefono, "tarifa": entrega.tarifa, "contra_entrega": entrega.contra_entrega}
