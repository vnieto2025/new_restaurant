from Utils.tools import Tools, CustomException, clean_text
from Querys.usuario import UsuarioQuerys
from Models.usuario_model import UsuarioModel
from Class.Auth import hash_password, validate_password
from Class.Dispositivo import pin_hash, validate_pin


class Usuario:

    def __init__(self, db, ctx: dict):
        self.ctx = ctx
        self.tools = Tools()
        self.querys = UsuarioQuerys(db, ctx)

    def list(self, data: dict):
        usuarios = [self.querys.format_usuario(u) for u in self.querys.list_usuarios(data.get("todos") is True)]
        msg = "Listado de usuarios." if usuarios else "No hay usuarios creados."
        return self.tools.output(200, msg, usuarios)

    def get(self, data: dict):
        usuario = self.querys.get_usuario(data["usuario_id"])
        return self.tools.output(200, "Datos del usuario.", self.querys.format_usuario(usuario))

    # Roles que se pueden asignar desde el restaurante
    def roles(self):
        roles = [{"codigo": r.codigo, "nombre": r.nombre, "alcance": r.alcance} for r in self.allowed_roles()]
        return self.tools.output(200, "Roles disponibles.", roles)

    # Function for create an user (no hay autorregistro de personal, doc 08)
    def create(self, data: dict):

        usuario = str(data["usuario"]).strip().lower()
        if self.querys.usuario_exists(usuario):
            raise CustomException("Ya existe un usuario con ese nombre de acceso.")
        validate_password(data["password"])
        roles, zonas, puntos = self.clean_assignments(data)

        usuario_id = self.querys.insert_data(UsuarioModel, {
            "usuario": usuario,
            "nombre": clean_text(data["nombre"]),
            "documento": clean_text(data.get("documento")),
            "correo": clean_text(data.get("correo")),
            "password": hash_password(data["password"]),
        }, commit=False)
        self.querys.set_asignaciones(usuario_id, roles, zonas, puntos)
        self.querys.audit("usuario_creado", "usuario", usuario_id,
                          despues={"usuario": usuario, "roles": [r.codigo for r in roles], "zonas": zonas, "puntos": puntos})

        usuario = self.querys.get_usuario(usuario_id)
        return self.tools.output(201, "Usuario creado.", self.querys.format_usuario(usuario))

    # Function for update an user, sus roles y asignaciones
    def update(self, data: dict):

        usuario = self.querys.get_usuario(data["usuario_id"])
        antes = self.querys.format_usuario(usuario)
        roles, zonas, puntos = self.clean_assignments(data)

        # Nadie se concede permisos a sí mismo (RN-PER-07)
        if usuario.id == self.ctx["usuario_id"] and sorted(r.codigo for r in roles) != sorted(antes["roles"]):
            raise CustomException("No puede cambiar sus propios roles. Pídaselo a otro administrador.")

        usuario.nombre = clean_text(data["nombre"])
        usuario.documento = clean_text(data.get("documento"))
        usuario.correo = clean_text(data.get("correo"))
        if data.get("password"):
            validate_password(data["password"])
            usuario.password = hash_password(data["password"])

        self.querys.set_asignaciones(usuario.id, roles, zonas, puntos)
        despues = self.querys.format_usuario(usuario)
        self.querys.audit("usuario_actualizado", "usuario", usuario.id,
                          antes=self.audit_view(antes), despues=self.audit_view(despues),
                          motivo="Cambio de contraseña" if data.get("password") else None)

        return self.tools.output(200, "Usuario actualizado.", despues)

    # Function for change status. Desactivar cierra sus sesiones al instante (RN-USR-05)
    def change_status(self, data: dict):

        usuario = self.querys.get_usuario(data["usuario_id"])
        activo = data["activo"] is True

        if not activo and usuario.id == self.ctx["usuario_id"]:
            raise CustomException("No puede desactivar su propio usuario.")
        if not activo and self.querys.count_admins_activos(exclude_id=usuario.id) == 0:
            raise CustomException("Debe quedar al menos un administrador activo en el restaurante.")

        usuario.activo = activo
        self.querys.db.flush()
        self.querys.audit("usuario_estado", "usuario", usuario.id, despues={"activo": activo})

        return self.tools.output(200, "Usuario activado." if activo else "Usuario desactivado.")

    # PIN para identificarse en tablets y pantallas autorizadas; único en la empresa
    def set_pin(self, data: dict):

        usuario = self.querys.get_usuario(data["usuario_id"])
        if data.get("pin") in [None, ""]:
            usuario.pin_hash = None
            self.querys.audit("pin_quitado", "usuario", usuario.id)
            return self.tools.output(200, "PIN quitado.")

        huella = pin_hash(usuario.empresa_id, validate_pin(data["pin"]))
        if self.querys.pin_in_use(usuario.empresa_id, huella, usuario.id):
            raise CustomException("Ese PIN ya lo usa otra persona. Elige otro.")
        usuario.pin_hash = huella
        self.querys.audit("pin_asignado", "usuario", usuario.id)
        return self.tools.output(200, "PIN asignado.")

    def allowed_roles(self):
        roles = self.querys.get_roles()
        # Solo un administrador de empresa crea otros administradores de empresa
        if "admin_empresa" not in self.ctx.get("roles", []):
            roles = [rol for rol in roles if rol.alcance != "empresa"]
        return roles

    def clean_assignments(self, data: dict):

        codigos = data["roles"]
        if not codigos:
            raise CustomException("El usuario debe tener al menos un rol.")
        permitidos = {rol.codigo: rol for rol in self.allowed_roles()}
        no_validos = [codigo for codigo in codigos if codigo not in permitidos]
        if no_validos:
            raise CustomException(f"Roles no válidos: {', '.join(no_validos)}.")
        roles = [permitidos[codigo] for codigo in dict.fromkeys(codigos)]

        zonas = [int(z) for z in data.get("zonas") or []]
        puntos = [int(p) for p in data.get("puntos") or []]
        if set(zonas) - self.querys.valid_zonas(zonas):
            raise CustomException("Alguna de las zonas no existe.")
        if set(puntos) - self.querys.valid_puntos(puntos):
            raise CustomException("Alguno de los puntos de producción no existe.")

        if "mesero" in codigos and not zonas and not any(r.alcance in ["empresa", "restaurante"] for r in roles):
            raise CustomException("Asigne al menos una zona al mesero.")
        if "cocina" in codigos and not puntos and not any(r.alcance in ["empresa", "restaurante"] for r in roles):
            raise CustomException("Asigne al menos un punto de producción al usuario de cocina.")
        return roles, zonas, puntos

    def audit_view(self, data: dict):
        return {key: data[key] for key in ["nombre", "roles", "zonas", "puntos", "activo"]}
