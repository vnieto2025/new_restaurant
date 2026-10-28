from Querys.base import Querys
from Models.usuario_model import UsuarioModel
from Models.restaurante_model import RestauranteModel
from Models.zona_model import ZonaModel
from Models.punto_produccion_model import PuntoProduccionModel
from Utils.tools import now


class AuthQuerys(Querys):

    # Query for obtain data of user to log
    def get_usuario_login(self, usuario: str):
        return self.db.query(UsuarioModel).filter(
            UsuarioModel.usuario == usuario,
            UsuarioModel.activo.is_(True),
            UsuarioModel.eliminado_en.is_(None),
        ).first()

    def get_usuario(self, usuario_id):
        return self.db.query(UsuarioModel).filter(UsuarioModel.id == usuario_id).first()

    def touch_ultimo_acceso(self, usuario_id):
        self.db.query(UsuarioModel).filter(UsuarioModel.id == usuario_id).update({"ultimo_acceso": now()})
        self.db.commit()

    def update_password(self, usuario_id, password_hash):
        self.db.query(UsuarioModel).filter(UsuarioModel.id == usuario_id).update({"password": password_hash})
        self.db.commit()

    def get_restaurante(self, restaurante_id):
        return self.db.query(RestauranteModel).filter(RestauranteModel.id == restaurante_id).first()

    # Zonas y puntos con nombre, para que la interfaz arme sus menús
    def get_zonas(self, restaurante_id, ids=None):
        query = self.db.query(ZonaModel).filter(
            ZonaModel.restaurante_id == restaurante_id,
            ZonaModel.activo.is_(True),
            ZonaModel.eliminado_en.is_(None),
        )
        if ids is not None:
            query = query.filter(ZonaModel.id.in_(ids or [0]))
        return [
            {"id": z.id, "nombre": z.nombre, "es_mostrador": z.es_mostrador}
            for z in query.order_by(ZonaModel.orden.asc(), ZonaModel.id.asc()).all()
        ]

    def get_puntos(self, restaurante_id, ids=None):
        query = self.db.query(PuntoProduccionModel).filter(
            PuntoProduccionModel.restaurante_id == restaurante_id,
            PuntoProduccionModel.activo.is_(True),
            PuntoProduccionModel.eliminado_en.is_(None),
        )
        if ids is not None:
            query = query.filter(PuntoProduccionModel.id.in_(ids or [0]))
        return [
            {"id": p.id, "nombre": p.nombre, "tipo": p.tipo}
            for p in query.order_by(PuntoProduccionModel.id.asc()).all()
        ]
