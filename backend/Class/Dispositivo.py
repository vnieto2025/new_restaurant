import hashlib
import hmac
import os
import secrets
from datetime import timedelta
from Utils.tools import Tools, CustomException, clean_text, now
from Utils.limiter import limiter
from Utils.contexto import cargar_contexto
from Querys.base import Querys
from Models.dispositivo_model import DispositivoModel, TIPOS_DISPOSITIVO
from Models.usuario_model import UsuarioModel
from Models.zona_model import ZonaModel
from Models.punto_produccion_model import PuntoProduccionModel
from Models.restaurante_model import RestauranteModel
from Class.Auth import Auth

CODIGO_MINUTOS = 15
PIN_INTENTOS = 5
PIN_VENTANA = 300
EMPAREJAR_INTENTOS = 10


def token_hash(token: str):
    return hashlib.sha256(token.encode()).hexdigest()


def pin_hash(empresa_id, pin: str):
    """ Huella del PIN, única por empresa. Es determinística para poder identificar a la persona
        solo con su PIN; la clave del servidor impide calcularla sin acceso al backend. """
    llave = os.getenv("MY_SECRET_KEY", "").encode()
    return hmac.new(llave, f"{empresa_id}:{pin}".encode(), hashlib.sha256).hexdigest()


def validate_pin(pin):
    pin = str(pin or "").strip()
    if not pin.isdigit() or not 4 <= len(pin) <= 6:
        raise CustomException("El PIN debe tener entre 4 y 6 números.")
    if len(set(pin)) == 1 or pin in "0123456789" or pin in "9876543210":
        raise CustomException("Ese PIN es muy fácil de adivinar. Elige otro.")
    return pin


