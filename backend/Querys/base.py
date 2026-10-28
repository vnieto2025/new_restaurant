from Utils.tools import Tools, CustomException, now
from Models.auditoria_model import AuditoriaModel
from sqlalchemy import text


class Querys:
    """ Consultas comunes a todos los módulos.
        Cada módulo tiene su propia clase en Querys/<modulo>.py que hereda de esta.

        ctx es el contexto de la petición (Utils/contexto.py). Cuando trae empresa y restaurante,
        toda lectura y escritura queda limitada a ellos (RG-16): el aislamiento lo aplica el backend,
        no la interfaz. """

    def __init__(self, db, ctx: dict = None):
        self.db = db
        self.ctx = ctx or {}
        self.tools = Tools()
        self.bind_tenant()

    # Fija la empresa de la petición en la sesión de base de datos para Row Level Security (ADR-023).
    # Solo en peticiones de una persona o de un cliente por QR; nunca en la consola de plataforma.
    def bind_tenant(self):
        if not self.empresa_id or self.ctx.get("plataforma"):
            return
        if "usuario_id" not in self.ctx and not self.ctx.get("publico"):
            return
        if self.db.info.get("empresa_id") == self.empresa_id:
            return
        self.db.info["empresa_id"] = self.empresa_id
        if self.db.in_transaction():
            self.db.execute(text("SELECT set_config('app.empresa_id', :empresa, true)"), {"empresa": str(self.empresa_id)})

    @property
    def empresa_id(self):
        return self.ctx.get("empresa_id")

    @property
    def restaurante_id(self):
        return self.ctx.get("restaurante_id")

    # Fija empresa y restaurante del contexto en los datos a guardar (no se aceptan los que mande el cliente)
    def _with_tenant(self, model: any, data: dict):
        columns = model.__table__.columns.keys()
        data = dict(data)
        if "empresa_id" in columns and self.empresa_id:
            data["empresa_id"] = self.empresa_id
        if "restaurante_id" in columns and self.restaurante_id:
            data["restaurante_id"] = self.restaurante_id
        return data

    # Consulta de un modelo limitada a la empresa y el restaurante de la petición
    def scoped(self, model: any, include_deleted=False):
        columns = model.__table__.columns.keys()
        query = self.db.query(model)
        if "empresa_id" in columns and self.empresa_id:
            query = query.filter(model.empresa_id == self.empresa_id)
        if "restaurante_id" in columns and self.restaurante_id:
            query = query.filter(model.restaurante_id == self.restaurante_id)
        if "eliminado_en" in columns and not include_deleted:
            query = query.filter(model.eliminado_en.is_(None))
        return query

    # Obtiene un registro propio; si es de otra empresa responde igual que si no existiera
    def get_own(self, model: any, record_id, field: str = "registro", lock=False):
        try:
            record_id = int(record_id)
        except (TypeError, ValueError):
            raise CustomException(f"El campo {field} no es válido.")

        query = self.scoped(model).filter(model.id == record_id)
        if lock:
            query = query.with_for_update()
        record = query.first()

        if not record:
            raise CustomException(f"El {field} no existe.", 404)
        return record

    # Inserting data. Con commit=False solo se agrega a la transacción en curso
    def insert_data(self, model: any, data: dict, commit=True):

        try:
            model_data = model(self._with_tenant(model, data))
            self.db.add(model_data)
            if commit:
                self.db.commit()
            else:
                self.db.flush()
            return model_data.id
        except Exception as ex:
            self.db.rollback()
            print(str(ex))
            raise CustomException(str(ex))

    # Updating data of an own record
    def update_data(self, model: any, record_id, data: dict, field: str = "registro", commit=True):

        record = self.get_own(model, record_id, field)
        columns = model.__table__.columns.keys()
        for key, value in data.items():
            if key in columns and key not in ["id", "empresa_id", "restaurante_id"]:
                setattr(record, key, value)
        if commit:
            self.db.commit()
        else:
            self.db.flush()
        return record

    # Borrado lógico (RG-11)
    def soft_delete(self, model: any, record_id, field: str = "registro"):
        return self.update_data(model, record_id, {"eliminado_en": now(), "activo": False}, field)

    # Registro de auditoría (RG-14, RG-15). Va en la misma transacción de la acción auditada.
    def audit(self, accion: str, entidad: str, entidad_id=None, antes=None, despues=None,
              motivo=None, commit=True):
        self.insert_data(AuditoriaModel, {
            "empresa_id": self.empresa_id,
            "restaurante_id": self.restaurante_id,
            "usuario_id": self.ctx.get("usuario_id"),
            "accion": accion,
            "entidad": entidad,
            "entidad_id": entidad_id,
            "antes": antes,
            "despues": despues,
            "motivo": motivo,
            "ip": self.ctx.get("ip"),
            "dispositivo": self.ctx.get("dispositivo"),
        }, commit=commit)

    def commit(self):
        self.db.commit()
