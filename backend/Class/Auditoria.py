from sqlalchemy import or_
from Utils.tools import Tools
from Querys.base import Querys
from Models.auditoria_model import AuditoriaModel
from Models.usuario_model import UsuarioModel

MAX_LIMITE = 200


class Auditoria:

    def __init__(self, db, ctx: dict):
        self.db = db
        self.tools = Tools()
        self.querys = Querys(db, ctx)

    # Línea de tiempo: quién, qué, cuándo (doc 30)
    def list(self, data: dict):

        limite = min(int(data.get("limite") or 50), MAX_LIMITE)
        # Lo del restaurante más lo de la empresa que no es de ningún restaurante (ej. ingresos fallidos)
        query = self.db.query(AuditoriaModel).filter(
            AuditoriaModel.empresa_id == self.querys.empresa_id,
            or_(AuditoriaModel.restaurante_id == self.querys.restaurante_id, AuditoriaModel.restaurante_id.is_(None)),
        )
        if data.get("accion"):
            query = query.filter(AuditoriaModel.accion == data["accion"])
        registros = query.order_by(AuditoriaModel.id.desc()).limit(limite).all()

        usuarios = {u.id: u.nombre for u in self.db.query(UsuarioModel).filter(
            UsuarioModel.id.in_([r.usuario_id for r in registros if r.usuario_id] or [0])).all()}
        result = [{
            "id": r.id,
            "accion": r.accion,
            "entidad": r.entidad,
            "entidad_id": r.entidad_id,
            "usuario": usuarios.get(r.usuario_id),
            "antes": r.antes,
            "despues": r.despues,
            "motivo": r.motivo,
            "ip": r.ip,
            "creado_en": r.creado_en,
        } for r in registros]

        msg = "Registro de auditoría." if result else "No hay registros de auditoría."
        return self.tools.output(200, msg, result)
