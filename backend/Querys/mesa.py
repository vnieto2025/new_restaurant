from Querys.base import Querys
from Models.mesa_model import MesaModel
from Models.zona_model import ZonaModel
from Models.sesion_mesa_model import SesionMesaModel
from Models.orden_model import OrdenModel
from Models.orden_item_model import OrdenItemModel
from Models.usuario_model import UsuarioModel
from Models.cuenta_model import CuentaModel
from Utils.estados import CANCELADO
from Utils.tools import now
from sqlalchemy import func


class MesaQuerys(Querys):

    def list_mesas(self, zona_ids=None, zona_id=None, incluir_externa=False, incluir_inactivas=False):
        query = self.scoped(MesaModel).join(ZonaModel, ZonaModel.id == MesaModel.zona_id).filter(
            ZonaModel.eliminado_en.is_(None)
        )
        if zona_ids is not None:
            query = query.filter(MesaModel.zona_id.in_(zona_ids or [0]))
        if zona_id:
            query = query.filter(MesaModel.zona_id == int(zona_id))
        if not incluir_externa:
            query = query.filter(MesaModel.tipo == "normal")
        if not incluir_inactivas:
            query = query.filter(MesaModel.activo.is_(True), ZonaModel.activo.is_(True))
        return query.order_by(ZonaModel.orden.asc(), MesaModel.orden.asc(), MesaModel.id.asc()).all()

    def name_exists(self, zona_id, nombre: str, exclude_id=None):
        query = self.scoped(MesaModel, include_deleted=True).filter(
            MesaModel.zona_id == zona_id, func.lower(MesaModel.nombre) == nombre.lower()
        )
        if exclude_id:
            query = query.filter(MesaModel.id != exclude_id)
        return query.first() is not None

    def max_orden(self, zona_id):
        value = self.scoped(MesaModel).with_entities(func.max(MesaModel.orden)).filter(
            MesaModel.zona_id == zona_id).scalar()
        return value or 0

    def get_mesa_externa(self):
        return self.scoped(MesaModel).filter(MesaModel.tipo == "externa").first()

    # Sesión abierta de una mesa normal (la externa tiene una por orden)
    def get_open_session(self, mesa_id, lock=False):
        query = self.scoped(SesionMesaModel).filter(
            SesionMesaModel.mesa_id == mesa_id,
            SesionMesaModel.estado == "abierta",
            SesionMesaModel.es_externa.is_(False),
        )
        if lock:
            query = query.with_for_update()
        return query.first()

    def open_session(self, mesa, mesero_id=None):
        sesion_id = self.insert_data(SesionMesaModel, {
            "mesa_id": mesa.id,
            "zona_id": mesa.zona_id,
            "es_externa": mesa.tipo == "externa",
            "mesero_id": mesero_id,
            "abierta_en": now(),
        }, commit=False)
        return self.db.get(SesionMesaModel, sesion_id)

    def close_session(self, sesion, usuario_id=None):
        sesion.estado = "cerrada"
        sesion.cerrada_en = now()
        sesion.cerrada_por = usuario_id
        self.db.flush()

    # Estados de los ítems y total de las órdenes de varias sesiones de una vez
    def items_by_session(self, sesion_ids: list):
        rows = self.scoped(OrdenItemModel).join(
            OrdenModel, OrdenModel.id == OrdenItemModel.orden_id
        ).with_entities(
            OrdenModel.sesion_mesa_id, OrdenItemModel.estado, OrdenItemModel.total
        ).filter(OrdenModel.sesion_mesa_id.in_(sesion_ids or [0])).all()

        result = {}
        for sesion_id, estado, total in rows:
            data = result.setdefault(sesion_id, {"estados": [], "total": 0})
            data["estados"].append(estado)
            if estado != CANCELADO:
                data["total"] += total
        return result

    def open_sessions(self, mesa_ids: list):
        rows = self.scoped(SesionMesaModel).filter(
            SesionMesaModel.mesa_id.in_(mesa_ids or [0]),
            SesionMesaModel.estado == "abierta",
            SesionMesaModel.es_externa.is_(False),
        ).all()
        return {sesion.mesa_id: sesion for sesion in rows}

    # Sesiones cuya cuenta ya se pidió (para marcar la mesa)
    def sessions_with_bill_requested(self, sesion_ids: list):
        return {c.sesion_mesa_id for c in self.scoped(CuentaModel).filter(
            CuentaModel.sesion_mesa_id.in_(sesion_ids or [0]), CuentaModel.solicitada.is_(True),
            CuentaModel.estado == "abierta").all()}

    def ordenes_de_sesion(self, sesion_id):
        return self.scoped(OrdenModel).filter(OrdenModel.sesion_mesa_id == sesion_id).all()

    def cuenta_de_sesion(self, sesion_id):
        return self.scoped(CuentaModel).filter(CuentaModel.sesion_mesa_id == sesion_id).first()

    def get_usuario_nombre(self, usuario_id):
        if not usuario_id:
            return None
        usuario = self.db.get(UsuarioModel, usuario_id)
        return usuario.nombre if usuario else None
