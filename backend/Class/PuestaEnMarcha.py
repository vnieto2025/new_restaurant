from Utils.tools import Tools, CustomException, now
from Querys.base import Querys
from Querys.facturacion import FacturacionQuerys
from Models.restaurante_model import RestauranteModel
from Models.horario_model import HorarioModel
from Models.mesa_model import MesaModel
from Models.producto_model import ProductoModel
from Models.punto_produccion_model import PuntoProduccionModel
from Models.dispositivo_model import DispositivoModel
from Models.usuario_model import UsuarioModel
from Models.usuario_restaurante_model import UsuarioRestauranteModel
from Models.zona_envio_model import ZonaEnvioModel

# Lo que no se puede deducir de los datos lo confirma una persona
MANUALES = ["qr", "ensayo"]


class PuestaEnMarcha:
    """ Asistente de configuración inicial (doc 41, sección 2): lo que le falta al restaurante para abrir.
        Casi todo se deduce de los datos, así que lo hecho por cualquier camino cuenta y no hay dos verdades.
        Termina con el ensayo en vacío, sin el cual ningún restaurante entra en producción (RN-ONB-01). """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = Querys(db, ctx)
        self.restaurante = db.get(RestauranteModel, ctx["restaurante_id"])

    def get(self):
        return self.tools.output(200, "Puesta en marcha.", self.state())

    def mark(self, data: dict):
        paso, hecho = data["paso"], data["hecho"] is True
        if paso not in MANUALES:
            raise CustomException("Ese paso se completa solo al hacerlo.")
        marcas = dict(self.restaurante.puesta_en_marcha or {})
        if hecho and paso == "ensayo":
            faltan = [p["titulo"] for p in self.steps() if p["obligatorio"] and not p["hecho"] and p["clave"] != "ensayo"]
            if faltan:
                raise CustomException(f"Antes del ensayo falta: {', '.join(faltan)}.", 409)
        if hecho:
            marcas[paso] = {"en": now().isoformat(), "por": self.ctx.get("nombre")}
        else:
            marcas.pop(paso, None)
        # Se reasigna: SQLAlchemy no detecta cambios dentro del JSON
        self.restaurante.puesta_en_marcha = marcas
        self.querys.audit("puesta_en_marcha", "restaurante", self.restaurante.id, despues={"paso": paso, "hecho": hecho})
        return self.tools.output(200, "Paso confirmado." if hecho else "Paso reabierto.", self.state())

    def state(self):
        pasos = self.steps()
        obligatorios = [p for p in pasos if p["obligatorio"]]
        return {
            "pasos": pasos,
            "total": len(obligatorios),
            "hechos": sum(1 for p in obligatorios if p["hecho"]),
            "listo": "ensayo" in (self.restaurante.puesta_en_marcha or {}),
        }

    def count(self, model, *filtros):
        return self.querys.scoped(model).filter(*filtros).count()

    def steps(self):
        modulos = self.ctx.get("modulos", set())
        con_pedidos = "pedidos" in modulos
        marcas = self.restaurante.puesta_en_marcha or {}
        otros = self.querys.scoped(UsuarioRestauranteModel).join(UsuarioModel, UsuarioModel.id == UsuarioRestauranteModel.usuario_id).filter(
            UsuarioModel.activo.is_(True), UsuarioModel.eliminado_en.is_(None), UsuarioModel.id != self.ctx["usuario_id"]).count()

        pasos = [{
            "clave": "datos", "titulo": "Datos del restaurante", "ruta": "admin-restaurante", "obligatorio": True,
            "descripcion": "Dirección y teléfono, propina sugerida y aviso de tratamiento de datos.",
            "hecho": bool(self.restaurante.direccion and self.restaurante.telefono),
        }, {
            "clave": "horario", "titulo": "Horario de atención", "ruta": "admin-restaurante", "obligatorio": False,
            "descripcion": "Sin horario se reciben órdenes a toda hora.",
            "hecho": self.count(HorarioModel) > 0,
        }]
        if "facturacion" in modulos:
            pasos.append({
                "clave": "impuestos", "titulo": "Impuestos", "ruta": "admin-impuestos", "obligatorio": True,
                "descripcion": "Elige el impuesto por defecto de tus productos. Revísalo con tu contador.",
                "hecho": FacturacionQuerys(self.db, self.ctx).impuesto_defecto() is not None,
            })
        if con_pedidos:
            pasos += [{
                "clave": "cocina", "titulo": "Cocina y bar", "ruta": "admin-puntos", "obligatorio": True,
                "descripcion": "Dónde se prepara cada cosa. Ya tienes una Cocina; agrega un Bar si lo necesitas.",
                "hecho": self.count(PuntoProduccionModel) > 0,
            }, {
                "clave": "mesas", "titulo": "Zonas y mesas", "ruta": "admin-mesas", "obligatorio": True, "accion": "mesas",
                "descripcion": "Crea tus mesas de una sola vez, por zona.",
                "hecho": self.count(MesaModel, MesaModel.tipo != "externa") > 0,
            }]
        pasos += [{
            "clave": "carta", "titulo": "Carta", "ruta": "admin-productos", "obligatorio": True, "accion": "importar",
            "descripcion": "Carga tus productos desde una hoja de cálculo o uno por uno.",
            "hecho": self.count(ProductoModel, ProductoModel.activo.is_(True)) > 0,
        }, {
            "clave": "personal", "titulo": "Personal", "ruta": "admin-usuarios", "obligatorio": con_pedidos,
            "descripcion": "Un usuario por persona, con su rol. Los meseros también con su PIN.",
            "hecho": otros > 0,
        }]
        if con_pedidos:
            pasos.append({
                "clave": "dispositivos", "titulo": "Tablets y pantallas", "ruta": "admin-dispositivos", "obligatorio": False,
                "descripcion": "Autoriza las tablets de zona y la pantalla de cocina. También se puede entrar con usuario y clave.",
                "hecho": self.count(DispositivoModel, DispositivoModel.token_hash.isnot(None)) > 0,
            })
        if "domicilios" in modulos:
            pasos.append({
                "clave": "domicilios", "titulo": "Domicilios", "ruta": "admin-domicilios", "obligatorio": True,
                "descripcion": "Zonas de envío con su tarifa y las personas que llevan los pedidos.",
                "hecho": self.count(ZonaEnvioModel, ZonaEnvioModel.activo.is_(True)) > 0,
            })
        if con_pedidos:
            pasos.append({
                "clave": "qr", "titulo": "Códigos QR", "ruta": "admin-qr", "obligatorio": True, "manual": True,
                "descripcion": "Imprímelos y ponlos en un lugar visible de cada mesa.",
                "boton": "Ya los imprimí", "hecho": "qr" in marcas, "marca": marcas.get("qr"),
            })
        pasos.append({
            "clave": "ensayo", "titulo": "Ensayo en vacío", "obligatorio": True, "manual": True,
            "descripcion": "Simula una jornada sin clientes para encontrar errores antes de abrir.",
            "boton": "Ya hicimos el ensayo", "hecho": "ensayo" in marcas, "marca": marcas.get("ensayo"),
        })
        return pasos
