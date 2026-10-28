from fastapi import HTTPException
from Config.db import SessionLocal
from Models.usuario_model import UsuarioModel
from Models.usuario_rol_model import UsuarioRolModel
from Models.rol_model import RolModel
from Models.rol_permiso_model import RolPermisoModel
from Models.permiso_model import PermisoModel
from Models.empresa_model import EmpresaModel
from Models.restaurante_model import RestauranteModel
from Models.usuario_restaurante_model import UsuarioRestauranteModel
from Models.usuario_zona_model import UsuarioZonaModel
from Models.usuario_punto_model import UsuarioPuntoModel
from Models.contrato_model import ContratoModel
from Models.contrato_modulo_model import ContratoModuloModel
from Models.modulo_model import ModuloModel
from Models.dispositivo_model import DispositivoModel
from Utils.tools import jornada

# Estados de contrato con los que el restaurante opera (doc 02A, sección 3)
CONTRATO_OPERATIVO = ["prueba", "activo"]


def sesion_invalida(message="La sesión ya no es válida. Ingrese de nuevo."):
    return HTTPException(status_code=401, detail=message)


def prohibido(codigo: str, message: str):
    return HTTPException(status_code=403, detail={"codigo": codigo, "mensaje": message})


def roles_de_usuario(db, usuario_id):
    return db.query(RolModel).join(
        UsuarioRolModel, UsuarioRolModel.rol_id == RolModel.id
    ).filter(UsuarioRolModel.usuario_id == usuario_id).all()


def permisos_de_roles(db, rol_ids):
    if not rol_ids:
        return []
    return db.query(PermisoModel).join(
        RolPermisoModel, RolPermisoModel.permiso_id == PermisoModel.id
    ).filter(RolPermisoModel.rol_id.in_(rol_ids)).distinct().all()


# Restaurantes a los que entra un usuario: todos los de su empresa si es admin de empresa
def restaurantes_de_usuario(db, usuario, roles):
    query = db.query(RestauranteModel).filter(
        RestauranteModel.empresa_id == usuario.empresa_id,
        RestauranteModel.estado != "inactivo",
    )
    if not any(rol.alcance == "empresa" for rol in roles):
        query = query.join(
            UsuarioRestauranteModel, UsuarioRestauranteModel.restaurante_id == RestauranteModel.id
        ).filter(UsuarioRestauranteModel.usuario_id == usuario.id)
    return query.order_by(RestauranteModel.id.asc()).all()


# Módulos con los que opera hoy el restaurante según su contrato
def modulos_activos(db, restaurante):
    contrato = db.query(ContratoModel).filter(ContratoModel.restaurante_id == restaurante.id).first()
    obligatorios = {m.codigo for m in db.query(ModuloModel).filter(ModuloModel.obligatorio.is_(True)).all()}
    if not contrato:
        return obligatorios, None

    vigente = contrato.estado in CONTRATO_OPERATIVO
    hoy = jornada(tz_name=restaurante.zona_horaria, inicio=restaurante.hora_inicio_jornada)
    if contrato.fecha_fin and contrato.fecha_fin < hoy:
        vigente = False

    if not vigente:
        return obligatorios, contrato.estado

    contratados = db.query(ModuloModel.codigo).join(
        ContratoModuloModel, ContratoModuloModel.modulo_id == ModuloModel.id
    ).filter(ContratoModuloModel.contrato_id == contrato.id).all()
    return obligatorios | {codigo for (codigo,) in contratados}, contrato.estado


