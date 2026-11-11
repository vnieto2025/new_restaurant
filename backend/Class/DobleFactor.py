from werkzeug.security import check_password_hash
from Utils.tools import Tools, CustomException, now
from Utils.cifrado import cifrar, descifrar
from Utils.limiter import limiter
from Utils import totp
from Class.Qr import qr_svg
from Querys.base import Querys
from Models.usuario_model import UsuarioModel
from Models.empresa_model import EmpresaModel

# Roles que administran: a ellos se les recomienda y se les puede exigir (ADR-054)
ROLES_ADMIN = {"superadmin", "admin_empresa", "admin_restaurante"}
EMISOR = "RestaurantERP"
# Intentos de código por usuario antes de esperar
INTENTOS, VENTANA = 5, 300


def es_admin(roles) -> bool:
    return bool(ROLES_ADMIN & {getattr(r, "codigo", r) for r in roles})


def exigido(db, usuario, roles) -> bool:
    empresa = db.get(EmpresaModel, usuario.empresa_id) if usuario.empresa_id else None
    return bool(empresa and empresa.exigir_2fa and es_admin(roles))


def secreto_de(usuario):
    return descifrar(usuario.totp_secreto)["s"] if usuario.totp_secreto else None


def comprobar(db, usuario, valor) -> str:
    """ Valida un código de la aplicación o uno de respaldo (que se gasta). Devuelve cuál fue, o lanza error.
        Los intentos se cuentan por usuario: quien sabe la clave no puede probar códigos sin límite. """
    llave = f"2fa:{usuario.id}"
    limiter.check(llave, INTENTOS, VENTANA, "Demasiados códigos incorrectos. Espera unos minutos e inténtalo de nuevo.")
    paso = totp.verificar(secreto_de(usuario), valor, usuario.totp_ultimo_paso)
    if paso is not None:
        usuario.totp_ultimo_paso = paso
        limiter.reset(llave)
        return "aplicacion"
    huella = totp.huella_respaldo(valor)
    restantes = list(usuario.codigos_respaldo or [])
    if len(totp.normalizar_respaldo(valor)) == 8 and huella in restantes:
        restantes.remove(huella)
        usuario.codigos_respaldo = restantes
        limiter.reset(llave)
        return "respaldo"
    raise CustomException("El código no es correcto. Revisa que sea el que muestra ahora la aplicación.")


