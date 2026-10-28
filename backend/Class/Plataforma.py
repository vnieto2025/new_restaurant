from datetime import date
from Utils.tools import Tools, CustomException, clean_text, to_local
from Querys.plataforma import PlataformaQuerys
from Querys.restaurante import RestauranteQuerys
from Models.empresa_model import EmpresaModel, ESTADOS_EMPRESA
from Models.usuario_model import UsuarioModel
from Models.usuario_rol_model import UsuarioRolModel
from Models.contrato_model import ESTADOS_CONTRATO
from Class.Restaurante import bootstrap_restaurant, resolve_modules
from Class.Auth import hash_password, validate_password
from Class.Qr import qr_url
from Class.Suscripcion import Suscripcion
from Models.qr_acceso_model import QrAccesoModel


class Plataforma:
    """ Consola del proveedor del software: alta de empresas, restaurantes y contratos (doc 06).
        En el MVP el alta es manual, la hace el superadministrador. """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = PlataformaQuerys(db, ctx)

    # Alta completa: empresa -> administrador -> primer restaurante con contrato (doc 06, sección 4)
    def create_company(self, data: dict):

        admin = data["admin"]
        usuario = str(admin["usuario"]).strip().lower()
        if self.querys.usuario_exists(usuario):
            raise CustomException("Ya existe un usuario con ese nombre de acceso.")
        validate_password(admin["password"])

        empresa_id = self.querys.insert_data(EmpresaModel, {
            "nombre_comercial": clean_text(data["nombre_comercial"]),
            "razon_social": clean_text(data.get("razon_social")),
            "documento_fiscal": clean_text(data.get("documento_fiscal")),
            "contacto_nombre": clean_text(data.get("contacto_nombre")),
            "contacto_correo": clean_text(data.get("contacto_correo")),
            "contacto_telefono": clean_text(data.get("contacto_telefono")),
            "estado": data.get("estado") or "prueba",
        }, commit=False)

        restaurante_id = bootstrap_restaurant(
            self.db, empresa_id, data["restaurante"], data.get("modulos") or ["pedidos"],
            data.get("estado_contrato") or "prueba",
        )

        admin_id = self.querys.insert_data(UsuarioModel, {
            "empresa_id": empresa_id,
            "usuario": usuario,
            "nombre": clean_text(admin["nombre"]),
            "correo": clean_text(admin.get("correo")),
            "password": hash_password(admin["password"]),
        }, commit=False)
        self.querys.insert_data(UsuarioRolModel, {
            "usuario_id": admin_id, "rol_id": self.querys.get_rol("admin_empresa").id,
        }, commit=False)

        self.querys.audit("empresa_creada", "empresa", empresa_id,
                          despues={"restaurante_id": restaurante_id, "admin": usuario})

        return self.tools.output(201, "Empresa creada.", self.format_company(self.querys.get_empresa(empresa_id)))

    # Otro restaurante de una empresa existente, con su propio contrato (RN-RES-01)
    def create_restaurant(self, data: dict):

        empresa = self.querys.get_empresa(data["empresa_id"])
        restaurante_id = bootstrap_restaurant(
            self.db, empresa.id, data["restaurante"], data.get("modulos") or ["pedidos"],
            data.get("estado_contrato") or "prueba",
        )
        self.querys.audit("restaurante_creado", "restaurante", restaurante_id, despues={"empresa_id": empresa.id})

        restaurante = RestauranteQuerys(self.db).get_restaurante(restaurante_id)
        return self.tools.output(201, "Restaurante creado.", RestauranteQuerys(self.db).format_restaurante(restaurante))

    def list_companies(self, data: dict):
        empresas = [self.format_company(empresa) for empresa in self.querys.list_empresas()]
        msg = "Listado de empresas." if empresas else "No hay empresas creadas."
        return self.tools.output(200, msg, empresas)

    def change_company_status(self, data: dict):

        estado = data["estado"]
        if estado not in ESTADOS_EMPRESA:
            raise CustomException("El estado no es válido.")

        empresa = self.querys.get_empresa(data["empresa_id"])
        antes = empresa.estado
        empresa.estado = estado
        self.db.flush()
        self.querys.audit("empresa_estado", "empresa", empresa.id, antes={"estado": antes},
                          despues={"estado": estado}, motivo=clean_text(data.get("motivo")))
        return self.tools.output(200, "Estado de la empresa actualizado.", self.format_company(empresa))

    # Estado, vigencia y módulos del contrato de un restaurante
    def update_contract(self, data: dict):

        estado = data["estado"]
        if estado not in ESTADOS_CONTRATO:
            raise CustomException("El estado del contrato no es válido.")

        querys = RestauranteQuerys(self.db)
        restaurante = querys.get_restaurante(int(data["restaurante_id"]))
        contrato = querys.get_contrato(restaurante.id)
        antes = {"estado": contrato.estado, "fecha_fin": str(contrato.fecha_fin),
                 "modulos": querys.get_modulos_contrato(contrato.id)}

        modulos = resolve_modules(querys, data.get("modulos") or [])
        contrato.estado = estado
        contrato.fecha_fin = self.tools_date(data.get("fecha_fin"))
        querys.set_modulos_contrato(contrato, modulos)
        # Cobro del servicio (doc 42, sección 6)
        if "mensualidad" in data:
            mensualidad = int(data["mensualidad"]) if data.get("mensualidad") not in (None, "") else None
            if mensualidad is not None and mensualidad < 0:
                raise CustomException("La mensualidad no es válida.")
            contrato.mensualidad = mensualidad
        if "proximo_vencimiento" in data:
            contrato.proximo_vencimiento = self.tools_date(data.get("proximo_vencimiento"))
        if "notas_comerciales" in data:
            contrato.notas_comerciales = clean_text(data.get("notas_comerciales"))

        despues = {"estado": estado, "fecha_fin": str(contrato.fecha_fin), "modulos": [m.codigo for m in modulos],
                   "mensualidad": contrato.mensualidad, "proximo_vencimiento": str(contrato.proximo_vencimiento)}
        self.querys.audit("contrato_actualizado", "contrato", contrato.id, antes=antes, despues=despues)
        return self.tools.output(200, "Contrato actualizado.", querys.format_restaurante(restaurante))

    def list_modules(self):
        modulos = [
            {"codigo": m.codigo, "nombre": m.nombre, "depende_de": m.depende_de, "obligatorio": m.obligatorio}
            for m in RestauranteQuerys(self.db).get_modulos()
        ]
        return self.tools.output(200, "Módulos disponibles.", modulos)

    def tools_date(self, value):
        if not value:
            return None
        try:
            return date.fromisoformat(str(value))
        except ValueError:
            raise CustomException("La fecha de fin no es válida (AAAA-MM-DD).")

    def format_company(self, empresa):
        restaurantes = []
        querys = RestauranteQuerys(self.db)
        for restaurante in self.querys.list_restaurantes(empresa.id):
            data = querys.format_restaurante(restaurante)
            rapido = self.db.query(QrAccesoModel).filter(
                QrAccesoModel.restaurante_id == restaurante.id,
                QrAccesoModel.tipo == "rapido",
                QrAccesoModel.activo.is_(True),
            ).first()
            data["url_para_llevar"] = qr_url(rapido.token) if rapido else None
            contrato = querys.get_contrato(restaurante.id)
            if contrato:
                data["contrato"].update({"mensualidad": contrato.mensualidad, "proximo_vencimiento": contrato.proximo_vencimiento,
                                         "notas_comerciales": contrato.notas_comerciales})
                data["suscripcion"] = Suscripcion(self.db, self.ctx).account(restaurante, contrato)
            restaurantes.append(data)
        return {
            "id": empresa.id,
            "nombre_comercial": empresa.nombre_comercial,
            "razon_social": empresa.razon_social,
            "documento_fiscal": empresa.documento_fiscal,
            "contacto_nombre": empresa.contacto_nombre,
            "contacto_correo": empresa.contacto_correo,
            "contacto_telefono": empresa.contacto_telefono,
            "estado": empresa.estado,
            "creado_en": to_local(empresa.creado_en),
            "restaurantes": restaurantes,
        }