def cargar_contexto(token_data: dict, ip: str = None, dispositivo: str = None, db=None):
    """ Arma el contexto de la petición a partir del token: identidad, empresa, restaurante,
        permisos efectivos, módulos contratados y alcance (zonas y puntos de producción).
        Se recalcula en cada petición, así un cambio de permisos o una desactivación
        aplica de inmediato a las sesiones abiertas (RN-PER-05, RN-USR-05). """

    own_session = db is None
    db = db or SessionLocal()
    try:
        usuario = db.query(UsuarioModel).filter(
            UsuarioModel.id == token_data.get("usuario_id"),
            UsuarioModel.activo.is_(True),
            UsuarioModel.eliminado_en.is_(None),
        ).first()
        if not usuario:
            raise sesion_invalida()

        roles = roles_de_usuario(db, usuario.id)
        permisos = permisos_de_roles(db, [rol.id for rol in roles])
        ctx = {
            "usuario_id": usuario.id,
            "nombre": usuario.nombre,
            "roles": [rol.codigo for rol in roles],
            "empresa_id": usuario.empresa_id,
            "restaurante_id": None,
            "permisos": set(),
            "modulos": set(),
            "zonas": None,
            "puntos": None,
            "ip": ip,
            "dispositivo": (dispositivo or "")[:250] or None,
        }

        if any(rol.alcance == "plataforma" for rol in roles):
            ctx["permisos"] = {p.codigo for p in permisos}
            ctx["plataforma"] = True
            return ctx

        empresa = db.query(EmpresaModel).filter(EmpresaModel.id == usuario.empresa_id).first()
        if not empresa or empresa.estado == "cancelada":
            raise sesion_invalida("La empresa no tiene acceso a la plataforma.")

        restaurante_id = token_data.get("restaurante_id")
        restaurantes = restaurantes_de_usuario(db, usuario, roles)
        restaurante = next((r for r in restaurantes if r.id == restaurante_id), None)
        if not restaurante:
            raise sesion_invalida("No tiene acceso a este restaurante.")

        dispositivo = None
        if token_data.get("dispositivo_id"):
            dispositivo = db.query(DispositivoModel).filter(
                DispositivoModel.id == token_data["dispositivo_id"],
                DispositivoModel.restaurante_id == restaurante.id,
                DispositivoModel.activo.is_(True),
                DispositivoModel.token_hash.isnot(None),
            ).first()
            if not dispositivo:
                raise sesion_invalida("Este dispositivo ya no está autorizado.")

        modulos, contrato_estado = modulos_activos(db, restaurante)
        if empresa.estado == "suspendida":
            modulos = {m for m in modulos if m == "base"}

        ctx.update({
            "restaurante_id": restaurante.id,
            "zona_horaria": restaurante.zona_horaria,
            "hora_inicio_jornada": restaurante.hora_inicio_jornada,
            "moneda": restaurante.moneda,
            "modulos": modulos,
            "contrato_estado": contrato_estado,
            "dispositivo_id": dispositivo.id if dispositivo else None,
            # Un permiso solo es efectivo si su módulo está contratado (RN-PER-04)
            "permisos": {p.codigo for p in permisos if p.modulo in modulos},
        })

        alcance_total = any(rol.alcance in ["empresa", "restaurante"] for rol in roles)
        if not alcance_total:
            ctx["zonas"] = [z for (z,) in db.query(UsuarioZonaModel.zona_id).filter(
                UsuarioZonaModel.usuario_id == usuario.id,
                UsuarioZonaModel.restaurante_id == restaurante.id,
            ).all()]
            ctx["puntos"] = [p for (p,) in db.query(UsuarioPuntoModel.punto_produccion_id).filter(
                UsuarioPuntoModel.usuario_id == usuario.id,
                UsuarioPuntoModel.restaurante_id == restaurante.id,
            ).all()]

        return ctx
    finally:
        if own_session:
            db.close()


def exigir(ctx: dict, permisos: list = None, modulo: str = None):
    """ Verifica módulo contratado y permisos (basta con uno de la lista) """
    if modulo and modulo not in ctx.get("modulos", set()) and not ctx.get("plataforma"):
        raise prohibido("modulo_no_contratado", "Este módulo no está incluido en el contrato del restaurante.")
    if permisos and not (set(permisos) & ctx.get("permisos", set())):
        raise prohibido("permiso_insuficiente", "No tienes permiso para realizar esta acción.")
