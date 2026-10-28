from datetime import timedelta
from Utils.tools import Tools, CustomException, clean_text
from Utils.cifrado import cifrar, descifrar
from Utils.proveedores_factura import PROVEEDORES
from Querys.facturacion import FacturacionQuerys
from Models.facturacion_config_model import FacturacionConfigModel
from Models.resolucion_model import TIPOS_DOCUMENTO
from Class.Resolucion import Resolucion
from Class.Caja import dia_actual

AMBIENTES = ["pruebas", "produccion"]
MODOS_SIMULADO = ["aceptar", "rechazar", "caido"]


class Facturacion:
    """ Configuración de facturación electrónica del restaurante y su estado (doc 21A).
        Las credenciales se guardan cifradas y nunca se devuelven (RN-FIS-03). """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = FacturacionQuerys(db, ctx)

    def get_config(self, data: dict = None):
        return self.tools.output(200, "Configuración de facturación.", self.format(self.querys.config()))

    def save_config(self, data: dict):
        if data["proveedor"] not in PROVEEDORES:
            raise CustomException("El proveedor de facturación no está disponible.")
        if data.get("ambiente", "pruebas") not in AMBIENTES:
            raise CustomException("El ambiente no es válido.")
        if data.get("documento_defecto", "pos") not in ("pos", "factura"):
            raise CustomException("El documento por defecto debe ser POS electrónico o factura.")

        config = self.querys.config(lock=True)
        if not config:
            self.querys.insert_data(FacturacionConfigModel, {}, commit=False)
            config = self.querys.config(lock=True)
        antes = {"activo": config.activo, "proveedor": config.proveedor, "ambiente": config.ambiente}

        config.proveedor = data["proveedor"]
        config.ambiente = data.get("ambiente") or "pruebas"
        config.documento_defecto = data.get("documento_defecto") or "pos"
        config.dias_factura_posterior = max(0, min(int(data.get("dias_factura_posterior") or 30), 365))
        # Credenciales: solo se reemplazan si llegan; vacías no borran las guardadas
        credenciales = data.get("credenciales")
        if isinstance(credenciales, dict) and any(v not in (None, "") for v in credenciales.values()):
            if config.proveedor == "simulado" and credenciales.get("modo") not in MODOS_SIMULADO:
                raise CustomException("El modo del proveedor simulado no es válido.")
            config.credenciales = cifrar({k: clean_text(str(v)) for k, v in credenciales.items() if v not in (None, "")})
        activo = data.get("activo") is True
        if activo and not self.querys.resolucion_para(config.documento_defecto, dia_actual(self.ctx)):
            raise CustomException("Para activar la facturación crea primero una resolución vigente del documento por defecto.")
        config.activo = activo

        self.querys.audit("facturacion_configurada", "facturacion_config", config.id, antes=antes,
                          despues={"activo": config.activo, "proveedor": config.proveedor, "ambiente": config.ambiente,
                                   "credenciales_cambiadas": bool(credenciales)}, commit=False)
        self.db.commit()
        return self.tools.output(200, "Facturación activada." if config.activo else "Configuración guardada.",
                                 self.format(config))

    def status(self, data: dict = None):
        """ Tablero de facturación: alertas de numeración, documentos rechazados o en cola y ventas sin documento """
        config = self.querys.config()
        hoy = dia_actual(self.ctx)
        alertas = []
        resolucion = Resolucion(self.db, self.ctx)
        for r in self.querys.resoluciones():
            if not r.activo or r.tipo_documento == "nota_credito":
                continue
            datos = resolucion.format(r)
            if datos["vencida"]:
                alertas.append({"nivel": "critico", "texto": f"La resolución {r.prefijo or ''} {r.desde}-{r.hasta} está vencida."})
            elif datos["restantes"] <= 0:
                alertas.append({"nivel": "critico", "texto": f"La resolución {r.prefijo or ''} {r.desde}-{r.hasta} se agotó."})
            elif datos["por_agotarse"]:
                alertas.append({"nivel": "aviso", "texto": f"Quedan {datos['restantes']} números en la resolución {r.prefijo or ''}."})
            elif r.vigente_hasta and r.vigente_hasta <= hoy + timedelta(days=15):
                alertas.append({"nivel": "aviso", "texto": f"La resolución {r.prefijo or ''} vence el {r.vigente_hasta.strftime('%d/%m/%Y')}."})

        activa = bool(config and config.activo)
        if activa:
            for tipo in ("pos", "factura"):
                if tipo == config.documento_defecto and not self.querys.resolucion_para(tipo, hoy):
                    alertas.append({"nivel": "critico", "texto": "No hay resolución vigente para el documento por defecto: las ventas quedan sin documento."})

        conteo = self.querys.conteo_por_estado()
        if conteo.get("rechazada"):
            alertas.append({"nivel": "critico", "texto": f"{conteo['rechazada']} documento(s) rechazado(s) por corregir."})
        sin_documento = self.querys.cuentas_sin_documento(hoy - timedelta(days=7)) if activa else []
        if sin_documento:
            alertas.append({"nivel": "aviso", "texto": f"{len(sin_documento)} cuenta(s) pagada(s) sin documento en los últimos 7 días."})

        return self.tools.output(200, "Estado de la facturación.", {
            "activa": activa,
            "modulo": "facturacion" in (self.ctx.get("modulos") or set()),
            "proveedor": config.proveedor if config else None,
            "ambiente": config.ambiente if config else None,
            "documentos": conteo,
            "alertas": alertas,
            "cuentas_sin_documento": [{"id": c.id, "numero": c.numero, "total": c.total, "jornada": c.jornada}
                                      for c in sin_documento[:50]],
        })

    def format(self, config):
        if not config:
            return {"activo": False, "proveedor": "simulado", "ambiente": "pruebas", "documento_defecto": "pos",
                    "dias_factura_posterior": 30, "credenciales_guardadas": False, "modo_simulado": None,
                    "proveedores": list(PROVEEDORES), "tipos_documento": TIPOS_DOCUMENTO}
        credenciales = descifrar(config.credenciales)
        return {
            "activo": config.activo,
            "proveedor": config.proveedor,
            "ambiente": config.ambiente,
            "documento_defecto": config.documento_defecto,
            "dias_factura_posterior": config.dias_factura_posterior,
            "credenciales_guardadas": bool(credenciales),
            # El modo del simulado no es un secreto y ayuda a probar
            "modo_simulado": credenciales.get("modo", "aceptar") if config.proveedor == "simulado" else None,
            "proveedores": list(PROVEEDORES),
            "tipos_documento": TIPOS_DOCUMENTO,
        }