class DobleFactor:
    """ Verificación en dos pasos con una aplicación autenticadora (ADR-054): activarla, desactivarla,
        quitársela a otra persona que perdió el celular y exigirla a los administradores de la empresa. """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = Querys(db, ctx)

    def usuario(self, usuario_id=None):
        return self.db.query(UsuarioModel).filter(UsuarioModel.id == (usuario_id or self.ctx["usuario_id"])).with_for_update().one()

    def roles(self, usuario_id):
        from Utils.contexto import roles_de_usuario
        return roles_de_usuario(self.db, usuario_id)

    def clave(self, usuario, password):
        if not check_password_hash(usuario.password, str(password or "")):
            raise CustomException("La clave no es correcta.")

    def status(self, data: dict = None):
        usuario = self.db.get(UsuarioModel, self.ctx["usuario_id"])
        roles = self.roles(usuario.id)
        return self.tools.output(200, "Verificación en dos pasos.", {
            "activo": usuario.totp_activo_en is not None,
            "activo_en": usuario.totp_activo_en,
            "codigos_restantes": len(usuario.codigos_respaldo or []) if usuario.totp_activo_en else 0,
            "exigido": exigido(self.db, usuario, roles),
            "recomendado": es_admin(roles),
        })

    def start(self, data: dict):
        """ Paso 1: un secreto nuevo, todavía sin activar, y el QR para escanearlo """
        usuario = self.usuario()
        self.clave(usuario, data.get("password"))
        if usuario.totp_activo_en:
            raise CustomException("Ya tienes la verificación en dos pasos activa.", 409)
        secreto = totp.nuevo_secreto()
        usuario.totp_secreto = cifrar({"s": secreto})
        usuario.totp_ultimo_paso = None
        self.db.commit()
        enlace = totp.uri(secreto, usuario.usuario, EMISOR)
        return self.tools.output(200, "Escanea el código con la aplicación.", {
            "secreto": " ".join(secreto[i:i + 4] for i in range(0, len(secreto), 4)),
            "uri": enlace,
            "qr_svg": qr_svg(enlace, scale=5),
        })

    def activate(self, data: dict):
        """ Paso 2: con el primer código correcto queda activa y se entregan los códigos de respaldo, una sola vez """
        usuario = self.usuario()
        if usuario.totp_activo_en:
            raise CustomException("Ya tienes la verificación en dos pasos activa.", 409)
        if not usuario.totp_secreto:
            raise CustomException("Primero escanea el código QR.", 409)
        paso = totp.verificar(secreto_de(usuario), data["codigo"])
        if paso is None:
            raise CustomException("El código no es correcto. Revisa que el celular tenga la hora bien puesta.")
        respaldo = totp.codigos_respaldo()
        usuario.totp_activo_en, usuario.totp_ultimo_paso = now(), paso
        usuario.codigos_respaldo = [totp.huella_respaldo(c) for c in respaldo]
        self.querys.audit("2fa_activada", "usuario", usuario.id, commit=False)
        self.db.commit()
        return self.tools.output(200, "Verificación en dos pasos activa.", {
            "codigos_respaldo": [f"{c[:4]}-{c[4:]}" for c in respaldo]})

    def disable(self, data: dict):
        usuario = self.usuario()
        if not usuario.totp_activo_en:
            raise CustomException("No tienes la verificación en dos pasos activa.", 409)
        if exigido(self.db, usuario, self.roles(usuario.id)):
            raise CustomException("Tu empresa exige la verificación en dos pasos a los administradores.", 409)
        self.clave(usuario, data.get("password"))
        comprobar(self.db, usuario, data.get("codigo"))
        self.clear(usuario)
        self.querys.audit("2fa_desactivada", "usuario", usuario.id, commit=False)
        self.db.commit()
        return self.tools.output(200, "Verificación en dos pasos desactivada.")

    def new_backup_codes(self, data: dict):
        usuario = self.usuario()
        if not usuario.totp_activo_en:
            raise CustomException("No tienes la verificación en dos pasos activa.", 409)
        comprobar(self.db, usuario, data.get("codigo"))
        respaldo = totp.codigos_respaldo()
        usuario.codigos_respaldo = [totp.huella_respaldo(c) for c in respaldo]
        self.querys.audit("2fa_codigos_nuevos", "usuario", usuario.id, commit=False)
        self.db.commit()
        return self.tools.output(200, "Códigos de respaldo nuevos: los anteriores ya no sirven.", {
            "codigos_respaldo": [f"{c[:4]}-{c[4:]}" for c in respaldo]})

    def reset_user(self, data: dict):
        """ Otra persona perdió el celular y sus códigos: se le quita para que la vuelva a activar """
        objetivo = self.db.query(UsuarioModel).filter(UsuarioModel.id == int(data["usuario_id"]),
                                                      UsuarioModel.empresa_id == self.ctx["empresa_id"]).with_for_update().first()
        if not objetivo:
            raise CustomException("El usuario no existe.", 404)
        if objetivo.id == self.ctx["usuario_id"]:
            raise CustomException("La tuya se desactiva desde Mi cuenta, con tu código.")
        if "admin_empresa" in {r.codigo for r in self.roles(objetivo.id)} and "admin_empresa" not in self.ctx.get("roles", []):
            raise CustomException("Solo un administrador de la empresa se la quita a otro administrador de la empresa.", 403)
        if not objetivo.totp_activo_en:
            raise CustomException("Ese usuario no tiene la verificación en dos pasos activa.", 409)
        self.clear(objetivo)
        self.querys.audit("2fa_quitada", "usuario", objetivo.id, motivo="Perdió el acceso a su aplicación", commit=False)
        self.db.commit()
        return self.tools.output(200, f"Se le quitó la verificación en dos pasos a {objetivo.nombre}. Debe activarla de nuevo.")

    def require(self, data: dict):
        if "admin_empresa" not in self.ctx.get("roles", []):
            raise CustomException("Solo el administrador de la empresa decide esto.", 403)
        empresa = self.db.query(EmpresaModel).filter(EmpresaModel.id == self.ctx["empresa_id"]).with_for_update().one()
        empresa.exigir_2fa = data["exigir"] is True
        self.querys.audit("2fa_exigida" if empresa.exigir_2fa else "2fa_no_exigida", "empresa", empresa.id, commit=False)
        self.db.commit()
        return self.tools.output(200, "Los administradores deberán activar la verificación en dos pasos." if empresa.exigir_2fa
                                 else "La verificación en dos pasos ya no es obligatoria.", {"exigir": empresa.exigir_2fa})

    def clear(self, usuario):
        usuario.totp_secreto = usuario.totp_activo_en = usuario.totp_ultimo_paso = usuario.codigos_respaldo = None
