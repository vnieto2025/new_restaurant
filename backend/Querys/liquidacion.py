from Querys.usuario import UsuarioQuerys
from Models.liquidacion_model import LiquidacionModel
from Models.liquidacion_linea_model import LiquidacionLineaModel
from Models.liquidacion_ajuste_model import LiquidacionAjusteModel
from Models.liquidacion_config_model import LiquidacionConfigModel
from Models.cuenta_model import CuentaModel
from Models.sesion_mesa_model import SesionMesaModel
from Models.entrega_model import EntregaModel
from Models.orden_model import OrdenModel
from Models.rendicion_model import RendicionModel
from Models.domiciliario_model import DomiciliarioModel
from Models.turno_mesero_model import TurnoMeseroModel
from Models.usuario_zona_model import UsuarioZonaModel
from Models.zona_model import ZonaModel
from sqlalchemy import and_, exists


class LiquidacionQuerys(UsuarioQuerys):

    def config(self):
        return self.scoped(LiquidacionConfigModel).first()

    def list_liquidaciones(self, tipo, limite=24):
        return self.scoped(LiquidacionModel).filter(LiquidacionModel.tipo == tipo).order_by(
            LiquidacionModel.desde.desc()).limit(limite).all()

    def por_periodo(self, tipo, desde, lock=False):
        query = self.scoped(LiquidacionModel).filter(LiquidacionModel.tipo == tipo, LiquidacionModel.desde == desde)
        if lock:
            query = query.with_for_update()
        return query.first()

    def calculada(self, tipo):
        return self.scoped(LiquidacionModel).filter(LiquidacionModel.tipo == tipo,
                                                    LiquidacionModel.estado == "calculada").first()

    def lineas(self, liquidacion_id):
        return self.scoped(LiquidacionLineaModel).filter(LiquidacionLineaModel.liquidacion_id == liquidacion_id).order_by(
            LiquidacionLineaModel.nombre.asc()).all()

    def delete_lineas(self, liquidacion_id):
        self.scoped(LiquidacionLineaModel).filter(LiquidacionLineaModel.liquidacion_id == liquidacion_id).delete(
            synchronize_session=False)

    def ajustes(self, tipo, liquidacion_id=None):
        """ Los de una liquidación, o los pendientes (sin liquidación) que entran en la siguiente """
        query = self.scoped(LiquidacionAjusteModel).filter(LiquidacionAjusteModel.tipo == tipo)
        if liquidacion_id:
            query = query.filter(LiquidacionAjusteModel.liquidacion_id == liquidacion_id)
        else:
            query = query.filter(LiquidacionAjusteModel.liquidacion_id.is_(None))
        return query.order_by(LiquidacionAjusteModel.id.asc()).all()

    # ---- Propinas ----

    def _domicilio_con_domiciliario(self):
        return exists().where(and_(EntregaModel.sesion_mesa_id == CuentaModel.sesion_mesa_id,
                                   EntregaModel.estado == "entregada", EntregaModel.domiciliario_id.isnot(None)))

    def propinas_por_liquidar(self, hasta, domicilios=None):
        """ Cuentas pagadas con propina que ninguna liquidación ha repartido, hasta el fin del periodo.
            Incluye las de periodos anteriores que llegaron tarde: ninguna propina se pierde.
            domicilios: None = todas; False = sin las de domicilio entregado; True = solo esas. """
        query = self.scoped(CuentaModel).join(SesionMesaModel, SesionMesaModel.id == CuentaModel.sesion_mesa_id).filter(
            CuentaModel.estado == "pagada", CuentaModel.propina > 0, CuentaModel.liquidacion_propina_id.is_(None),
            CuentaModel.jornada <= hasta).add_columns(SesionMesaModel.mesero_id)
        if domicilios is False:
            query = query.filter(~self._domicilio_con_domiciliario())
        elif domicilios is True:
            query = query.filter(self._domicilio_con_domiciliario())
        return query.order_by(CuentaModel.id.asc()).all()

    def domiciliario_de_sesion(self, sesion_id):
        entrega = self.scoped(EntregaModel).filter(EntregaModel.sesion_mesa_id == sesion_id,
                                                   EntregaModel.estado == "entregada").first()
        return entrega.domiciliario_id if entrega else None

    def propinas_de_mesero(self, usuario_id, desde, hasta):
        filas = self.scoped(CuentaModel).join(SesionMesaModel, SesionMesaModel.id == CuentaModel.sesion_mesa_id).filter(
            CuentaModel.estado == "pagada", SesionMesaModel.mesero_id == usuario_id,
            CuentaModel.liquidacion_propina_id.is_(None), CuentaModel.jornada >= desde, CuentaModel.jornada <= hasta).all()
        return sum(c.propina for c in filas), len([c for c in filas if c.propina])

    def zonas_de_usuarios(self, usuario_ids):
        zonas = {}
        for fila in self.scoped(UsuarioZonaModel).filter(UsuarioZonaModel.usuario_id.in_(usuario_ids or [0])).all():
            zonas.setdefault(fila.usuario_id, []).append(fila.zona_id)
        return zonas

    def horas(self, usuario_ids, desde, hasta):
        """ Horas de los turnos cerrados del periodo (doc 08A). No reemplaza el registro laboral. """
        horas = {}
        for turno in self.scoped(TurnoMeseroModel).filter(
                TurnoMeseroModel.usuario_id.in_(usuario_ids or [0]), TurnoMeseroModel.estado == "cerrado",
                TurnoMeseroModel.jornada >= desde, TurnoMeseroModel.jornada <= hasta, TurnoMeseroModel.fin.isnot(None)).all():
            horas[turno.usuario_id] = horas.get(turno.usuario_id, 0) + (turno.fin - turno.inicio).total_seconds() / 3600
        return horas

    def nombres_zonas(self):
        return {z.id: z.nombre for z in self.scoped(ZonaModel).all()}

    # ---- Domiciliarios ----

    def entregas_por_liquidar(self, hasta):
        return self.scoped(EntregaModel).join(OrdenModel, OrdenModel.id == EntregaModel.orden_id).filter(
            EntregaModel.estado == "entregada", EntregaModel.domiciliario_id.isnot(None),
            EntregaModel.liquidacion_id.is_(None), OrdenModel.jornada <= hasta).order_by(EntregaModel.id.asc()).all()

    def faltantes_por_liquidar(self):
        return self.scoped(RendicionModel).filter(RendicionModel.diferencia < 0, RendicionModel.liquidacion_id.is_(None)).all()

    def por_rendir(self):
        """ Efectivo cobrado contra entrega que el domiciliario aún no ha rendido en caja """
        pendientes = {}
        for entrega in self.scoped(EntregaModel).filter(EntregaModel.estado == "entregada", EntregaModel.contra_entrega.is_(True),
                                                        EntregaModel.rendicion_id.is_(None),
                                                        EntregaModel.domiciliario_id.isnot(None)).all():
            pendientes[entrega.domiciliario_id] = pendientes.get(entrega.domiciliario_id, 0) + entrega.monto_a_cobrar
        return pendientes

    def domiciliarios(self):
        return self.scoped(DomiciliarioModel).order_by(DomiciliarioModel.codigo.asc()).all()

    # ---- Lo propio (RN-PRP-05) ----

    def lineas_de_usuario(self, usuario_id, limite=12):
        domiciliarios = [d.id for d in self.scoped(DomiciliarioModel).filter(DomiciliarioModel.usuario_id == usuario_id)]
        condicion = LiquidacionLineaModel.usuario_id == usuario_id
        if domiciliarios:
            condicion = condicion | LiquidacionLineaModel.domiciliario_id.in_(domiciliarios)
        return self.scoped(LiquidacionLineaModel).join(
            LiquidacionModel, LiquidacionModel.id == LiquidacionLineaModel.liquidacion_id).filter(
            condicion, LiquidacionModel.estado.in_(["aprobada", "pagada"])).add_entity(LiquidacionModel).order_by(
            LiquidacionModel.desde.desc()).limit(limite).all()
