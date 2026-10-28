from datetime import timedelta
from Utils.tools import Tools, CustomException, clean_text, now
from Utils.impuestos import desglosar, repartir, porcentaje_texto
from Utils.cifrado import descifrar
from Utils.proveedores_factura import obtener_proveedor, ProveedorNoDisponible
from Utils.emision import cola_emision
from Querys.facturacion import FacturacionQuerys, proximo_intento
from Querys.caja import CajaQuerys
from Models.documento_venta_model import DocumentoVentaModel
from Models.documento_venta_linea_model import DocumentoVentaLineaModel
from Models.cuenta_model import CuentaModel
from Models.cliente_model import ClienteModel
from Models.empresa_model import EmpresaModel
from Models.restaurante_model import RestauranteModel
from Models.pago_model import PagoModel
from Models.resolucion_model import ResolucionModel
from Models.medio_pago_model import MedioPagoModel
from Class.Resolucion import Resolucion, numero_completo, TIPOS_TEXTO
from Class.Caja import dia_actual
from Class.Impuesto import Impuesto
from Utils.estados import CANCELADO

CONSUMIDOR_FINAL = "Consumidor final"
TIPOS_IDENTIFICACION = ["CC", "CE", "NIT", "PAS", "PPT", "TI"]


class Documento:
    """ Documentos de venta (doc 21): se generan de la cuenta pagada, se numeran de forma atómica
        y se envían al proveedor por una cola con reintentos. Cobrar nunca espera al proveedor (RN-FAC-06). """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = FacturacionQuerys(db, ctx)

    # ---------- Generación ----------

    def activa(self):
        config = self.querys.config()
        return bool(config and config.activo and "facturacion" in (self.ctx.get("modulos") or set())), config

    def generate_for_account(self, cuenta, receptor: dict = None, caja_id=None):
        """ Lo llama Cuenta.settle dentro de la transacción del cobro. Devuelve (documento, aviso).
            Si la facturación no está activa no hace nada; si falta resolución, la venta sigue y queda el aviso. """
        activa, config = self.activa()
        if receptor and not activa:
            raise CustomException("La facturación electrónica no está activa: no se puede facturar a nombre del cliente.", 409)
        if not activa or cuenta.total - cuenta.propina <= 0:
            return None, None
        tipo = "factura" if receptor else config.documento_defecto
        dia = cuenta.jornada or dia_actual(self.ctx)
        resolucion = self.querys.resolucion_para(tipo, dia, caja_id)
        if not resolucion:
            if receptor:
                raise CustomException("No hay una resolución de factura vigente. Cobra sin factura a nombre o configúrala.", 409)
            return None, f"No se generó documento: no hay resolución vigente de {TIPOS_TEXTO[tipo].lower()}."
        return self.build(cuenta, tipo, resolucion, self.clean_receptor(receptor)), None

    def build(self, cuenta, tipo, resolucion, receptor: dict, origen=None, motivo=None):
        numero = self.querys.siguiente_numero(resolucion.id)
        if numero is None:
            raise CustomException("La resolución de numeración se agotó. Configura un rango nuevo.", 409)
        lineas = self.lines_from_origin(origen) if origen else self.lines_from_account(cuenta)
        base = sum(l["base"] for l in lineas)
        impuestos = sum(l["impuesto_valor"] for l in lineas)
        documento_id = self.querys.insert_data(DocumentoVentaModel, {
            "tipo": tipo,
            "cuenta_id": cuenta.id if cuenta else None,
            "documento_origen_id": origen.id if origen else None,
            "motivo": motivo,
            "resolucion_id": resolucion.id,
            "prefijo": resolucion.prefijo,
            "numero": numero,
            "estado": "pendiente",
            "jornada": dia_actual(self.ctx) if origen else (cuenta.jornada or dia_actual(self.ctx)),
            "base": base,
            "impuestos": impuestos,
            "descuento": origen.descuento if origen else cuenta.descuento + cuenta.descuento_cupon + cuenta.descuento_envio,
            "total": base + impuestos,
            "propina": origen.propina if origen else cuenta.propina,
            "creado_por": self.ctx.get("usuario_id"),
            **receptor,
        }, commit=False)
        for linea in lineas:
            self.querys.insert_data(DocumentoVentaLineaModel, {**linea, "documento_id": documento_id}, commit=False)
        return self.querys.get_own(DocumentoVentaModel, documento_id, "documento")

    def lines_from_account(self, cuenta):
        """ Ítems no cancelados de la cuenta con su impuesto desglosado. El descuento (manual y de cupones) se reparte
            entre las líneas en proporción a su valor, así baja la base y el impuesto. """
        caja = CajaQuerys(self.db, self.ctx)
        filas = [item for item, _ in caja.items_de_sesion(cuenta.sesion_mesa_id) if item.estado != CANCELADO]
        modificadores = caja.modifiers_of([item.id for item in filas])
        nombres = {i.id: i.nombre for i in self.querys.impuestos(incluir_inactivos=True)}
        descuentos = repartir(cuenta.descuento + cuenta.descuento_cupon, [item.total for item in filas])
        lineas = []
        for item, descuento in zip(filas, descuentos):
            extras = [m["nombre"] if isinstance(m, dict) else str(m) for m in modificadores.get(item.id, [])]
            descripcion = item.nombre_producto + (f" ({', '.join(extras)})" if extras else "")
            total = item.total - descuento
            base, impuesto = desglosar(total, item.impuesto_porcentaje)
            lineas.append({
                "descripcion": descripcion[:250],
                "cantidad": item.cantidad,
                "precio_unitario": item.precio_unitario,
                "descuento": descuento,
                "total": total,
                "base": base,
                "impuesto_id": item.impuesto_id,
                "impuesto_nombre": nombres.get(item.impuesto_id),
                "porcentaje": item.impuesto_porcentaje or 0,
                "impuesto_valor": impuesto,
            })
        # El domicilio va como concepto aparte con el impuesto que se fijó al pedir (doc 15B, sección 5).
        # Con envío gratis completo la línea no va: no hubo venta de ese servicio.
        entrega = caja.entrega_de_sesion(cuenta.sesion_mesa_id)
        envio = cuenta.envio - cuenta.descuento_envio
        if envio > 0 and entrega:
            base, impuesto = desglosar(envio, entrega.impuesto_porcentaje)
            lineas.append({
                "descripcion": "Domicilio", "cantidad": 1, "precio_unitario": cuenta.envio, "descuento": cuenta.descuento_envio,
                "total": envio, "base": base, "impuesto_id": entrega.impuesto_id,
                "impuesto_nombre": nombres.get(entrega.impuesto_id), "porcentaje": entrega.impuesto_porcentaje or 0,
                "impuesto_valor": impuesto,
            })
        return lineas

    # La nota crédito copia las líneas del documento que anula
    def lines_from_origin(self, origen):
        return [{
            "descripcion": l.descripcion, "cantidad": l.cantidad, "precio_unitario": l.precio_unitario,
            "descuento": l.descuento, "total": l.total, "base": l.base, "impuesto_id": l.impuesto_id,
            "impuesto_nombre": l.impuesto_nombre, "porcentaje": l.porcentaje, "impuesto_valor": l.impuesto_valor,
        } for l in self.querys.lineas(origen.id)]

    def clean_receptor(self, receptor: dict = None):
        if not receptor:
            return {"receptor_nombre": CONSUMIDOR_FINAL, "cliente_id": None}
        cliente = None
        if receptor.get("cliente_id"):
            cliente = self.querys.get_own(ClienteModel, receptor["cliente_id"], "cliente")
        nombre = clean_text(receptor.get("nombre")) or (cliente.nombre if cliente else None)
        tipo_documento = receptor.get("tipo_documento") or (cliente.tipo_documento if cliente else None)
        documento = clean_text(receptor.get("documento")) or (cliente.documento if cliente else None)
        correo = clean_text(receptor.get("correo")) or (cliente.correo if cliente else None)
        if not nombre or not documento:
            raise CustomException("Para la factura a nombre del cliente escribe su nombre y número de documento.")
        if tipo_documento not in TIPOS_IDENTIFICACION:
            raise CustomException("Elige el tipo de documento del cliente.")
        return {
            "cliente_id": cliente.id if cliente else None,
            "receptor_nombre": nombre[:150],
            "receptor_tipo_documento": tipo_documento,
            "receptor_documento": documento.replace(" ", "")[:30],
            "receptor_correo": correo,
        }

    # ---------- Anulación y factura posterior ----------

    def void_for_account(self, cuenta, motivo):
        """ Al anular una cuenta, cada documento vigente recibe su nota crédito (RN-FAC-04) """
        notas = []
        for documento in self.querys.documentos_de_cuenta(cuenta.id):
            if documento.tipo != "nota_credito" and documento.estado != "anulada" and not self.has_credit_note(documento):
                notas.append(self.credit_note(documento, motivo))
        return notas

    def credit_note(self, documento, motivo):
        resolucion = Resolucion(self.db, self.ctx).ensure_credit_range(dia_actual(self.ctx))
        receptor = {c: getattr(documento, c) for c in ("cliente_id", "receptor_nombre", "receptor_tipo_documento",
                                                       "receptor_documento", "receptor_correo")}
        nota = self.build(None, "nota_credito", resolucion, receptor, origen=documento, motivo=motivo)
        nota.cuenta_id = documento.cuenta_id
        self.querys.audit("nota_credito", "documento_venta", documento.id, despues={"nota": numero_completo(nota)},
                          motivo=motivo, commit=False)
        return nota

    def has_credit_note(self, documento):
        return any(n.estado != "rechazada" for n in self.querys.notas_de(documento.id))

    def invoice_for(self, data: dict):
        """ Documento posterior al pago (doc 21, preguntas abiertas):
            - con receptor: factura a nombre del cliente; el documento POS vigente se anula con nota crédito;
            - sin receptor: documento por defecto para una cuenta que quedó sin él (p. ej. sin resolución al cobrar). """
        activa, config = self.activa()
        if not activa:
            raise CustomException("La facturación electrónica no está activa en este restaurante.", 409)
        cuenta = CajaQuerys(self.db, self.ctx).get_own(CuentaModel, data["cuenta_id"], "cuenta", lock=True)
        if cuenta.estado != "pagada":
            raise CustomException("Solo se factura una cuenta pagada.", 409)
        if cuenta.jornada and (dia_actual(self.ctx) - cuenta.jornada).days > config.dias_factura_posterior:
            raise CustomException(f"Pasaron más de {config.dias_factura_posterior} días desde el pago: ya no se puede facturar.", 409)

        vigentes = [d for d in self.querys.documentos_de_cuenta(cuenta.id)
                    if d.tipo != "nota_credito" and d.estado != "anulada" and not self.has_credit_note(d)]
        receptor = data.get("receptor")
        if not receptor and vigentes:
            raise CustomException("La cuenta ya tiene documento de venta.", 409)
        if any(d.tipo == "factura" for d in vigentes):
            raise CustomException("La cuenta ya tiene factura a nombre del cliente. Para cambiarla, anula la cuenta.", 409)

        tipo = "factura" if receptor else config.documento_defecto
        resolucion = self.querys.resolucion_para(tipo, dia_actual(self.ctx))
        if not resolucion:
            raise CustomException(f"No hay una resolución vigente de {TIPOS_TEXTO[tipo].lower()}.", 409)
        receptor = self.clean_receptor(receptor)
        for documento in vigentes:
            self.credit_note(documento, "Se reemplaza por factura a nombre del cliente")
        nuevo = self.build(cuenta, tipo, resolucion, receptor)
        self.db.commit()
        cola_emision.despertar()
        return self.tools.output(201, f"{TIPOS_TEXTO[tipo]} {numero_completo(nuevo)} generado. Se envía en segundo plano.",
                                 self.format(nuevo))

    # Un documento rechazado se corrige (datos del cliente) y vuelve a la cola con el mismo número
    def correct(self, data: dict):
        documento = self.querys.get_own(DocumentoVentaModel, data["documento_id"], "documento", lock=True)
        if documento.estado != "rechazada":
            raise CustomException("Solo se corrige un documento rechazado; uno emitido se corrige con nota crédito (RG-07).", 409)
        if documento.tipo != "nota_credito" and (data.get("receptor") or {}).get("documento"):
            receptor = self.clean_receptor(data["receptor"])
        else:
            receptor = {}
        antes = {"receptor_documento": documento.receptor_documento, "mensaje": documento.proveedor_mensaje}
        for campo, valor in receptor.items():
            setattr(documento, campo, valor)
        documento.estado, documento.proximo_intento_en = "pendiente", None
        self.querys.audit("documento_corregido", "documento_venta", documento.id, antes=antes, despues=receptor or None,
                          commit=False)
        self.db.commit()
        self.process({"documento_ids": [documento.id]})
        self.db.refresh(documento)
        return self.tools.output(200, self.state_message(documento), self.format(documento))

    # ---------- Cola de emisión ----------

    def process(self, data: dict = None):
        """ Envía al proveedor los documentos pendientes de este restaurante cuyo turno ya llegó.
            Lo usa el proceso en segundo plano y el botón "Enviar ahora". """
        data = data or {}
        ids = [int(i) for i in data.get("documento_ids") or []]
        if data.get("forzar") and ids:
            self.querys.scoped(DocumentoVentaModel).filter(DocumentoVentaModel.id.in_(ids),
                                                           DocumentoVentaModel.estado == "pendiente").update(
                {"proximo_intento_en": None}, synchronize_session=False)
            self.db.commit()
        resultados = {"aceptada": 0, "emitida": 0, "rechazada": 0, "pendiente": 0}
        for documento in self.querys.documentos_por_enviar(ids=ids or None):
            resultados[self.emit(documento)] += 1
            self.db.commit()
        enviados = sum(resultados.values())
        msg = "No había documentos por enviar." if not enviados else \
            f"Enviados {enviados}: {resultados['aceptada']} aceptados, {resultados['rechazada']} rechazados, {resultados['pendiente']} en espera."
        return self.tools.output(200, msg, resultados)

    def emit(self, documento):
        # La nota crédito sale después de que el documento que corrige fue aceptado
        if documento.tipo == "nota_credito":
            origen = self.db.get(DocumentoVentaModel, documento.documento_origen_id)
            if origen.estado == "rechazada":
                documento.estado = "anulada"
                documento.proveedor_mensaje = "El documento original nunca fue aceptado: no requiere nota crédito."
                return "rechazada"
            if origen.estado not in ("aceptada", "anulada"):
                documento.proximo_intento_en = now() + timedelta(seconds=30)
                return "pendiente"

        config = self.querys.config()
        documento.intentos += 1
        documento.enviado_en = now()
        try:
            proveedor = obtener_proveedor(config.proveedor, descifrar(config.credenciales), config.ambiente)
            resultado = proveedor.emitir(self.payload(documento))
        except ProveedorNoDisponible as error:
            documento.proveedor_mensaje = str(error)[:500]
            documento.proximo_intento_en = proximo_intento(documento.intentos)
            return "pendiente"
        except Exception as error:  # noqa: BLE001 - un error del proveedor nunca tumba la cola
            documento.proveedor_mensaje = f"Error inesperado del proveedor: {error}"[:500]
            documento.proximo_intento_en = proximo_intento(documento.intentos)
            return "pendiente"

        documento.estado = resultado.estado
        documento.proveedor_mensaje = (resultado.mensaje or "")[:500]
        documento.cufe = resultado.cufe or documento.cufe
        documento.proveedor_referencia = resultado.referencia or documento.proveedor_referencia
        documento.proximo_intento_en = None
        if resultado.estado == "aceptada":
            documento.aceptado_en = now()
            if documento.tipo == "nota_credito":
                origen = self.db.get(DocumentoVentaModel, documento.documento_origen_id)
                origen.estado = "anulada"
        return resultado.estado

    # Lo que el adaptador entrega al proveedor (doc 21A, sección 5)
    def payload(self, documento):
        restaurante = self.db.get(RestauranteModel, documento.restaurante_id)
        empresa = self.db.get(EmpresaModel, documento.empresa_id)
        origen = self.db.get(DocumentoVentaModel, documento.documento_origen_id) if documento.documento_origen_id else None
        pagos = []
        if documento.cuenta_id:
            pagos = [{"medio": medio.nombre, "tipo": medio.tipo, "valor": pago.monto}
                     for pago, medio in self.querys.scoped(PagoModel).join(MedioPagoModel, MedioPagoModel.id == PagoModel.medio_pago_id)
                     .filter(PagoModel.cuenta_id == documento.cuenta_id, PagoModel.estado == "aplicado")
                     .add_columns(MedioPagoModel).all()]
        return {
            "tipo": documento.tipo,
            "numero_completo": numero_completo(documento),
            "prefijo": documento.prefijo,
            "numero": documento.numero,
            "fecha": documento.creado_en.isoformat(),
            "emisor": {"razon_social": empresa.razon_social or empresa.nombre_comercial, "nit": empresa.documento_fiscal,
                       "establecimiento": restaurante.nombre, "direccion": restaurante.direccion},
            "receptor": {"nombre": documento.receptor_nombre, "tipo_documento": documento.receptor_tipo_documento,
                         "documento": documento.receptor_documento, "correo": documento.receptor_correo},
            "lineas": [{
                "descripcion": l.descripcion, "cantidad": l.cantidad, "precio_unitario": l.precio_unitario,
                "descuento": l.descuento, "base": l.base, "impuesto": l.impuesto_nombre,
                "porcentaje": float(l.porcentaje), "impuesto_valor": l.impuesto_valor,
            } for l in self.querys.lineas(documento.id)],
            "base": documento.base,
            "impuestos": documento.impuestos,
            "descuento": documento.descuento,
            "total": documento.total,
            # La propina va aparte y no suma a la base gravable (RN-FAC-03)
            "propina": documento.propina,
            "pagos": pagos,
            "referencia": {"numero": numero_completo(origen), "cufe": origen.cufe, "motivo": documento.motivo} if origen else None,
        }

    # ---------- Consulta ----------

    def list(self, data: dict):
        documentos = self.querys.list_documentos(
            estado=data.get("estado"), tipo=data.get("tipo"),
            desde=Impuesto.parse_date(data.get("desde")), hasta=Impuesto.parse_date(data.get("hasta")),
            buscar=clean_text(data.get("buscar")), limite=min(int(data.get("limite") or 100), 300))
        result = [self.format(d, resumen=True) for d in documentos]
        return self.tools.output(200, "Documentos de venta." if result else "No hay documentos con ese filtro.", result)

    def get(self, data: dict):
        documento = self.querys.get_own(DocumentoVentaModel, data["documento_id"], "documento")
        return self.tools.output(200, "Detalle del documento.", self.format(documento))

    def tax_summary(self, data: dict):
        hoy = dia_actual(self.ctx)
        desde = Impuesto.parse_date(data.get("desde")) or hoy.replace(day=1)
        hasta = Impuesto.parse_date(data.get("hasta")) or hoy
        filas = [{
            "impuesto": nombre or "Sin impuesto",
            "porcentaje": float(porcentaje or 0),
            "porcentaje_texto": f"{porcentaje_texto(porcentaje)} %",
            "base": int(base or 0),
            "impuesto_valor": int(impuesto or 0),
            "total": int(total or 0),
        } for nombre, porcentaje, base, impuesto, total in self.querys.resumen_impuestos(desde, hasta)]
        filas.sort(key=lambda f: -f["total"])
        return self.tools.output(200, "Ventas por impuesto.", {
            "desde": desde, "hasta": hasta, "filas": filas,
            "totales": {c: sum(f[c] for f in filas) for c in ("base", "impuesto_valor", "total")},
        })

    def format(self, documento, resumen=False):
        origen = self.db.get(DocumentoVentaModel, documento.documento_origen_id) if documento.documento_origen_id else None
        data = {
            "id": documento.id,
            "tipo": documento.tipo,
            "tipo_texto": TIPOS_TEXTO[documento.tipo],
            "numero": numero_completo(documento),
            "estado": documento.estado,
            "jornada": documento.jornada,
            "creado_en": documento.creado_en,
            "cuenta_id": documento.cuenta_id,
            "receptor_nombre": documento.receptor_nombre,
            "receptor_tipo_documento": documento.receptor_tipo_documento,
            "receptor_documento": documento.receptor_documento,
            "receptor_correo": documento.receptor_correo,
            "base": documento.base,
            "impuestos": documento.impuestos,
            "descuento": documento.descuento,
            "total": documento.total,
            "propina": documento.propina,
            "cufe": documento.cufe,
            "mensaje": documento.proveedor_mensaje,
            "intentos": documento.intentos,
            "proximo_intento_en": documento.proximo_intento_en,
            "origen": numero_completo(origen) if origen else None,
            "motivo": documento.motivo,
            "notas": [numero_completo(n) for n in self.querys.notas_de(documento.id)],
        }
        if not resumen:
            lineas = self.querys.lineas(documento.id)
            data["lineas"] = [{
                "descripcion": l.descripcion, "cantidad": l.cantidad, "precio_unitario": l.precio_unitario,
                "descuento": l.descuento, "total": l.total, "base": l.base,
                "impuesto": l.impuesto_nombre, "porcentaje": float(l.porcentaje), "impuesto_valor": l.impuesto_valor,
            } for l in lineas]
            data["impuestos_detalle"] = impuestos_detalle(lineas)
            # La tirilla imprime la resolución que autoriza la numeración
            resolucion = self.db.get(ResolucionModel, documento.resolucion_id)
            data["resolucion"] = {
                "numero": resolucion.numero_resolucion, "prefijo": resolucion.prefijo,
                "desde": resolucion.desde, "hasta": resolucion.hasta,
                "vigente_desde": resolucion.vigente_desde, "vigente_hasta": resolucion.vigente_hasta,
            } if resolucion and resolucion.tipo_documento != "nota_credito" else None
        return data

    @staticmethod
    def state_message(documento):
        return {
            "aceptada": "Documento aceptado.",
            "emitida": "Documento enviado; falta la validación.",
            "rechazada": f"El documento fue rechazado: {documento.proveedor_mensaje}",
            "pendiente": "El proveedor no respondió. Se reintentará automáticamente.",
            "anulada": "Documento anulado.",
        }[documento.estado]


def impuestos_detalle(lineas):
    """ Desglose para la tirilla: una fila por impuesto y tasa """
    grupos = {}
    for l in lineas:
        clave = (l.impuesto_nombre or "Sin impuesto", float(l.porcentaje))
        grupo = grupos.setdefault(clave, {"impuesto": clave[0], "porcentaje": clave[1],
                                          "porcentaje_texto": f"{porcentaje_texto(l.porcentaje)} %", "base": 0, "valor": 0})
        grupo["base"] += l.base
        grupo["valor"] += l.impuesto_valor
    return list(grupos.values())
