from datetime import timedelta
from Utils.tools import Tools, CustomException, clean_text, now, to_local
from Utils.cifrado import cifrar, descifrar
from Utils.telefono import normalizar_telefono, telefono_legible
from Utils.notificaciones import EVENTOS, VARIABLES, plantilla_valida, evento_activo, plantilla_de, armar
from Utils.proveedores_mensaje import PROVEEDORES, MODOS_SIMULADO, obtener_proveedor, ProveedorNoDisponible
from Querys.base import Querys
from Models.notificacion_config_model import NotificacionConfigModel, MODOS_AVISO
from Models.notificacion_model import NotificacionModel, ESTADOS_AVISO
from Models.orden_model import OrdenModel
from Models.restaurante_model import RestauranteModel
from Models.usuario_model import UsuarioModel

# Reintentos ante una caída del proveedor: después del último, el aviso pasa a manual
ESPERAS_MINUTOS = [1, 5, 15]
ESTADOS_TEXTO = {"pendiente": "En cola", "manual": "Por enviar", "enviada": "Enviada", "fallida": "No se pudo enviar",
                 "omitida": "No se envió", "descartada": "Descartada"}


class Notificacion:
    """ Avisos por WhatsApp a los clientes (doc 31B): configuración, avisos por enviar a mano,
        historial y envío automático por el proveedor. """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = Querys(db, ctx)

    # ---- Configuración ----

    def get_config(self):
        config = self.config()
        return self.tools.output(200, "Configuración de avisos.", self.format_config(config))

    def save_config(self, data: dict):
        modo = data.get("modo") or "manual"
        if modo not in MODOS_AVISO:
            raise CustomException("El modo debe ser manual o automático.")
        proveedor = data.get("proveedor") or "simulado"
        if proveedor not in PROVEEDORES:
            raise CustomException("El proveedor de WhatsApp no está disponible.")
        eventos, plantillas = {}, {}
        for codigo, valor in (data.get("eventos") or {}).items():
            if codigo not in EVENTOS:
                raise CustomException(f"El aviso {codigo} no existe.")
            eventos[codigo] = valor is True
        for codigo, texto in (data.get("plantillas") or {}).items():
            if codigo not in EVENTOS:
                raise CustomException(f"El aviso {codigo} no existe.")
            texto = clean_text(texto)
            if not texto or texto == EVENTOS[codigo]["plantilla"]:
                continue
            if len(texto) > 500 or not plantilla_valida(texto):
                raise CustomException(f"El texto de «{EVENTOS[codigo]['nombre']}» solo puede usar "
                                      + ", ".join("{" + v + "}" for v in VARIABLES) + ".")
            plantillas[codigo] = texto
        limite = int(data.get("limite_diario") or 5)
        if limite < 1 or limite > 50:
            raise CustomException("El límite diario debe estar entre 1 y 50 avisos por teléfono.")

        config = self.config(lock=True)
        if not config:
            self.querys.insert_data(NotificacionConfigModel, {}, commit=False)
            config = self.config(lock=True)
        credenciales = data.get("credenciales")
        if isinstance(credenciales, dict) and any(v not in (None, "") for v in credenciales.values()):
            if proveedor == "simulado" and credenciales.get("modo") not in MODOS_SIMULADO:
                raise CustomException("El modo del proveedor simulado no es válido.")
            config.credenciales = cifrar({k: clean_text(str(v)) for k, v in credenciales.items() if v not in (None, "")})
        if modo == "automatico" and not config.credenciales:
            raise CustomException("Para enviar automáticamente configura primero las credenciales del proveedor.")
        antes = {"modo": config.modo, "proveedor": config.proveedor}
        config.modo, config.proveedor = modo, proveedor
        config.numero_remitente = normalizar_telefono(data.get("numero_remitente")) if data.get("numero_remitente") else None
        config.eventos, config.plantillas, config.limite_diario = eventos, plantillas, limite
        self.querys.audit("avisos_configurados", "notificacion_config", config.id, antes=antes,
                          despues={"modo": modo, "proveedor": proveedor, "eventos": eventos}, commit=False)
        self.db.commit()
        return self.tools.output(200, "Avisos guardados.", self.format_config(config))

    # ---- Operación ----

    def pending(self, data: dict = None):
        """ Lo que alguien debe enviar a mano: avisos en modo manual y los automáticos que fallaron
            (una falla se muestra al encargado para que avise él, doc 31B sección 5) """
        desde = now() - timedelta(hours=12)
        filas = self.querys.scoped(NotificacionModel).filter(
            NotificacionModel.estado.in_(["manual", "fallida"]), NotificacionModel.creado_en >= desde).order_by(
            NotificacionModel.id.asc()).all()
        return self.tools.output(200, "Avisos por enviar." if filas else "No hay avisos por enviar.",
                                 [self.format(f) for f in filas])

    def mark_sent(self, data: dict):
        aviso = self.querys.get_own(NotificacionModel, data["notificacion_id"], "aviso", lock=True)
        if aviso.estado not in ("manual", "fallida"):
            raise CustomException("Ese aviso ya no está por enviar.", 409)
        aviso.estado, aviso.enviada_en, aviso.enviada_por = "enviada", now(), self.ctx.get("usuario_id")
        aviso.modo = "manual"
        self.db.commit()
        return self.tools.output(200, "Aviso marcado como enviado.", self.format(aviso))

    def discard(self, data: dict):
        aviso = self.querys.get_own(NotificacionModel, data["notificacion_id"], "aviso", lock=True)
        if aviso.estado not in ("manual", "fallida", "pendiente"):
            raise CustomException("Ese aviso ya no está por enviar.", 409)
        aviso.estado, aviso.enviada_por = "descartada", self.ctx.get("usuario_id")
        self.db.commit()
        return self.tools.output(200, "Aviso descartado.", self.format(aviso))

    def retry(self, data: dict):
        aviso = self.querys.get_own(NotificacionModel, data["notificacion_id"], "aviso", lock=True)
        config = self.config()
        if aviso.estado != "fallida" or not config or config.modo != "automatico":
            raise CustomException("Solo se reintenta un aviso automático que falló.", 409)
        aviso.estado, aviso.intentos, aviso.proximo_intento_en, aviso.error = "pendiente", 0, None, None
        self.db.commit()
        from Utils.mensajeria import cola_mensajes
        cola_mensajes.despertar()
        return self.tools.output(200, "Aviso de nuevo en la cola.", self.format(aviso))

    def list(self, data: dict):
        query = self.querys.scoped(NotificacionModel)
        if data.get("estado"):
            if data["estado"] not in ESTADOS_AVISO:
                raise CustomException("El estado no es válido.")
            query = query.filter(NotificacionModel.estado == data["estado"])
        if data.get("evento"):
            query = query.filter(NotificacionModel.evento == data["evento"])
        filas = query.order_by(NotificacionModel.id.desc()).limit(min(int(data.get("limite") or 100), 300)).all()
        return self.tools.output(200, "Historial de avisos." if filas else "Aún no hay avisos.", [self.format(f) for f in filas])

    def test(self, data: dict):
        """ Mensaje de prueba a un teléfono: por el proveedor en modo automático, o el enlace en modo manual """
        config = self.config()
        telefono = normalizar_telefono(data["telefono"], obligatorio=True)
        restaurante = self.db.get(RestauranteModel, self.ctx["restaurante_id"])
        texto = f"Mensaje de prueba de {restaurante.nombre}. Los avisos por WhatsApp están funcionando."
        if not config or config.modo != "automatico":
            return self.tools.output(200, "Abre el enlace para enviar la prueba desde tu WhatsApp.",
                                     {"modo": "manual", "telefono": telefono, "mensaje": texto})
        proveedor = obtener_proveedor(config.proveedor, descifrar(config.credenciales), config.numero_remitente)
        try:
            resultado = proveedor.enviar(telefono, texto, "prueba")
        except ProveedorNoDisponible as error:
            raise CustomException(str(error), 409)
        if resultado.estado != "enviada":
            raise CustomException(resultado.mensaje or "El proveedor no envió el mensaje.")
        return self.tools.output(200, "Mensaje de prueba enviado.", {"modo": "automatico", "referencia": resultado.referencia})

    def process(self, data: dict = None):
        """ Envía los avisos en cola (RN-NOT-03). Una caída del proveedor reintenta con espera; después
            del último intento, o si el proveedor lo rechaza, queda fallido para avisar a mano. """
        config = self.config()
        filas = self.querys.scoped(NotificacionModel).filter(
            NotificacionModel.estado == "pendiente",
            (NotificacionModel.proximo_intento_en.is_(None)) | (NotificacionModel.proximo_intento_en <= now()),
        ).order_by(NotificacionModel.id.asc()).limit(50).with_for_update(skip_locked=True).all()
        enviados = 0
        if not filas:
            return self.tools.output(200, "No hay avisos en cola.", {"enviados": 0})
        if not config or config.modo != "automatico":
            for fila in filas:
                fila.estado = "manual"
            self.db.commit()
            return self.tools.output(200, "Los avisos pasaron a envío manual.", {"enviados": 0})
        proveedor = obtener_proveedor(config.proveedor, descifrar(config.credenciales), config.numero_remitente)
        for fila in filas:
            fila.intentos += 1
            try:
                resultado = proveedor.enviar(fila.telefono, fila.mensaje, fila.evento)
            except ProveedorNoDisponible as error:
                fila.error = str(error)[:200]
                if fila.intentos > len(ESPERAS_MINUTOS):
                    fila.estado = "fallida"
                else:
                    fila.proximo_intento_en = now() + timedelta(minutes=ESPERAS_MINUTOS[fila.intentos - 1])
                continue
            if resultado.estado == "enviada":
                fila.estado, fila.enviada_en, fila.referencia, fila.error = "enviada", now(), resultado.referencia, None
                enviados += 1
            else:
                fila.estado, fila.error = "fallida", (resultado.mensaje or "Rechazado por el proveedor")[:200]
        self.db.commit()
        return self.tools.output(200, f"Avisos enviados: {enviados}.", {"enviados": enviados})

    # ---- Apoyo ----

    def config(self, lock=False):
        query = self.querys.scoped(NotificacionConfigModel)
        if lock:
            query = query.with_for_update()
        return query.first()

    def format_config(self, config):
        restaurante = self.db.get(RestauranteModel, self.ctx["restaurante_id"])
        ejemplo = {"nombre": "Ana", "numero": "#012", "restaurante": restaurante.nombre, "direccion": "Calle 10 # 5-20"}
        return {
            "modo": config.modo if config else "manual",
            "restaurante": restaurante.nombre,
            "proveedor": config.proveedor if config else "simulado",
            "proveedores": list(PROVEEDORES),
            "tiene_credenciales": bool(config and config.credenciales),
            "numero_remitente": telefono_legible(config.numero_remitente) if config and config.numero_remitente else None,
            "limite_diario": config.limite_diario if config else 5,
            "variables": VARIABLES,
            "eventos": [{
                "codigo": codigo, "nombre": evento["nombre"], "activo": evento_activo(config, codigo),
                "plantilla": plantilla_de(config, codigo), "plantilla_defecto": evento["plantilla"],
                "ejemplo": armar(plantilla_de(config, codigo), ejemplo),
            } for codigo, evento in EVENTOS.items()],
        }

    def format(self, aviso):
        orden = self.db.get(OrdenModel, aviso.orden_id) if aviso.orden_id else None
        usuario = self.db.get(UsuarioModel, aviso.enviada_por) if aviso.enviada_por else None
        return {
            "id": aviso.id, "evento": aviso.evento, "evento_texto": EVENTOS.get(aviso.evento, {}).get("nombre", aviso.evento),
            "orden_id": aviso.orden_id, "orden": f"#{orden.numero:03d}" if orden else None,
            "nombre": aviso.nombre, "telefono": aviso.telefono, "telefono_legible": telefono_legible(aviso.telefono),
            "mensaje": aviso.mensaje, "modo": aviso.modo, "estado": aviso.estado, "estado_texto": ESTADOS_TEXTO[aviso.estado],
            "intentos": aviso.intentos, "error": aviso.error, "creado_en": aviso.creado_en,
            "hora_local": to_local(aviso.creado_en, self.ctx.get("zona_horaria")), "enviada_en": aviso.enviada_en,
            "enviada_por": usuario.nombre if usuario else None,
        }
