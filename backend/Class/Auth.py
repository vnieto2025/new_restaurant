from werkzeug.security import check_password_hash, generate_password_hash
from Utils.tools import Tools, CustomException
from Utils.jwt_manager import create_token
from Utils.limiter import limiter
from Utils.contexto import cargar_contexto, roles_de_usuario, restaurantes_de_usuario
from Querys.auth import AuthQuerys
from Models.dispositivo_model import DispositivoModel
from Class.TurnoMesero import TurnoMesero

MIN_PASSWORD_LENGTH = 8

# Intentos fallidos de ingreso permitidos por usuario e IP antes de bloquear (RN-USR-06)
LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 300


def hash_password(password: str):
    return generate_password_hash(password, method="scrypt", salt_length=16)


def validate_password(password: str):
    if len(password) < MIN_PASSWORD_LENGTH:
        raise CustomException(f"La contraseña debe tener mínimo {MIN_PASSWORD_LENGTH} caracteres.")


class Auth:

    def __init__(self, db, ctx: dict = None):
        self.db = db
        self.ctx = ctx or {}
        self.tools = Tools()
        self.querys = AuthQuerys(db, self.ctx)

    # Function for log to the app
    def login(self, data: dict, ip: str = None, dispositivo: str = None):

        usuario = str(data["usuario"]).strip().lower()
        password = data["password"]
        key = f"login:{usuario}:{ip}"
        limiter.check(key, LOGIN_ATTEMPTS, LOGIN_WINDOW_SECONDS,
                      "Demasiados intentos fallidos. Espere unos minutos e inténtelo de nuevo.")

        user = self.querys.get_usuario_login(usuario)
        if not user or not check_password_hash(user.password, password):
            AuthQuerys(self.db, {
                "empresa_id": user.empresa_id if user else None,
                "ip": ip,
                "dispositivo": (dispositivo or "")[:250],
            }).audit("login_fallido", "usuario", user.id if user else None, despues={"usuario": usuario})
            raise CustomException("Usuario o contraseña incorrectos.")

        limiter.reset(key)

        roles = roles_de_usuario(self.db, user.id)
        restaurante_id = None
        if not any(rol.alcance == "plataforma" for rol in roles):
            restaurantes = restaurantes_de_usuario(self.db, user, roles)
            if not restaurantes:
                raise CustomException("Su usuario no tiene restaurantes asignados.")
            ids = [r.id for r in restaurantes]
            requested = data.get("restaurante_id")
            restaurante_id = int(requested) if requested and int(requested) in ids else ids[0]

        response = self.issue(user.id, restaurante_id, ip, dispositivo)
        self.querys.touch_ultimo_acceso(user.id)
        return self.tools.output(200, "Ingreso exitoso.", response)

    # Datos de la sesión actual (al recargar la página)
    def session(self):
        return self.tools.output(200, "Sesión activa.", self.summary(self.ctx))

    # Cambia el restaurante activo de un usuario con acceso a varios
    def change_restaurant(self, data: dict):
        response = self.issue(self.ctx["usuario_id"], int(data["restaurante_id"]),
                              self.ctx.get("ip"), self.ctx.get("dispositivo"))
        return self.tools.output(200, "Restaurante cambiado.", response)

    # Function for change password
    def change_password(self, data: dict):

        user = self.querys.get_usuario(self.ctx["usuario_id"])
        if not check_password_hash(user.password, data["password_actual"]):
            raise CustomException("La contraseña actual no es correcta.")
        if data["password_actual"] == data["password_nueva"]:
            raise CustomException("La contraseña nueva debe ser distinta a la actual.")

        validate_password(data["password_nueva"])
        self.querys.update_password(user.id, hash_password(data["password_nueva"]))
        self.querys.audit("cambio_password", "usuario", user.id)
        return self.tools.output(200, "Contraseña actualizada.")

    # Crea el token y devuelve el resumen de la sesión que usa la interfaz
    def issue(self, usuario_id, restaurante_id, ip=None, dispositivo=None, dispositivo_id=None):
        token_data = {"usuario_id": usuario_id, "restaurante_id": restaurante_id}
        if dispositivo_id:
            token_data["dispositivo_id"] = dispositivo_id
        try:
            ctx = cargar_contexto(token_data, ip, dispositivo, db=self.db)
        except Exception:
            raise CustomException("No tiene acceso a este restaurante.", 403)
        # Al identificarse, el mesero abre su turno de la jornada (doc 08A)
        if "mesero" in ctx["roles"] and ctx.get("restaurante_id"):
            TurnoMesero(self.db, ctx).ensure_open(dispositivo_id)
        return {"token": create_token(token_data), **self.summary(ctx)}

    def summary(self, ctx: dict):
        user = self.querys.get_usuario(ctx["usuario_id"])
        result = {
            "usuario": {"id": user.id, "usuario": user.usuario, "nombre": user.nombre},
            "roles": ctx["roles"],
            "permisos": sorted(ctx["permisos"]),
            "plataforma": bool(ctx.get("plataforma")),
            "modulos": sorted(ctx.get("modulos", [])),
            "restaurante": None,
            "restaurantes": [],
            "zonas": [],
            "puntos": [],
            "dispositivo": None,
        }
        if ctx.get("plataforma"):
            return result

        roles = roles_de_usuario(self.db, user.id)
        restaurante = self.querys.get_restaurante(ctx["restaurante_id"])
        result.update({
            "restaurante": {
                "id": restaurante.id,
                "nombre": restaurante.nombre,
                "estado": restaurante.estado,
                "zona_horaria": restaurante.zona_horaria,
                "moneda": restaurante.moneda,
                "contrato_estado": ctx.get("contrato_estado"),
            },
            "restaurantes": [
                {"id": r.id, "nombre": r.nombre} for r in restaurantes_de_usuario(self.db, user, roles)
            ],
            # Lo que el usuario puede atender: todas si su rol abarca el restaurante
            "zonas": self.querys.get_zonas(restaurante.id, ctx.get("zonas")),
            "puntos": self.querys.get_puntos(restaurante.id, ctx.get("puntos")),
        })
        if ctx.get("dispositivo_id"):
            dispositivo = self.db.get(DispositivoModel, ctx["dispositivo_id"])
            result["dispositivo"] = {"id": dispositivo.id, "nombre": dispositivo.nombre, "tipo": dispositivo.tipo,
                                     "zona_id": dispositivo.zona_id, "punto_produccion_id": dispositivo.punto_produccion_id}
        return result
