from Utils.tools import Tools, CustomException, clean_text
from Querys.entrega import EntregaQuerys
from Models.zona_envio_model import ZonaEnvioModel
from Models.domiciliario_model import DomiciliarioModel, VINCULOS
from Models.usuario_model import UsuarioModel
from Models.domicilio_web_model import DomicilioWebModel
from Models.qr_acceso_model import QrAccesoModel
from Models.pago_linea_config_model import PagoLineaConfigModel
from Querys.mesa import MesaQuerys
from Querys.qr import QrQuerys
from Class.Caja import validar_monto
from Class.Qr import new_token, qr_url, qr_svg


class Domicilio:
    """ Configuración de domicilios: zonas de envío con tarifa fija y domiciliarios con código (doc 15B) """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = EntregaQuerys(db, ctx)

    # ---- Zonas de envío ----

    def list_zones(self, data: dict):
        zonas = [self.format_zone(z) for z in self.querys.zonas(incluir_inactivas=data.get("todos") is True)]
        return self.tools.output(200, "Zonas de envío." if zonas else "Aún no hay zonas de envío.", zonas)

    def save_zone(self, data: dict):
        fields = {
            "nombre": clean_text(data["nombre"]),
            "barrios": clean_text(data.get("barrios")),
            "tarifa": validar_monto(data.get("tarifa") or 0, "tarifa", permitir_cero=True),
            "pago_domiciliario": validar_monto(data.get("pago_domiciliario") or 0, "pago al domiciliario", permitir_cero=True),
            "pedido_minimo": validar_monto(data.get("pedido_minimo") or 0, "pedido mínimo", permitir_cero=True),
            "orden": int(data.get("orden") or 0),
            "activo": data.get("activo") is not False,
        }
        zona_id = data.get("zona_envio_id")
        if self.querys.nombre_existe(ZonaEnvioModel, "nombre", fields["nombre"], exclude_id=zona_id):
            raise CustomException("Ya existe una zona de envío con ese nombre.")
        if zona_id:
            zona = self.querys.update_data(ZonaEnvioModel, zona_id, fields, "zona de envío")
            return self.tools.output(200, "Zona de envío actualizada. Aplica a los pedidos nuevos.", self.format_zone(zona))
        zona_id = self.querys.insert_data(ZonaEnvioModel, fields)
        return self.tools.output(201, "Zona de envío creada.", self.format_zone(self.db.get(ZonaEnvioModel, zona_id)))

    # ---- Domiciliarios ----

    def list_couriers(self, data: dict):
        result = []
        for d in self.querys.domiciliarios(incluir_inactivos=data.get("todos") is True):
            fila = self.format_courier(d)
            fila["en_camino"] = self.querys.en_camino_de(d.id)
            result.append(fila)
        return self.tools.output(200, "Domiciliarios." if result else "Aún no hay domiciliarios.", result)

    def save_courier(self, data: dict):
        vinculo = data.get("vinculo") or "propio"
        if vinculo not in VINCULOS:
            raise CustomException("El vínculo debe ser propio o independiente.")
        codigo = clean_text(data["codigo"]).upper()
        fields = {
            "nombre": clean_text(data["nombre"]), "codigo": codigo, "documento": clean_text(data.get("documento")),
            "telefono": clean_text(data.get("telefono")), "vinculo": vinculo,
            "usuario_id": self.check_user(data.get("usuario_id")),
        }
        domiciliario_id = data.get("domiciliario_id")
        if self.querys.nombre_existe(DomiciliarioModel, "codigo", codigo, exclude_id=domiciliario_id):
            raise CustomException(f"El código {codigo} ya lo tiene otro domiciliario.")
        if fields["usuario_id"]:
            otro = self.querys.domiciliario_de_usuario(fields["usuario_id"])
            if otro and otro.id != (int(domiciliario_id) if domiciliario_id else None):
                raise CustomException(f"Ese usuario ya está ligado a {otro.nombre}.")
        if domiciliario_id:
            domiciliario = self.querys.update_data(DomiciliarioModel, domiciliario_id, fields, "domiciliario")
            return self.tools.output(200, "Domiciliario actualizado.", self.format_courier(domiciliario))
        nuevo_id = self.querys.insert_data(DomiciliarioModel, fields)
        return self.tools.output(201, "Domiciliario creado.", self.format_courier(self.db.get(DomiciliarioModel, nuevo_id)))

    # No se desactiva con entregas en camino (RN-DOM-02)
    def change_courier_status(self, data: dict):
        domiciliario = self.querys.get_own(DomiciliarioModel, data["domiciliario_id"], "domiciliario")
        activo = data["activo"] is True
        if not activo and self.querys.en_camino_de(domiciliario.id):
            raise CustomException(f"{domiciliario.nombre} tiene entregas en camino. Ciérralas antes de desactivarlo.", 409)
        self.querys.update_data(DomiciliarioModel, domiciliario.id, {"activo": activo}, "domiciliario")
        return self.tools.output(200, "Domiciliario activado." if activo else "Domiciliario desactivado.")

    # ---- Pedidos por la web (doc 17A, sección 2.6) ----

    def get_web(self):
        """ Enlace y QR de domicilios con su configuración. El enlace se crea la primera vez que se pide. """
        config = self.web_config()
        qr = self.web_qr()
        self.db.commit()
        return self.tools.output(200, "Pedidos por la web.", self.format_web(config, qr))

    def save_web(self, data: dict):
        config = self.web_config()
        if data["activo"] is True and not self.querys.zonas():
            raise CustomException("Crea al menos una zona de envío activa antes de recibir pedidos por la web.", 409)
        antes = {"activo": config.activo, "aprobacion": config.aprobacion}
        config.activo, config.aprobacion = data["activo"] is True, data.get("aprobacion") is not False
        config.mensaje = clean_text(data.get("mensaje"))
        self.querys.audit("domicilio_web_configurado", "domicilio_web", config.id, antes=antes,
                          despues={"activo": config.activo, "aprobacion": config.aprobacion}, commit=False)
        qr = self.web_qr()
        self.db.commit()
        mensaje = "Pedidos por la web activos." if config.activo else "Pedidos por la web pausados: el enlace muestra que no se reciben."
        return self.tools.output(200, mensaje, self.format_web(config, qr))

    def regenerate_web(self):
        """ Un enlace nuevo: el anterior deja de funcionar al instante (por ejemplo, si lo están usando para spam) """
        qr_querys = QrQuerys(self.db, self.ctx)
        mesa = self.external_table()
        anterior = qr_querys.get_active_by_mesa(mesa.id, "domicilio")
        qr_querys.revoke_by_mesa(mesa.id, "domicilio")
        qr = self.web_qr()
        self.querys.audit("qr_regenerado", "mesa", mesa.id, antes={"qr_id": anterior.id if anterior else None},
                          despues={"qr_id": qr.id, "tipo": "domicilio"}, commit=False)
        self.db.commit()
        return self.tools.output(200, "Enlace nuevo listo. El anterior ya no funciona: cambia el que publicaste.",
                                 self.format_web(self.web_config(), qr))

    def web_config(self):
        config = self.querys.scoped(DomicilioWebModel).first()
        if not config:
            self.querys.insert_data(DomicilioWebModel, {"activo": False, "aprobacion": True}, commit=False)
            config = self.querys.scoped(DomicilioWebModel).first()
        return config

    def web_qr(self):
        mesa = self.external_table()
        qr_querys = QrQuerys(self.db, self.ctx)
        qr = qr_querys.get_active_by_mesa(mesa.id, "domicilio")
        if not qr:
            self.querys.insert_data(QrAccesoModel, {"tipo": "domicilio", "zona_id": mesa.zona_id, "mesa_id": mesa.id,
                                                    "token": new_token()}, commit=False)
            qr = qr_querys.get_active_by_mesa(mesa.id, "domicilio")
        return qr

    def external_table(self):
        mesa = MesaQuerys(self.db, self.ctx).get_mesa_externa()
        if not mesa:
            raise CustomException("El restaurante no tiene mesa externa para recibir pedidos.", 409)
        return mesa

    def format_web(self, config, qr):
        url = qr_url(qr.token)
        pagos = self.querys.scoped(PagoLineaConfigModel).first()
        return {"activo": config.activo, "aprobacion": config.aprobacion, "mensaje": config.mensaje, "url": url,
                "svg": qr_svg(url), "zonas": len(self.querys.zonas()), "restaurante": QrQuerys(self.db, self.ctx).get_restaurante_nombre(),
                "pago_en_linea": "pagos_linea" in self.ctx.get("modulos", set()) and bool(pagos and pagos.activo)}

    # ---- Apoyo ----

    def check_user(self, usuario_id):
        if not usuario_id:
            return None
        from Models.usuario_restaurante_model import UsuarioRestauranteModel
        usuario = self.db.get(UsuarioModel, int(usuario_id))
        enlace = self.db.query(UsuarioRestauranteModel).filter(
            UsuarioRestauranteModel.usuario_id == int(usuario_id),
            UsuarioRestauranteModel.restaurante_id == self.ctx["restaurante_id"]).first() if usuario else None
        if not usuario or usuario.empresa_id != self.ctx["empresa_id"] or not enlace:
            raise CustomException("El usuario no existe en este restaurante.", 404)
        return usuario.id

    def format_zone(self, zona):
        return {"id": zona.id, "nombre": zona.nombre, "barrios": zona.barrios, "tarifa": zona.tarifa,
                "pago_domiciliario": zona.pago_domiciliario, "pedido_minimo": zona.pedido_minimo,
                "orden": zona.orden, "activo": zona.activo}

    def format_courier(self, domiciliario):
        usuario = self.db.get(UsuarioModel, domiciliario.usuario_id) if domiciliario.usuario_id else None
        return {"id": domiciliario.id, "nombre": domiciliario.nombre, "codigo": domiciliario.codigo,
                "documento": domiciliario.documento, "telefono": domiciliario.telefono, "vinculo": domiciliario.vinculo,
                "usuario_id": domiciliario.usuario_id, "usuario": usuario.usuario if usuario else None,
                "activo": domiciliario.activo}
