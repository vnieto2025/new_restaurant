import re
import secrets
from datetime import date, timedelta, time
from Utils.tools import Tools, CustomException, clean_text, now, to_local
from Utils.estados import CANCELADO
from Querys.cupon import CuponQuerys
from Models.cupon_model import CuponModel, TIPOS_CUPON, CANALES_CUPON
from Models.cupon_redencion_model import CuponRedencionModel, USOS_VIGENTES
from Models.cuenta_model import CuentaModel
from Models.cliente_model import ClienteModel
from Models.producto_model import ProductoModel
from Models.categoria_model import CategoriaModel
from Models.zona_model import ZonaModel
from Models.mesa_model import MesaModel
from Models.usuario_model import UsuarioModel
from Models.restaurante_model import RestauranteModel
from Class.Caja import dia_actual

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
CANALES_TEXTO = {"mesa": "mesa", "para_llevar": "para llevar", "domicilio": "domicilio"}
TIPOS_TEXTO = {"porcentaje": "Porcentaje", "valor": "Valor fijo", "producto": "Producto", "envio": "Envío gratis"}
ESTADOS_TEXTO = {"activo": "Activo", "pausado": "Pausado", "anulado": "Anulado", "vencido": "Vencido",
                 "agotado": "Agotado", "programado": "Programado"}
# Sin letras ni números que se confundan al dictarlos (O/0, I/1)
ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODIGO_VALIDO = re.compile(r"^[A-Z0-9-]{3,30}$")
# Campos que la plantilla le pasa al cupón que emite
CAMPOS_COPIADOS = ["nombre", "descripcion", "tipo", "valor", "tope", "producto_id", "canales", "zonas", "productos",
                   "categorias", "dias", "hora_desde", "hora_hasta", "monto_minimo", "acumulable"]


def normalizar_codigo(codigo):
    return re.sub(r"\s+", "", str(codigo or "")).upper()


def moneda(valor):
    return "$" + f"{int(valor):,}".replace(",", ".")


def consentimiento_comercial(cliente):
    return bool(cliente and cliente.comercial_aceptado_en and not cliente.comercial_revocado_en and not cliente.anonimizado_en)


def descuento_de(cupon, lineas: list, envio: int, disponible: int, nombre_producto=None):
    """ Lo que descuenta un cupón: (sobre los ítems, sobre el domicilio). Si la cuenta no cumple una regla
        que depende de lo pedido, lanza el motivo (RN-CUP-01). Nunca deja la cuenta en negativo (RN-CUP-02). """
    subtotal = sum(l["total"] for l in lineas)
    if subtotal < (cupon.monto_minimo or 0):
        raise CustomException(f"El cupón pide una compra mínima de {moneda(cupon.monto_minimo)}; "
                              f"faltan {moneda(cupon.monto_minimo - subtotal)}.")
    if cupon.tipo == "envio":
        if not envio:
            raise CustomException("El cupón es de envío gratis y esta cuenta no tiene domicilio.")
        return 0, envio

    restringido = bool(cupon.productos or cupon.categorias)
    elegibles = [l for l in lineas if not restringido or l["producto_id"] in (cupon.productos or [])
                 or l["categoria_id"] in (cupon.categorias or [])]
    if not elegibles:
        raise CustomException("El cupón aplica solo a algunos productos y la cuenta no tiene ninguno.")

    if cupon.tipo == "producto":
        candidatas = [l for l in lineas if l["producto_id"] == cupon.producto_id]
        if not candidatas:
            raise CustomException(f"El cupón es para {nombre_producto or 'un producto'} y no está en la cuenta.")
        unidad = max(round(l["total"] / l["cantidad"]) for l in candidatas)
        valor = round(unidad * cupon.valor / 100)
    elif cupon.tipo == "porcentaje":
        valor = round(sum(l["total"] for l in elegibles) * cupon.valor / 100)
        if cupon.tope:
            valor = min(valor, cupon.tope)
    else:
        valor = min(cupon.valor, sum(l["total"] for l in elegibles))
    return max(min(valor, disponible), 0), 0


