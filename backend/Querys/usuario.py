from Querys.base import Querys
from Models.usuario_model import UsuarioModel
from Models.rol_model import RolModel
from Models.usuario_rol_model import UsuarioRolModel
from Models.usuario_restaurante_model import UsuarioRestauranteModel
from Models.usuario_zona_model import UsuarioZonaModel
from Models.usuario_punto_model import UsuarioPuntoModel
from Models.zona_model import ZonaModel
from Models.punto_produccion_model import PuntoProduccionModel
from Utils.tools import CustomException
from sqlalchemy import or_


class UsuarioQuerys(Querys):

    # Usuarios de la empresa que entran al restaurante actual (los admin de empresa entran a todos)
    def list_usuarios(self, incluir_inactivos=False):
        admins_empresa = self.db.query(UsuarioRolModel.usuario_id).join(
            RolModel, RolModel.id == UsuarioRolModel.rol_id
        ).filter(RolModel.alcance == "empresa")
        con_acceso = self.db.query(UsuarioRestauranteModel.usuario_id).filter(
            UsuarioRestauranteModel.restaurante_id == self.restaurante_id
        )
        query = self.db.query(UsuarioModel).filter(
            UsuarioModel.empresa_id == self.empresa_id,
            UsuarioModel.eliminado_en.is_(None),
            or_(UsuarioModel.id.in_(admins_empresa), UsuarioModel.id.in_(con_acceso)),
        )
        if not incluir_inactivos:
            query = query.filter(UsuarioModel.activo.is_(True))
        return query.order_by(UsuarioModel.nombre.asc()).all()

    # Un usuario de la empresa con acceso al restaurante actual
    def get_usuario(self, usuario_id):
        usuarios = {u.id: u for u in self.list_usuarios(incluir_inactivos=True)}
        usuario = usuarios.get(int(usuario_id))
        if not usuario:
            raise CustomException("El usuario no existe.", 404)
        return usuario

    def usuario_exists(self, usuario: str, exclude_id=None):
        query = self.db.query(UsuarioModel).filter(UsuarioModel.usuario == usuario)
        if exclude_id:
            query = query.filter(UsuarioModel.id != exclude_id)
        return query.first() is not None

    def pin_in_use(self, empresa_id, huella: str, exclude_id):
        return self.db.query(UsuarioModel).filter(
            UsuarioModel.empresa_id == empresa_id, UsuarioModel.pin_hash == huella, UsuarioModel.id != exclude_id
        ).first() is not None

    def get_roles(self, codigos: list = None):
        query = self.db.query(RolModel).filter(RolModel.alcance != "plataforma")
        if codigos is not None:
            query = query.filter(RolModel.codigo.in_(codigos or [""]))
        return query.order_by(RolModel.id.asc()).all()

    def get_roles_usuario(self, usuario_id):
        return self.db.query(RolModel).join(
            UsuarioRolModel, UsuarioRolModel.rol_id == RolModel.id
        ).filter(UsuarioRolModel.usuario_id == usuario_id).all()

    def get_zonas_usuario(self, usuario_id):
        return [z for (z,) in self.scoped(UsuarioZonaModel).with_entities(UsuarioZonaModel.zona_id).filter(
            UsuarioZonaModel.usuario_id == usuario_id).all()]

    def get_puntos_usuario(self, usuario_id):
        return [p for (p,) in self.scoped(UsuarioPuntoModel).with_entities(UsuarioPuntoModel.punto_produccion_id).filter(
            UsuarioPuntoModel.usuario_id == usuario_id).all()]

    def valid_zonas(self, ids: list):
        return {z.id for z in self.scoped(ZonaModel).filter(ZonaModel.id.in_(ids or [0])).all()}

    def valid_puntos(self, ids: list):
        return {p.id for p in self.scoped(PuntoProduccionModel).filter(PuntoProduccionModel.id.in_(ids or [0])).all()}

    # Reemplaza roles, acceso al restaurante, zonas y puntos de un usuario
    def set_asignaciones(self, usuario_id, roles: list, zonas: list, puntos: list):
        self.db.query(UsuarioRolModel).filter(UsuarioRolModel.usuario_id == usuario_id).delete()
        for rol in roles:
            self.db.add(UsuarioRolModel({"usuario_id": usuario_id, "rol_id": rol.id}))

        if not self.scoped(UsuarioRestauranteModel).filter(UsuarioRestauranteModel.usuario_id == usuario_id).first():
            self.insert_data(UsuarioRestauranteModel, {"usuario_id": usuario_id}, commit=False)

        self.scoped(UsuarioZonaModel).filter(UsuarioZonaModel.usuario_id == usuario_id).delete(synchronize_session=False)
        for zona_id in zonas:
            self.insert_data(UsuarioZonaModel, {"usuario_id": usuario_id, "zona_id": zona_id}, commit=False)

        self.scoped(UsuarioPuntoModel).filter(UsuarioPuntoModel.usuario_id == usuario_id).delete(synchronize_session=False)
        for punto_id in puntos:
            self.insert_data(UsuarioPuntoModel, {"usuario_id": usuario_id, "punto_produccion_id": punto_id}, commit=False)
        self.db.flush()

    # Administradores activos del restaurante (RN-USR-04)
    def count_admins_activos(self, exclude_id=None):
        count = 0
        for usuario in self.list_usuarios():
            if usuario.id == exclude_id:
                continue
            if any(rol.codigo in ["admin_restaurante", "admin_empresa"] for rol in self.get_roles_usuario(usuario.id)):
                count += 1
        return count

    def format_usuario(self, usuario):
        return {
            "id": usuario.id,
            "usuario": usuario.usuario,
            "nombre": usuario.nombre,
            "documento": usuario.documento,
            "correo": usuario.correo,
            "activo": usuario.activo,
            "tiene_pin": usuario.pin_hash is not None,
            "ultimo_acceso": usuario.ultimo_acceso,
            "roles": [rol.codigo for rol in self.get_roles_usuario(usuario.id)],
            "zonas": self.get_zonas_usuario(usuario.id),
            "puntos": self.get_puntos_usuario(usuario.id),
        }