class Dispositivo:
    """ Tablets de zona y pantallas de producción autorizadas, con ingreso por PIN (doc 08, ADR-026) """

    def __init__(self, db, ctx: dict = None):
        self.db = db
        self.ctx = ctx or {}
        self.tools = Tools()
        self.querys = Querys(db, self.ctx)

    def list(self):
        dispositivos = self.querys.scoped(DispositivoModel).order_by(DispositivoModel.id.asc()).all()
        return self.tools.output(200, "Dispositivos.", [self.format(d) for d in dispositivos])

    # El administrador crea el dispositivo y recibe un código para escribir en la tablet
    def create(self, data: dict):

        tipo = data["tipo"]
        if tipo not in TIPOS_DISPOSITIVO:
            raise CustomException("El tipo de dispositivo no es válido.")
        fields = {"nombre": clean_text(data["nombre"]), "tipo": tipo}
        if tipo == "zona":
            fields["zona_id"] = self.querys.get_own(ZonaModel, data.get("zona_id"), "zona").id
        else:
            fields["punto_produccion_id"] = self.querys.get_own(PuntoProduccionModel, data.get("punto_produccion_id"),
                                                                "punto de producción").id
        fields.update(self.new_code())

        dispositivo_id = self.querys.insert_data(DispositivoModel, fields, commit=False)
        self.querys.audit("dispositivo_creado", "dispositivo", dispositivo_id, despues={"nombre": fields["nombre"]})
        dispositivo = self.db.get(DispositivoModel, dispositivo_id)
        return self.tools.output(201, "Dispositivo creado. Escribe el código en la tablet.", self.format(dispositivo, con_codigo=True))

    # Nuevo código para volver a emparejar (por ejemplo, si se cambió la tablet)
    def new_pairing_code(self, data: dict):
        dispositivo = self.querys.get_own(DispositivoModel, data["dispositivo_id"], "dispositivo")
        for key, value in self.new_code().items():
            setattr(dispositivo, key, value)
        dispositivo.activo = True
        self.querys.audit("dispositivo_codigo", "dispositivo", dispositivo.id)
        return self.tools.output(200, "Código generado.", self.format(dispositivo, con_codigo=True))

    # Desautorizar: las sesiones abiertas desde ese dispositivo caen al instante
    def change_status(self, data: dict):
        dispositivo = self.querys.get_own(DispositivoModel, data["dispositivo_id"], "dispositivo")
        activo = data["activo"] is True
        dispositivo.activo = activo
        if not activo:
            dispositivo.token_hash, dispositivo.codigo, dispositivo.codigo_expira = None, None, None
        self.querys.audit("dispositivo_estado", "dispositivo", dispositivo.id, despues={"activo": activo})
        return self.tools.output(200, "Dispositivo activado." if activo else "Dispositivo desautorizado.", self.format(dispositivo))

    # La tablet escribe el código y recibe su secreto (un solo uso)
    def pair(self, data: dict, ip: str = None):

        limiter.check(f"emparejar:{ip}", EMPAREJAR_INTENTOS, PIN_VENTANA, "Demasiados intentos. Espera unos minutos.")
        dispositivo = self.db.query(DispositivoModel).filter(
            DispositivoModel.codigo == str(data["codigo"]).strip(),
            DispositivoModel.codigo_expira > now(),
            DispositivoModel.activo.is_(True),
        ).with_for_update().first()
        if not dispositivo:
            raise CustomException("El código no es válido o ya venció. Pide uno nuevo al administrador.", 404)

        secreto = secrets.token_urlsafe(32)
        dispositivo.token_hash = token_hash(secreto)
        dispositivo.codigo, dispositivo.codigo_expira = None, None
        dispositivo.emparejado_en = now()
        self.db.commit()
        return self.tools.output(200, "Dispositivo autorizado.", {"token": secreto, **self.public_info(dispositivo)})

    def info(self, data: dict):
        dispositivo = self.by_token(data["token"])
        return self.tools.output(200, "Dispositivo autorizado.", self.public_info(dispositivo))

    # Identificarse con PIN en un dispositivo autorizado (RN-USR-03)
    def pin_login(self, data: dict, ip: str = None, user_agent: str = None):

        dispositivo = self.by_token(data["token"])
        key = f"pin:{dispositivo.id}"
        limiter.check(key, PIN_INTENTOS, PIN_VENTANA, "Demasiados PIN incorrectos. Espera unos minutos.")

        usuario = self.db.query(UsuarioModel).filter(
            UsuarioModel.empresa_id == dispositivo.empresa_id,
            UsuarioModel.pin_hash == pin_hash(dispositivo.empresa_id, str(data["pin"]).strip()),
            UsuarioModel.activo.is_(True),
            UsuarioModel.eliminado_en.is_(None),
        ).first()

        ctx = None
        if usuario:
            try:
                ctx = cargar_contexto({"usuario_id": usuario.id, "restaurante_id": dispositivo.restaurante_id}, db=self.db)
            except Exception:
                ctx = None
        if not ctx or not self.allowed_on(dispositivo, ctx):
            Querys(self.db, {"empresa_id": dispositivo.empresa_id, "restaurante_id": dispositivo.restaurante_id,
                             "ip": ip, "dispositivo": dispositivo.nombre}).audit(
                "pin_fallido", "dispositivo", dispositivo.id)
            raise CustomException("PIN incorrecto o sin acceso a este dispositivo.")

        limiter.reset(key)
        dispositivo.ultimo_uso = now()
        self.db.commit()
        sesion = Auth(self.db).issue(usuario.id, dispositivo.restaurante_id, ip, user_agent, dispositivo_id=dispositivo.id)
        return self.tools.output(200, f"Hola, {usuario.nombre.split(' ')[0]}.", sesion)

    # Una tablet de zona es para quien atiende esa zona; una pantalla, para quien produce en ese punto
    def allowed_on(self, dispositivo, ctx: dict):
        if dispositivo.tipo == "zona":
            return "ordenes.crear_mesa" in ctx["permisos"] and (ctx["zonas"] is None or dispositivo.zona_id in ctx["zonas"])
        return "cocina.operar" in ctx["permisos"] and (ctx["puntos"] is None or dispositivo.punto_produccion_id in ctx["puntos"])

    def by_token(self, token: str):
        dispositivo = self.db.query(DispositivoModel).filter(
            DispositivoModel.token_hash == token_hash(str(token)), DispositivoModel.activo.is_(True)).first()
        if not dispositivo:
            raise CustomException("Este dispositivo ya no está autorizado. Pide un código nuevo al administrador.", 401)
        return dispositivo

    def new_code(self):
        return {"codigo": f"{secrets.randbelow(1_000_000):06d}",
                "codigo_expira": now() + timedelta(minutes=CODIGO_MINUTOS)}

    def public_info(self, dispositivo):
        restaurante = self.db.get(RestauranteModel, dispositivo.restaurante_id)
        destino = self.db.get(ZonaModel, dispositivo.zona_id) if dispositivo.zona_id else \
            self.db.get(PuntoProduccionModel, dispositivo.punto_produccion_id)
        return {
            "nombre": dispositivo.nombre,
            "tipo": dispositivo.tipo,
            "restaurante": restaurante.nombre,
            "destino": destino.nombre if destino else None,
            "zona_id": dispositivo.zona_id,
            "punto_produccion_id": dispositivo.punto_produccion_id,
        }

    def format(self, dispositivo, con_codigo=False):
        data = {
            "id": dispositivo.id,
            "nombre": dispositivo.nombre,
            "tipo": dispositivo.tipo,
            "zona_id": dispositivo.zona_id,
            "punto_produccion_id": dispositivo.punto_produccion_id,
            "emparejado": dispositivo.token_hash is not None,
            "emparejado_en": dispositivo.emparejado_en,
            "ultimo_uso": dispositivo.ultimo_uso,
            "activo": dispositivo.activo,
            "codigo_pendiente": dispositivo.codigo is not None and dispositivo.codigo_expira and dispositivo.codigo_expira > now(),
        }
        if con_codigo:
            data["codigo"] = dispositivo.codigo
            data["codigo_expira"] = dispositivo.codigo_expira
        return data
