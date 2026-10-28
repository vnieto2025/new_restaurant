from Utils.tools import Tools, CustomException, clean_text
from Querys.entrega import EntregaQuerys
from Models.zona_envio_model import ZonaEnvioModel
from Models.domiciliario_model import DomiciliarioModel, VINCULOS
from Models.usuario_model import UsuarioModel
from Class.Caja import validar_monto


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
