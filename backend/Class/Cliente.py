from Utils.tools import Tools, CustomException, clean_text, now, jornada
from Utils.telefono import normalizar_telefono
from Querys.cliente import ClienteQuerys
from Models.cliente_model import ClienteModel, ESTADOS_CLIENTE
from Models.cliente_direccion_model import ClienteDireccionModel
from Models.restaurante_model import RestauranteModel

TIPOS_DOCUMENTO = ["CC", "CE", "NIT", "PAS", "PPT", "TI"]
CANALES_CONSENTIMIENTO = ["mostrador", "telefono", "whatsapp", "carta", "domicilio_web", "registro"]
MAX_DIRECCIONES = 5


class Cliente:
    """ Clientes registrados de la empresa (doc 25) con su tratamiento de datos (doc 32A) """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = ClienteQuerys(db, ctx)

    # Búsqueda rápida para autocompletar en mostrador y domicilios (doc 25, sección 3)
    def search(self, data: dict):
        texto = clean_text(data.get("texto")) or ""
        if len(texto) < 3:
            return self.tools.output(200, "Escribe al menos 3 caracteres.", [])
        clientes = [self.querys.format_cliente(c) for c in self.querys.search(texto)]
        return self.tools.output(200, "Clientes encontrados." if clientes else "No hay coincidencias.", clientes)

    def list(self, data: dict):
        limite = min(int(data.get("limite") or 50), 200)
        pagina = max(int(data.get("pagina") or 1), 1)
        if clean_text(data.get("buscar")):
            filas, total = self.querys.search(data["buscar"], limite), None
        else:
            filas, total = self.querys.list_clientes(limite, (pagina - 1) * limite)
        return self.tools.output(200, "Clientes.", {
            "clientes": [self.querys.format_cliente(c, con_direcciones=False) for c in filas],
            "total": total,
        })

    # Ficha con historial. Toda consulta de datos personales queda registrada (RN-CLI-06)
    def get(self, data: dict):
        cliente = self.querys.get_own(ClienteModel, data["cliente_id"], "cliente")
        ordenes = self.querys.ordenes(cliente.id, limite=10)
        self.querys.audit("cliente_consultado", "cliente", cliente.id)
        cupones = None
        if "fidelizacion" in (self.ctx.get("modulos") or set()):
            from Class.Cupon import Cupon
            cupones = Cupon(self.db, self.ctx).client_summary(cliente.id)
        return self.tools.output(200, "Ficha del cliente.", {
            **self.querys.format_cliente(cliente),
            "cupones": cupones,
            "historial": {
                "ordenes": len(self.querys.ordenes(cliente.id)),
                "total_gastado": self.querys.total_gastado(cliente.id),
                "favoritos": self.querys.favoritos(cliente.id),
                "ultimas": [{"numero_texto": f"#{o.numero:03d}", "jornada": o.jornada, "canal": o.canal, "total": o.total}
                            for o in ordenes],
            },
        })

    def create(self, data: dict):
        cliente = self.register(data, canal=data.get("canal") or "mostrador")
        self.db.commit()
        return self.tools.output(201, "Cliente registrado.", self.querys.format_cliente(cliente))

    def update(self, data: dict):

        cliente = self.querys.get_own(ClienteModel, data["cliente_id"], "cliente")
        if cliente.anonimizado_en:
            raise CustomException("Este cliente fue anonimizado y no se puede editar.", 409)
        telefono = normalizar_telefono(data.get("telefono"))
        if telefono and telefono != cliente.telefono and self.querys.by_phone(telefono):
            raise CustomException("Ya existe otro cliente con ese teléfono.")

        cliente.nombre = clean_text(data["nombre"])
        cliente.telefono = telefono
        cliente.correo = clean_text(data.get("correo"))
        cliente.tipo_documento, cliente.documento = self.clean_document(data)
        cliente.notas = clean_text(data.get("notas"))
        self.apply_commercial(cliente, data.get("acepta_comercial"), data.get("canal") or "mostrador")
        if isinstance(data.get("acepta_avisos"), bool) and data["acepta_avisos"] != cliente.acepta_avisos:
            cliente.acepta_avisos = data["acepta_avisos"]
            self.querys.audit("avisos_cliente", "cliente", cliente.id, despues={"acepta_avisos": cliente.acepta_avisos}, commit=False)
        self.querys.audit("cliente_actualizado", "cliente", cliente.id)
        return self.tools.output(200, "Cliente actualizado.", self.querys.format_cliente(cliente))

    def change_status(self, data: dict):
        cliente = self.querys.get_own(ClienteModel, data["cliente_id"], "cliente")
        if data["estado"] not in ESTADOS_CLIENTE:
            raise CustomException("El estado no es válido.")
        cliente.estado = data["estado"]
        self.querys.audit("cliente_estado", "cliente", cliente.id, despues={"estado": cliente.estado})
        return self.tools.output(200, "Estado del cliente actualizado.")

    def save_address(self, data: dict):

        cliente = self.querys.get_own(ClienteModel, data["cliente_id"], "cliente")
        if data.get("direccion_id"):
            direccion = self.querys.get_own(ClienteDireccionModel, data["direccion_id"], "dirección")
            if direccion.cliente_id != cliente.id:
                raise CustomException("La dirección no es de este cliente.", 404)
        else:
            if len(self.querys.direcciones(cliente.id)) >= MAX_DIRECCIONES:
                raise CustomException(f"Un cliente puede guardar máximo {MAX_DIRECCIONES} direcciones.")
            direccion_id = self.querys.insert_data(ClienteDireccionModel, {"cliente_id": cliente.id, "direccion": "-"}, commit=False)
            direccion = self.db.get(ClienteDireccionModel, direccion_id)
        direccion.nombre = clean_text(data.get("nombre"))
        direccion.direccion = clean_text(data["direccion"])
        direccion.indicaciones = clean_text(data.get("indicaciones"))
        direccion.barrio = clean_text(data.get("barrio"))
        self.db.commit()
        return self.tools.output(200, "Dirección guardada.", self.querys.format_cliente(cliente))

    def delete_address(self, data: dict):
        direccion = self.querys.get_own(ClienteDireccionModel, data["direccion_id"], "dirección")
        direccion.activo = False
        self.db.commit()
        cliente = self.db.get(ClienteModel, direccion.cliente_id)
        return self.tools.output(200, "Dirección eliminada.", self.querys.format_cliente(cliente))

    # Derecho de acceso del titular: todo lo que el sistema guarda de esa persona (doc 32A, sección 5)
    def export(self, data: dict):
        cliente = self.querys.get_own(ClienteModel, data["cliente_id"], "cliente")
        self.querys.audit("cliente_exportado", "cliente", cliente.id, motivo=clean_text(data.get("motivo")))
        return self.tools.output(200, "Datos del cliente.", {
            **self.querys.format_cliente(cliente),
            "consentimientos": {
                "datos": {"aceptado_en": cliente.datos_aceptado_en, "canal": cliente.datos_canal, "version_aviso": cliente.datos_version},
                "comercial": {"aceptado_en": cliente.comercial_aceptado_en, "canal": cliente.comercial_canal,
                              "revocado_en": cliente.comercial_revocado_en},
            },
            "ordenes": [{"numero_texto": f"#{o.numero:03d}", "jornada": o.jornada, "canal": o.canal, "total": o.total}
                        for o in self.querys.ordenes(cliente.id)],
        })

    # Supresión: se borran los datos personales y las ventas quedan anónimas (RN-CLI-05)
    def anonymize(self, data: dict):
        cliente = self.querys.get_own(ClienteModel, data["cliente_id"], "cliente")
        if cliente.anonimizado_en:
            raise CustomException("El cliente ya estaba anonimizado.", 409)
        cliente.nombre = "Cliente anonimizado"
        cliente.telefono = cliente.correo = cliente.documento = cliente.tipo_documento = cliente.notas = None
        cliente.anonimizado_en, cliente.estado = now(), "inactivo"
        cliente.comercial_revocado_en = now()
        self.querys.delete_addresses(cliente.id)
        self.querys.anonymize_orders(cliente.id)
        self.querys.audit("cliente_anonimizado", "cliente", cliente.id, motivo=clean_text(data["motivo"]))
        return self.tools.output(200, "Datos personales eliminados. Las ventas se conservan sin ellos.")

    def register(self, data: dict, canal: str):
        """ Crea un cliente. Exige la autorización de tratamiento de datos (RN-PRI-01, RN-PRI-02). """
        if data.get("acepta_datos") is not True:
            raise CustomException("Para registrar al cliente debe aceptar el tratamiento de sus datos.")
        telefono = normalizar_telefono(data.get("telefono"), obligatorio=True)
        if self.querys.by_phone(telefono):
            raise CustomException("Ya existe un cliente con ese teléfono.")
        tipo, documento = self.clean_document(data)
        cliente_id = self.querys.insert_data(ClienteModel, {
            "nombre": clean_text(data["nombre"]),
            "telefono": telefono,
            "correo": clean_text(data.get("correo")),
            "tipo_documento": tipo,
            "documento": documento,
            "notas": clean_text(data.get("notas")),
            "acepta_avisos": data.get("acepta_avisos") is not False,
            "datos_aceptado_en": now(),
            "datos_canal": canal,
            "datos_version": self.aviso_version(),
            "registrado_por": self.ctx.get("usuario_id"),
        }, commit=False)
        cliente = self.db.get(ClienteModel, cliente_id)
        self.apply_commercial(cliente, data.get("acepta_comercial"), canal)
        return cliente

    def for_order(self, nombre, telefono, acepta_datos: bool, canal: str):
        """ Cliente de una orden externa: si ya existe por teléfono se reutiliza; si no, se crea
            solo cuando autorizó el tratamiento de datos. Sin autorización la orden guarda el
            teléfono para gestionarla, pero no se crea ficha (doc 32A). """
        telefono = normalizar_telefono(telefono)
        if not telefono:
            return None
        cliente = self.querys.by_phone(telefono)
        if cliente:
            if cliente.estado == "bloqueado":
                raise CustomException("Este cliente está bloqueado. Habla con el administrador.", 409)
            if cliente.anonimizado_en:
                return None
        elif acepta_datos:
            cliente = self.register({"nombre": nombre or "Cliente", "telefono": telefono, "acepta_datos": True}, canal)
        else:
            return None
        cliente.ultima_compra = jornada(tz_name=self.ctx.get("zona_horaria"), inicio=self.ctx.get("hora_inicio_jornada"))
        return cliente

    def apply_commercial(self, cliente, acepta, canal):
        if acepta is True and (cliente.comercial_aceptado_en is None or cliente.comercial_revocado_en):
            cliente.comercial_aceptado_en, cliente.comercial_canal, cliente.comercial_revocado_en = now(), canal, None
        elif acepta is False and cliente.comercial_aceptado_en and not cliente.comercial_revocado_en:
            cliente.comercial_revocado_en = now()

    def clean_document(self, data: dict):
        tipo, documento = data.get("tipo_documento") or None, clean_text(data.get("documento"))
        if documento and tipo not in TIPOS_DOCUMENTO:
            raise CustomException("Elige el tipo de documento.")
        return (tipo, documento) if documento else (None, None)

    def aviso_version(self):
        restaurante = self.db.get(RestauranteModel, self.ctx.get("restaurante_id")) if self.ctx.get("restaurante_id") else None
        return restaurante.aviso_version if restaurante else None