class Cupon:
    """ Cupones de descuento (doc 25A): se crean con reglas, se aplican al cobrar validados en el servidor
        (RN-CUP-05), cada uso queda como redención y solo se revierte con la anulación de la cuenta (RN-CUP-03). """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = CuponQuerys(db, ctx)

    # ================= Administración =================

    def list(self, data: dict):
        cupones = self.querys.list_cupones(data.get("estado"), clean_text(data.get("buscar")), bool(data.get("plantillas")),
                                           data.get("cliente_id"))
        usos = self.querys.usos_por_cupon([c.id for c in cupones])
        filas = [self.format(c, usos.get(c.id, 0)) for c in cupones]
        if data.get("vigentes"):
            filas = [f for f in filas if f["estado_actual"] in ("activo", "programado")]
        return self.tools.output(200, "Cupones." if filas else "Aún no hay cupones.", filas)

    def get(self, data: dict):
        cupon = self.querys.get_own(CuponModel, data["cupon_id"], "cupón")
        detalle = self.format(cupon, self.querys.usos(cupon.id))
        detalle["redenciones"] = [self.format_redencion(r) for r in self.querys.redenciones_de_cupon(cupon.id)]
        return self.tools.output(200, "Detalle del cupón.", detalle)

    def save(self, data: dict):
        cupon = self.querys.get_own(CuponModel, data["cupon_id"], "cupón", lock=True) if data.get("cupon_id") else None
        valores = self.clean(data, cupon)
        if cupon:
            antes = self.format(cupon)
            for campo, valor in valores.items():
                setattr(cupon, campo, valor)
            self.db.flush()
            self.querys.audit("cupon_editado", "cupon", cupon.id, antes={"codigo": antes["codigo"], "valor": antes["valor"]},
                              despues={"codigo": cupon.codigo, "valor": cupon.valor}, commit=False)
            mensaje = "Cupón actualizado."
        else:
            cupon_id = self.querys.insert_data(CuponModel, {**valores, "estado": "activo", "origen": "manual",
                                                            "creado_por": self.ctx.get("usuario_id")}, commit=False)
            cupon = self.db.get(CuponModel, cupon_id)
            self.querys.audit("cupon_creado", "cupon", cupon.id, despues={"codigo": cupon.codigo, "tipo": cupon.tipo,
                                                                          "valor": cupon.valor}, commit=False)
            mensaje = "Plantilla creada." if cupon.plantilla else f"Cupón {cupon.codigo} creado."
        self.db.commit()
        return self.tools.output(200 if data.get("cupon_id") else 201, mensaje, self.format(cupon, self.querys.usos(cupon.id)))

    def change_status(self, data: dict):
        cupon = self.querys.get_own(CuponModel, data["cupon_id"], "cupón", lock=True)
        estado = data["estado"]
        if cupon.estado == "anulado":
            raise CustomException("El cupón está anulado y no se puede reactivar.", 409)
        if estado == cupon.estado:
            return self.tools.output(200, "Sin cambios.", self.format(cupon, self.querys.usos(cupon.id)))
        antes = cupon.estado
        cupon.estado = estado
        # Lo ya aplicado en cuentas abiertas se respeta: la regla se revisó al aplicarlo
        self.querys.audit("cupon_estado", "cupon", cupon.id, antes={"estado": antes}, despues={"estado": estado},
                          motivo=clean_text(data.get("motivo")), commit=False)
        self.db.commit()
        textos = {"activo": "Cupón activo.", "pausado": "Cupón pausado: no se puede aplicar hasta reactivarlo.",
                  "anulado": "Cupón anulado."}
        return self.tools.output(200, textos[estado], self.format(cupon, self.querys.usos(cupon.id)))

    def send(self, data: dict):
        """ Mensaje de WhatsApp para un cupón personal, solo con consentimiento comercial (RN-CLI-04, RN-NOT-02).
            En este paso se envía con el enlace de WhatsApp desde el celular o computador del restaurante. """
        cupon = self.querys.get_own(CuponModel, data["cupon_id"], "cupón", lock=True)
        if not cupon.cliente_id:
            raise CustomException("Solo se envían cupones personales. Asígnalo a un cliente.", 409)
        if self.state_of(cupon, self.querys.usos(cupon.id)) not in ("activo", "programado"):
            raise CustomException("El cupón no está vigente.", 409)
        cliente = self.db.get(ClienteModel, cupon.cliente_id)
        if not consentimiento_comercial(cliente):
            raise CustomException("El cliente no autorizó recibir promociones. Solo se le puede entregar en persona.", 409)
        if not cliente.telefono:
            raise CustomException("El cliente no tiene celular registrado.", 409)
        restaurante = self.db.get(RestauranteModel, self.ctx["restaurante_id"])
        mensaje = (f"Hola {cliente.nombre.split(' ')[0]}, tienes un cupón en {restaurante.nombre}: "
                   f"{cupon.descripcion or cupon.nombre}. Código {cupon.codigo}"
                   + (f", válido hasta el {cupon.termina.strftime('%d/%m/%Y')}" if cupon.termina else "") + ".")
        cupon.enviado_en = now()
        self.querys.audit("cupon_enviado", "cupon", cupon.id, despues={"cliente_id": cliente.id}, commit=False)
        self.db.commit()
        return self.tools.output(200, "Mensaje listo para enviar.", {"telefono": cliente.telefono, "mensaje": mensaje})

    def results(self, data: dict):
        """ Redenciones por cupón, canal y usuario; ventas atribuidas, costo del descuento, ticket con y sin cupón
            y clientes nuevos (doc 25A, sección 6) """
        hasta = date.fromisoformat(data["hasta"]) if data.get("hasta") else dia_actual(self.ctx)
        desde = date.fromisoformat(data["desde"]) if data.get("desde") else hasta - timedelta(days=29)
        if desde > hasta:
            raise CustomException("La fecha inicial es posterior a la final.")
        filas = self.querys.redimidas(desde, hasta)
        cuentas = self.querys.cuentas_pagadas(desde, hasta)
        con_cupon = {cuenta.id for _, cuenta in filas}
        neto = lambda c: c.subtotal - c.descuento - c.descuento_cupon  # noqa: E731
        sin = [c for c in cuentas if c.id not in con_cupon]

        cupones = {}
        por_cupon, por_canal, por_usuario = {}, {}, {}
        nuevos_total = set()
        for redencion, cuenta in filas:
            cupon = cupones.get(redencion.cupon_id) or self.db.get(CuponModel, redencion.cupon_id)
            cupones[cupon.id] = cupon
            # Los cupones emitidos por una plantilla se agrupan en ella
            grupo = cupones.get(cupon.plantilla_id) or (self.db.get(CuponModel, cupon.plantilla_id) if cupon.plantilla_id else cupon)
            cupones[grupo.id] = grupo
            nuevo = bool(redencion.cliente_id) and self.new_client(redencion.cliente_id, cuenta)
            if nuevo:
                nuevos_total.add(redencion.cliente_id)
            for tabla, clave, nombre in ((por_cupon, grupo.id, f"Automático: {grupo.nombre}" if grupo.plantilla else grupo.codigo),
                                         (por_canal, redencion.canal, CANALES_TEXTO.get(redencion.canal, redencion.canal).capitalize()),
                                         (por_usuario, redencion.aplicada_por or 0,
                                          self.querys.nombre_usuario(redencion.aplicada_por) or "El cliente desde su celular")):
                fila = tabla.setdefault(clave, {"clave": clave, "nombre": nombre, "redenciones": 0, "descuento": 0,
                                                "ventas": 0, "clientes_nuevos": 0})
                fila["redenciones"] += 1
                fila["descuento"] += redencion.valor
                fila["ventas"] += redencion.ventas
                fila["clientes_nuevos"] += int(nuevo)
        for tabla in (por_cupon, por_canal, por_usuario):
            for fila in tabla.values():
                bruto = fila["ventas"] + fila["descuento"]
                fila["costo_porcentaje"] = round(fila["descuento"] * 100 / bruto, 1) if bruto else 0
                fila["ticket_promedio"] = round(fila["ventas"] / fila["redenciones"]) if fila["redenciones"] else 0
        for clave, fila in por_cupon.items():
            fila["nombre_cupon"] = cupones[clave].nombre

        cuentas_con = [c for c in cuentas if c.id in con_cupon]
        ventas_con = sum(neto(c) for c in cuentas_con)
        descuento = sum(r.valor for r, _ in filas)
        return self.tools.output(200, "Resultados de los cupones.", {
            "desde": desde, "hasta": hasta,
            "resumen": {
                "redenciones": len(filas),
                "cuentas": len(cuentas_con),
                "descuento": descuento,
                "ventas": ventas_con,
                "costo_porcentaje": round(descuento * 100 / (ventas_con + descuento), 1) if ventas_con + descuento else 0,
                "ticket_con_cupon": round(ventas_con / len(cuentas_con)) if cuentas_con else 0,
                "ticket_sin_cupon": round(sum(neto(c) for c in sin) / len(sin)) if sin else 0,
                "clientes_nuevos": len(nuevos_total),
            },
            "por_cupon": sorted(por_cupon.values(), key=lambda f: -f["redenciones"]),
            "por_canal": sorted(por_canal.values(), key=lambda f: -f["redenciones"]),
            "por_usuario": sorted(por_usuario.values(), key=lambda f: -f["redenciones"]),
        })

    # ================= En la cuenta =================

    def apply(self, data: dict):
        """ El cajero ingresa el código (doc 25A, sección 4) """
        from Class.Cuenta import Cuenta
        cuentas = Cuenta(self.db, self.ctx)
        cuenta = self.querys.get_own(CuentaModel, data["cuenta_id"], "cuenta", lock=True)
        cuentas.can_charge_table(self.db.get(MesaModel, cuenta.mesa_id))
        if data.get("cliente_id"):
            self.set_client(cuenta, data["cliente_id"])
        cupon = self.apply_code(cuenta, data["codigo"])
        self.db.commit()
        cuentas.notify(cuenta, "cuenta.actualizada")
        return self.tools.output(200, f"Cupón {cupon.codigo} aplicado.", cuentas.format(cuenta))

    def remove(self, data: dict):
        """ Quitar un cupón antes de pagar. Una vez pagada, solo se revierte anulando la cuenta (RN-CUP-03). """
        from Class.Cuenta import Cuenta
        cuentas = Cuenta(self.db, self.ctx)
        cuenta = self.querys.get_own(CuentaModel, data["cuenta_id"], "cuenta", lock=True)
        cuentas.can_charge_table(self.db.get(MesaModel, cuenta.mesa_id))
        if cuenta.estado != "abierta":
            raise CustomException("La cuenta ya se pagó: el cupón solo se revierte anulando la cuenta.", 409)
        redencion = self.querys.get_own(CuponRedencionModel, data["redencion_id"], "cupón aplicado", lock=True)
        if redencion.cuenta_id != cuenta.id or redencion.estado != "aplicada":
            raise CustomException("Ese cupón no está aplicado en esta cuenta.", 409)
        if self.querys.pago_en_curso(cuenta.id):
            raise CustomException("Hay un pago en línea en curso: espera su resultado antes de cambiar la cuenta.", 409)
        redencion.estado, redencion.motivo = "quitada", "Quitado antes de pagar"
        self.db.flush()
        cuentas.refresh(cuenta)
        if cuenta.total < cuenta.pagado:
            raise CustomException("Sin el cupón, lo ya pagado quedaría por encima del total.", 409)
        cupon = self.db.get(CuponModel, redencion.cupon_id)
        self.querys.audit("cupon_quitado", "cuenta", cuenta.id, antes={"cupon": cupon.codigo, "valor": redencion.valor},
                          commit=False)
        self.db.commit()
        cuentas.notify(cuenta, "cuenta.actualizada")
        return self.tools.output(200, "Cupón quitado.", cuentas.format(cuenta))

    def identify(self, data: dict):
        """ Cliente de la cuenta: habilita sus cupones personales y el cupón para la próxima visita """
        from Class.Cuenta import Cuenta
        cuentas = Cuenta(self.db, self.ctx)
        cuenta = self.querys.get_own(CuentaModel, data["cuenta_id"], "cuenta", lock=True)
        cuentas.can_charge_table(self.db.get(MesaModel, cuenta.mesa_id))
        if cuenta.estado != "abierta":
            raise CustomException("La cuenta ya no está abierta.", 409)
        if data.get("cliente_id"):
            self.set_client(cuenta, data["cliente_id"])
            mensaje = "Cliente identificado."
        else:
            cuenta.cliente_id = None
            mensaje = "La cuenta quedó sin cliente."
        self.drop_foreign_personal(cuenta)
        self.db.flush()
        cuentas.refresh(cuenta)
        self.db.commit()
        return self.tools.output(200, mensaje, cuentas.format(cuenta))

    def apply_code(self, cuenta, codigo):
        """ Valida todas las reglas y deja la redención aplicada. La comparten caja y el cliente desde su celular. """
        from Class.Cuenta import Cuenta
        if cuenta.estado != "abierta":
            raise CustomException("La cuenta ya no está abierta.", 409)
        if self.querys.pago_en_curso(cuenta.id):
            raise CustomException("Hay un pago en línea en curso: espera su resultado antes de aplicar un cupón.", 409)
        codigo = normalizar_codigo(codigo)
        # El cupón queda bloqueado mientras se cuentan sus usos: dos cajas no lo gastan a la vez
        cupon = self.querys.by_code(codigo, lock=True) if codigo else None
        if not cupon or cupon.plantilla or cupon.estado == "anulado":
            raise CustomException(f"El cupón {codigo} no existe.", 404)

        cuentas = Cuenta(self.db, self.ctx)
        cuentas.refresh(cuenta)
        aplicadas = self.querys.redenciones_de_cuenta(cuenta.id)
        if any(r.cupon_id == cupon.id for r in aplicadas):
            raise CustomException("Ese cupón ya está aplicado en esta cuenta.", 409)
        if aplicadas and (not cupon.acumulable or not all(self.db.get(CuponModel, r.cupon_id).acumulable for r in aplicadas)):
            raise CustomException("La cuenta ya tiene un cupón y no se pueden combinar.", 409)

        contexto = self.account_context(cuenta)
        cliente_id = self.client_of(cuenta)
        self.check_rules(cupon, contexto, cliente_id, cuenta.id)
        disponible = cuenta.subtotal - cuenta.descuento - cuenta.descuento_cupon
        items, envio = descuento_de(cupon, contexto["lineas"], cuenta.envio - cuenta.descuento_envio, disponible,
                                    self.product_name(cupon))
        if items + envio <= 0:
            raise CustomException("La cuenta ya no tiene valor para descontar.", 409)

        fila = {"cliente_id": cliente_id, "valor": items + envio, "estado": "aplicada", "canal": contexto["canal"],
                "aplicada_por": self.ctx.get("usuario_id"), "nota": None, "motivo": None}
        redencion = self.querys.redencion(cupon.id, cuenta.id)
        if redencion:
            for campo, valor in fila.items():
                setattr(redencion, campo, valor)
            self.db.flush()
        else:
            self.querys.insert_data(CuponRedencionModel, {**fila, "cupon_id": cupon.id, "cuenta_id": cuenta.id}, commit=False)
        cuentas.refresh(cuenta)
        if cuenta.total < cuenta.pagado:
            raise CustomException("Con el cupón, lo ya pagado quedaría por encima del total.", 409)
        self.querys.audit("cupon_aplicado", "cuenta", cuenta.id, despues={"cupon": cupon.codigo, "valor": items + envio,
                                                                          "origen": "caja" if self.ctx.get("usuario_id") else "cliente"},
                          commit=False)
        return cupon

    def check_rules(self, cupon, contexto, cliente_id, cuenta_id):
        """ Reglas que no dependen de lo pedido: estado, vigencia, canal, zona, horario, cliente y usos (RN-CUP-01) """
        if cupon.estado == "pausado":
            raise CustomException("El cupón está pausado.", 409)
        dia = dia_actual(self.ctx)
        if cupon.inicia and dia < cupon.inicia:
            raise CustomException(f"El cupón se puede usar desde el {cupon.inicia.strftime('%d/%m/%Y')}.", 409)
        if cupon.termina and dia > cupon.termina:
            raise CustomException(f"El cupón venció el {cupon.termina.strftime('%d/%m/%Y')}.", 409)
        if cupon.canales and contexto["canal"] not in cupon.canales:
            raise CustomException(f"El cupón no aplica en {CANALES_TEXTO[contexto['canal']]}; "
                                  f"solo en {', '.join(CANALES_TEXTO[c] for c in cupon.canales)}.", 409)
        if cupon.zonas and contexto["zona_id"] not in cupon.zonas:
            raise CustomException("El cupón no aplica en esta zona.", 409)
        local = to_local(now(), self.ctx.get("zona_horaria"))
        if cupon.dias and local.weekday() not in cupon.dias:
            raise CustomException(f"El cupón solo aplica los {', '.join(DIAS[d] for d in sorted(cupon.dias))}.", 409)
        if cupon.hora_desde and cupon.hora_hasta and not en_horario(local.time(), cupon.hora_desde, cupon.hora_hasta):
            raise CustomException(f"El cupón solo aplica de {cupon.hora_desde.strftime('%H:%M')} a "
                                  f"{cupon.hora_hasta.strftime('%H:%M')}.", 409)
        if cupon.cliente_id:
            if not cliente_id:
                raise CustomException("Este cupón es personal: identifica al cliente en la cuenta.", 409)
            if cupon.cliente_id != cliente_id:
                raise CustomException("Este cupón es de otro cliente.", 409)
        if cupon.usos_maximos and self.querys.usos(cupon.id, excluir_cuenta=cuenta_id) >= cupon.usos_maximos:
            raise CustomException("El cupón ya se usó el máximo de veces.", 409)
        if cupon.usos_por_cliente:
            if not cliente_id:
                raise CustomException("Este cupón tiene límite por cliente: identifica al cliente en la cuenta.", 409)
            if self.querys.usos(cupon.id, cliente_id, excluir_cuenta=cuenta_id) >= cupon.usos_por_cliente:
                raise CustomException("Este cliente ya usó el cupón las veces permitidas.", 409)

    def refresh_account(self, cuenta):
        """ Lo llama Cuenta.refresh: mientras la cuenta está abierta, cada cupón se recalcula con lo pedido.
            Si deja de cumplir el mínimo o ya no está el producto, no descuenta y queda la nota. """
        aplicadas = self.querys.redenciones_de_cuenta(cuenta.id)
        if not aplicadas:
            cuenta.descuento_cupon = cuenta.descuento_envio = 0
            return
        contexto = self.account_context(cuenta)
        disponible = cuenta.subtotal - cuenta.descuento
        items = envio = 0
        for redencion in aplicadas:
            cupon = self.db.get(CuponModel, redencion.cupon_id)
            try:
                valor_items, valor_envio = descuento_de(cupon, contexto["lineas"], cuenta.envio - envio, disponible - items,
                                                        self.product_name(cupon))
                redencion.nota = None
            except CustomException as error:
                valor_items = valor_envio = 0
                redencion.nota = error.message[:200]
            redencion.valor = valor_items + valor_envio
            items += valor_items
            envio += valor_envio
        cuenta.descuento_cupon, cuenta.descuento_envio = items, envio

    def on_settle(self, cuenta):
        """ Al pagarse la cuenta: los cupones aplicados quedan redimidos y, si aplica, se emite el de la próxima visita """
        for redencion in self.querys.redenciones_de_cuenta(cuenta.id):
            if redencion.valor > 0:
                redencion.estado, redencion.redimida_en = "redimida", now()
                redencion.ventas = cuenta.subtotal - cuenta.descuento - cuenta.descuento_cupon
            else:
                redencion.estado, redencion.motivo = "quitada", redencion.nota or "No descontaba al pagar"
        self.db.flush()
        return self.emit_after_purchase(cuenta)

    def on_void(self, cuenta, motivo):
        """ Anular la cuenta revierte sus redenciones (RN-CUP-03) y anula el cupón que ella emitió si no se usó """
        for redencion in self.querys.redenciones_de_cuenta(cuenta.id, USOS_VIGENTES):
            redencion.estado, redencion.revertida_en, redencion.motivo = "revertida", now(), motivo
        self.db.flush()
        for emitido in self.querys.emitidos_por_cuenta(cuenta.id):
            if emitido.estado != "anulado" and not self.querys.usos(emitido.id):
                emitido.estado = "anulado"

    def emit_after_purchase(self, cuenta):
        """ Cupón personal para la próxima visita (doc 25A, sección 3): con cliente identificado, compra desde el
            mínimo de una plantilla activa y sin otro cupón de esa plantilla por usar. Uno por cuenta. """
        if "fidelizacion" not in (self.ctx.get("modulos") or set()) or self.querys.emitidos_por_cuenta(cuenta.id):
            return None
        cliente_id = self.client_of(cuenta)
        cliente = self.db.get(ClienteModel, cliente_id) if cliente_id else None
        if not cliente or cliente.anonimizado_en or cliente.estado != "activo":
            return None
        dia = cuenta.jornada or dia_actual(self.ctx)
        neto = cuenta.subtotal - cuenta.descuento - cuenta.descuento_cupon
        for plantilla in self.querys.plantillas_para(neto):
            if (plantilla.inicia and dia < plantilla.inicia) or (plantilla.termina and dia > plantilla.termina):
                continue
            if self.querys.emitido_vivo(plantilla.id, cliente.id, dia):
                return None
            cupon_id = self.querys.insert_data(CuponModel, {
                **{campo: getattr(plantilla, campo) for campo in CAMPOS_COPIADOS},
                "codigo": self.new_code(), "cliente_id": cliente.id, "usos_maximos": 1, "inicia": dia,
                "termina": dia + timedelta(days=plantilla.dias_validez or 30), "estado": "activo", "origen": "automatico",
                "plantilla": False, "plantilla_id": plantilla.id, "cuenta_origen_id": cuenta.id,
            }, commit=False)
            return self.db.get(CuponModel, cupon_id)
        return None

    def for_account(self, cuenta):
        """ Lo que la cuenta muestra de cupones: aplicados, cliente, sus cupones disponibles y el obsequio emitido """
        estados = ("aplicada",) if cuenta.estado == "abierta" else ("redimida",)
        aplicados = []
        for redencion in self.querys.redenciones_de_cuenta(cuenta.id, estados):
            cupon = self.db.get(CuponModel, redencion.cupon_id)
            aplicados.append({"redencion_id": redencion.id, "codigo": cupon.codigo, "nombre": cupon.nombre,
                              "tipo": cupon.tipo, "valor": redencion.valor, "nota": redencion.nota,
                              "aplicado_por": self.querys.nombre_usuario(redencion.aplicada_por) or "Cliente"})
        cliente_id = self.client_of(cuenta)
        cliente = self.db.get(ClienteModel, cliente_id) if cliente_id else None
        disponibles = []
        if cliente and cuenta.estado == "abierta":
            usados = {a["codigo"] for a in aplicados}
            personales = self.querys.list_cupones("activo", cliente_id=cliente.id)
            usos = self.querys.usos_por_cupon([c.id for c in personales])
            disponibles = [{"codigo": c.codigo, "nombre": c.nombre, "descripcion": c.descripcion, "termina": c.termina}
                           for c in personales if c.codigo not in usados and self.state_of(c, usos.get(c.id, 0)) == "activo"]
        emitido = next(iter(self.querys.emitidos_por_cuenta(cuenta.id)), None) if cuenta.estado == "pagada" else None
        return {
            "cupones": aplicados,
            "cliente": {"id": cliente.id, "nombre": cliente.nombre} if cliente and not cliente.anonimizado_en else None,
            "cupones_cliente": disponibles,
            "cupon_obsequio": {"codigo": emitido.codigo, "descripcion": emitido.descripcion or emitido.nombre,
                               "termina": emitido.termina} if emitido and emitido.estado == "activo" else None,
        }

    def client_summary(self, cliente_id):
        """ Cupones personales y usados de un cliente, para su ficha (doc 25, sección 4) """
        personales = self.querys.list_cupones(cliente_id=cliente_id)
        usos = self.querys.usos_por_cupon([c.id for c in personales])
        usados = []
        for redencion in self.querys.redenciones_de_cliente(cliente_id):
            if redencion.estado != "redimida":
                continue
            cupon = self.db.get(CuponModel, redencion.cupon_id)
            usados.append({"codigo": cupon.codigo, "nombre": cupon.nombre, "valor": redencion.valor,
                           "fecha": redencion.redimida_en})
        return {"personales": [self.format(c, usos.get(c.id, 0)) for c in personales], "usados": usados}

    # ================= Apoyo =================

    def set_client(self, cuenta, cliente_id):
        cliente = self.querys.get_own(ClienteModel, cliente_id, "cliente")
        if cliente.anonimizado_en or cliente.estado == "bloqueado":
            raise CustomException("Ese cliente no se puede asociar a la cuenta.", 409)
        cuenta.cliente_id = cliente.id

    def drop_foreign_personal(self, cuenta):
        """ Al cambiar el cliente, se quitan los cupones personales de otra persona (RN-CUP-04) """
        cliente_id = self.client_of(cuenta)
        for redencion in self.querys.redenciones_de_cuenta(cuenta.id):
            cupon = self.db.get(CuponModel, redencion.cupon_id)
            if cupon.cliente_id and cupon.cliente_id != cliente_id:
                redencion.estado, redencion.motivo = "quitada", "Cambió el cliente de la cuenta"
            else:
                redencion.cliente_id = cliente_id

    def client_of(self, cuenta):
        return cuenta.cliente_id or self.querys.cliente_de_sesion(cuenta.sesion_mesa_id)

    def account_context(self, cuenta):
        filas = [item for item, _ in self.querys.items_de_sesion(cuenta.sesion_mesa_id) if item.estado != CANCELADO]
        ids = {item.producto_id for item in filas}
        categorias = {p.id: p.categoria_id for p in self.querys.scoped(ProductoModel).filter(ProductoModel.id.in_(ids))} if ids else {}
        mesa = self.db.get(MesaModel, cuenta.mesa_id)
        if self.querys.entrega_de_sesion(cuenta.sesion_mesa_id):
            canal = "domicilio"
        else:
            canal = "para_llevar" if mesa.tipo == "externa" else "mesa"
        return {
            "canal": canal, "zona_id": cuenta.zona_id,
            "lineas": [{"producto_id": i.producto_id, "categoria_id": categorias.get(i.producto_id), "cantidad": i.cantidad,
                        "total": i.total} for i in filas],
        }

    def product_name(self, cupon):
        if cupon.tipo != "producto" or not cupon.producto_id:
            return None
        producto = self.db.get(ProductoModel, cupon.producto_id)
        return producto.nombre if producto else None

    def new_code(self, prefijo=""):
        for _ in range(20):
            codigo = prefijo + "".join(secrets.choice(ALFABETO) for _ in range(8))
            if not self.querys.code_exists(codigo):
                return codigo
        raise CustomException("No se pudo generar un código único. Intenta de nuevo.", 409)

    def new_client(self, cliente_id, cuenta):
        primera = self.querys.primera_orden(cliente_id)
        if primera:
            return primera.sesion_mesa_id == cuenta.sesion_mesa_id
        # Registrado al cobrar, sin órdenes a su nombre: es nuevo si se registró esa jornada
        cliente = self.db.get(ClienteModel, cliente_id)
        return bool(cliente) and to_local(cliente.creado_en, self.ctx.get("zona_horaria")).date() == cuenta.jornada

    def state_of(self, cupon, usos):
        if cupon.estado != "activo":
            return cupon.estado
        dia = dia_actual(self.ctx)
        if cupon.termina and dia > cupon.termina:
            return "vencido"
        if cupon.usos_maximos and usos >= cupon.usos_maximos:
            return "agotado"
        if cupon.inicia and dia < cupon.inicia:
            return "programado"
        return "activo"

    def clean(self, data: dict, cupon=None):
        """ Valida y normaliza lo que se guarda de un cupón o una plantilla """
        plantilla = bool(cupon.plantilla) if cupon else bool(data.get("plantilla"))
        tipo = data["tipo"]
        usos = self.querys.usos(cupon.id) if cupon else 0
        if cupon and usos and tipo != cupon.tipo:
            raise CustomException("El cupón ya se usó: no se puede cambiar su tipo. Crea otro.", 409)

        codigo = normalizar_codigo(data.get("codigo"))
        if cupon and usos and codigo and codigo != cupon.codigo:
            raise CustomException("El cupón ya se usó: no se puede cambiar su código.", 409)
        if not codigo:
            if cupon:
                codigo = cupon.codigo
            elif plantilla:
                codigo = self.new_code("AUTO-")
            elif data.get("cliente_id"):
                codigo = self.new_code()
            else:
                raise CustomException("Escribe el código del cupón.")
        if not CODIGO_VALIDO.match(codigo):
            raise CustomException("El código solo puede tener letras, números y guiones (de 3 a 30).")
        if codigo != (cupon.codigo if cupon else None) and self.querys.code_exists(codigo):
            raise CustomException(f"Ya existe un cupón con el código {codigo}.", 409)

        valor = int(data.get("valor") or 0)
        producto_id = None
        if tipo == "porcentaje" and not 1 <= valor <= 100:
            raise CustomException("El porcentaje va de 1 a 100.")
        if tipo == "valor" and valor <= 0:
            raise CustomException("Escribe el valor del descuento.")
        if tipo == "producto":
            if not data.get("producto_id"):
                raise CustomException("Elige el producto del cupón.")
            producto_id = self.querys.get_own(ProductoModel, data["producto_id"], "producto").id
            valor = valor or 100
            if not 1 <= valor <= 100:
                raise CustomException("El porcentaje sobre el producto va de 1 a 100 (100 = gratis).")
        if tipo == "envio":
            valor = 0
        tope = int(data["tope"]) if tipo == "porcentaje" and data.get("tope") else None

        inicia = date.fromisoformat(data["inicia"]) if data.get("inicia") else None
        termina = date.fromisoformat(data["termina"]) if data.get("termina") else None
        if inicia and termina and termina < inicia:
            raise CustomException("La fecha final es anterior a la inicial.")

        canales = sorted(set(data.get("canales") or []))
        if set(canales) - set(CANALES_CUPON):
            raise CustomException("Hay un canal que no existe.")
        zonas = sorted({self.querys.get_own(ZonaModel, z, "zona").id for z in data.get("zonas") or []})
        productos = sorted({self.querys.get_own(ProductoModel, p, "producto").id for p in data.get("productos") or []})
        categorias = sorted({self.querys.get_own(CategoriaModel, c, "categoría").id for c in data.get("categorias") or []})
        dias = sorted({int(d) for d in data.get("dias") or []})
        if any(d < 0 or d > 6 for d in dias):
            raise CustomException("Hay un día de la semana que no existe.")
        desde, hasta = hora(data.get("hora_desde")), hora(data.get("hora_hasta"))
        if bool(desde) != bool(hasta):
            raise CustomException("Indica la hora de inicio y la de fin, o ninguna.")

        cliente_id = None
        if data.get("cliente_id"):
            if plantilla:
                raise CustomException("Una plantilla no se asigna a un cliente: emite cupones para cada cliente.")
            cliente = self.querys.get_own(ClienteModel, data["cliente_id"], "cliente")
            if cliente.anonimizado_en:
                raise CustomException("Ese cliente fue anonimizado.", 409)
            cliente_id = cliente.id

        valores = {
            "codigo": codigo, "nombre": clean_text(data["nombre"]), "descripcion": clean_text(data.get("descripcion")),
            "tipo": tipo, "valor": valor, "tope": tope, "producto_id": producto_id, "inicia": inicia, "termina": termina,
            "canales": canales or None, "zonas": zonas or None, "productos": productos or None,
            "categorias": categorias or None, "dias": dias or None, "hora_desde": desde, "hora_hasta": hasta,
            "monto_minimo": int(data.get("monto_minimo") or 0), "acumulable": bool(data.get("acumulable")),
            "usos_maximos": int(data["usos_maximos"]) if data.get("usos_maximos") else None,
            "usos_por_cliente": int(data["usos_por_cliente"]) if data.get("usos_por_cliente") else None,
            "cliente_id": cliente_id, "plantilla": plantilla,
        }
        if valores["usos_maximos"] is not None and valores["usos_maximos"] < 1:
            raise CustomException("Los usos totales deben ser al menos 1.")
        if valores["usos_por_cliente"] is not None and valores["usos_por_cliente"] < 1:
            raise CustomException("Los usos por cliente deben ser al menos 1.")
        if plantilla:
            valores["emitir_desde"] = int(data.get("emitir_desde") or 0)
            valores["dias_validez"] = int(data.get("dias_validez") or 0)
            if valores["emitir_desde"] <= 0:
                raise CustomException("Indica desde qué valor de compra se emite el cupón.")
            if not 1 <= valores["dias_validez"] <= 365:
                raise CustomException("Los días de validez van de 1 a 365.")
        return valores

    def format(self, cupon, usos=0):
        producto = self.db.get(ProductoModel, cupon.producto_id) if cupon.producto_id else None
        cliente = self.db.get(ClienteModel, cupon.cliente_id) if cupon.cliente_id else None
        estado = self.state_of(cupon, usos)
        return {
            "id": cupon.id, "codigo": cupon.codigo, "nombre": cupon.nombre, "descripcion": cupon.descripcion,
            "tipo": cupon.tipo, "tipo_texto": TIPOS_TEXTO[cupon.tipo], "valor": cupon.valor, "tope": cupon.tope,
            "beneficio": self.benefit_text(cupon, producto),
            "producto_id": cupon.producto_id, "producto": producto.nombre if producto else None,
            "inicia": cupon.inicia, "termina": cupon.termina,
            "canales": cupon.canales or [], "zonas": cupon.zonas or [], "productos": cupon.productos or [],
            "categorias": cupon.categorias or [], "dias": cupon.dias or [],
            "hora_desde": cupon.hora_desde.strftime("%H:%M") if cupon.hora_desde else None,
            "hora_hasta": cupon.hora_hasta.strftime("%H:%M") if cupon.hora_hasta else None,
            "monto_minimo": cupon.monto_minimo, "usos_maximos": cupon.usos_maximos,
            "usos_por_cliente": cupon.usos_por_cliente, "usos": usos, "acumulable": cupon.acumulable,
            "cliente_id": cupon.cliente_id,
            "cliente": cliente.nombre if cliente and not cliente.anonimizado_en else None,
            "cliente_contactable": consentimiento_comercial(cliente) and bool(cliente.telefono),
            "estado": cupon.estado, "estado_actual": estado, "estado_texto": ESTADOS_TEXTO[estado],
            "origen": cupon.origen, "plantilla": cupon.plantilla, "emitir_desde": cupon.emitir_desde,
            "dias_validez": cupon.dias_validez, "enviado_en": cupon.enviado_en, "creado_en": cupon.creado_en,
        }

    def benefit_text(self, cupon, producto=None):
        if cupon.tipo == "porcentaje":
            return f"{cupon.valor} % de descuento" + (f" (hasta {moneda(cupon.tope)})" if cupon.tope else "")
        if cupon.tipo == "valor":
            return f"{moneda(cupon.valor)} de descuento"
        if cupon.tipo == "envio":
            return "Domicilio gratis"
        nombre = producto.nombre if producto else "producto"
        return f"{nombre} gratis" if cupon.valor >= 100 else f"{cupon.valor} % en {nombre}"

    def format_redencion(self, redencion):
        cuenta = self.db.get(CuentaModel, redencion.cuenta_id)
        cliente = self.db.get(ClienteModel, redencion.cliente_id) if redencion.cliente_id else None
        return {
            "id": redencion.id, "estado": redencion.estado, "valor": redencion.valor, "canal": redencion.canal,
            "cuenta": f"C-{cuenta.numero:05d}" if cuenta and cuenta.numero else None,
            "cliente": cliente.nombre if cliente and not cliente.anonimizado_en else None,
            "aplicada_por": self.querys.nombre_usuario(redencion.aplicada_por) or "Cliente",
            "fecha": redencion.redimida_en or redencion.creado_en, "motivo": redencion.motivo,
        }


def hora(texto):
    if not texto:
        return None
    horas, minutos = str(texto)[:5].split(":")
    return time(int(horas), int(minutos))


def en_horario(actual, desde, hasta):
    """ Si "hasta" es menor que "desde", la franja cruza la medianoche """
    if desde <= hasta:
        return desde <= actual <= hasta
    return actual >= desde or actual <= hasta
