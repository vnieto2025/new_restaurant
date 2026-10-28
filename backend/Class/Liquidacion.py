import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from Utils.tools import Tools, CustomException, clean_text, now
from Utils.impuestos import repartir
from Querys.liquidacion import LiquidacionQuerys
from Models.liquidacion_config_model import (LiquidacionConfigModel, PERIODOS, MODELOS_PROPINA, METODOS_REPARTO,
                                             DESTINOS_PROPINA_DOMICILIO, MODELOS_PAGO_DOMICILIO)
from Models.liquidacion_model import LiquidacionModel
from Models.liquidacion_linea_model import LiquidacionLineaModel
from Models.liquidacion_ajuste_model import LiquidacionAjusteModel
from Models.cuenta_model import CuentaModel
from Models.entrega_model import EntregaModel
from Models.rendicion_model import RendicionModel
from Models.domiciliario_model import DomiciliarioModel
from Models.usuario_model import UsuarioModel
from Models.restaurante_model import RestauranteModel
from Class.Caja import dia_actual

# Puntos sugeridos por rol para el pozo (doc 26A, sección 3). El restaurante los cambia.
PESOS_DEFECTO = {"mesero": 1.0, "cocina": 0.8, "cajero": 0.5, "encargado_externos": 0.5, "admin_restaurante": 0}
ROLES_TEXTO = {"mesero": "Mesero", "cocina": "Cocina / bar", "cajero": "Cajero", "encargado_externos": "Pedidos externos",
               "admin_restaurante": "Administrador", "admin_empresa": "Administrador", "domiciliario": "Domiciliario"}
MEDIOS_PAGO = ["efectivo", "transferencia", "otro"]
ESTADOS_TEXTO = {"abierta": "Abierta", "calculada": "Calculada", "aprobada": "Aprobada", "pagada": "Pagada"}


def entero(valor):
    return int(Decimal(str(valor)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def periodo_de(fecha: date, periodo: str):
    """ (desde, hasta) del periodo que contiene la fecha: semana de lunes a domingo, quincena 1-15 y 16-fin, o mes """
    if periodo == "semanal":
        desde = fecha - timedelta(days=fecha.weekday())
        return desde, desde + timedelta(days=6)
    ultimo = calendar.monthrange(fecha.year, fecha.month)[1]
    if periodo == "quincenal":
        if fecha.day <= 15:
            return fecha.replace(day=1), fecha.replace(day=15)
        return fecha.replace(day=16), fecha.replace(day=ultimo)
    return fecha.replace(day=1), fecha.replace(day=ultimo)


def peso_reparto(participante, metodo):
    horas, puntos = Decimal(str(participante["horas"] or 0)), Decimal(str(participante["peso"] or 0))
    valor = {"horas": horas, "puntos": puntos}.get(metodo, horas * puntos)
    return int(valor * 1000)


def repartir_propinas(propinas: list, participantes: list, reglas: dict):
    """ Reparto de propinas (doc 26A, secciones 2 y 3). Puro: recibe las propinas
        [{monto, mesero_id, zona_id}] y los participantes [{clave, horas, peso, zonas, participa}].
        - Individual: cada propina va al mesero de la mesa. Mixta: un porcentaje al mesero y el resto al pozo.
          Sin mesero (mostrador, domicilio, QR para llevar) la propina va al pozo.
        - El pozo se reparte por horas, puntos del rol u horas × puntos; por zona si así se configura.
        - La retención, si existe, sale de cada propina antes del reparto.
        Todo en pesos enteros: lo que no se puede repartir (nadie con horas o puntos) queda "sin repartir". """
    porcentaje = {"individual": 100, "colectiva": 0}.get(reglas["modelo"], int(reglas.get("porcentaje_individual") or 0))
    retencion = Decimal(str(reglas.get("retencion") or 0)) / 100
    total = sum(p["monto"] for p in propinas)
    retenido = entero(total * retencion)

    crudo = {}
    for p in propinas:
        if p.get("mesero_id") and porcentaje:
            crudo[p["mesero_id"]] = crudo.get(p["mesero_id"], Decimal(0)) + Decimal(p["monto"]) * porcentaje / 100 * (1 - retencion)
    individual = {mesero: entero(valor) for mesero, valor in crudo.items()}
    pozo_total = total - retenido - sum(individual.values())

    # Cada zona aporta a su pozo lo que no fue individual
    if reglas.get("por_zona"):
        aportes = {}
        for p in propinas:
            parte = 100 - (porcentaje if p.get("mesero_id") else 0)
            aportes[p["zona_id"]] = aportes.get(p["zona_id"], 0) + p["monto"] * parte
        zonas = list(aportes)
        pozos = dict(zip(zonas, repartir(pozo_total, [aportes[z] for z in zonas])))
    else:
        pozos = {None: pozo_total}

    pozo = {}
    por_zona = {}
    sin_repartir = 0
    for zona, valor in pozos.items():
        elegibles = [x for x in participantes if x.get("participa", True)
                     and (zona is None or x.get("zonas") is None or zona in x["zonas"])]
        pesos = [peso_reparto(x, reglas["metodo"]) for x in elegibles]
        por_zona[zona] = {"pozo": valor, "repartido": 0}
        if not valor:
            continue
        if not sum(pesos):
            sin_repartir += valor
            continue
        for participante, parte in zip(elegibles, repartir(valor, pesos)):
            if parte:
                detalle = pozo.setdefault(participante["clave"], {"total": 0, "zonas": {}})
                detalle["total"] += parte
                detalle["zonas"][zona] = detalle["zonas"].get(zona, 0) + parte
        por_zona[zona]["repartido"] = valor
    return {"total": total, "retenido": retenido, "individual": individual, "pozo": pozo, "pozo_total": pozo_total,
            "por_zona": por_zona, "sin_repartir": sin_repartir}


def pago_entrega(entrega, reglas: dict):
    """ Lo que gana el domiciliario por una entrega: tarifa de la zona, porcentaje del envío o base + porcentaje """
    porcentaje = Decimal(str(reglas.get("pago_porcentaje") or 0))
    variable = entero(Decimal(entrega.tarifa) * porcentaje / 100)
    modelo = reglas.get("pago_domicilio") or "zona"
    if modelo == "porcentaje":
        return variable
    if modelo == "mixto":
        return int(reglas.get("pago_base") or 0) + variable
    return entrega.pago_domiciliario


class Liquidacion:
    """ Propinas y pago a domiciliarios por periodo (doc 26A): el sistema calcula y registra según las reglas
        que configura el restaurante; no mueve dinero ni decide qué es legalmente correcto. """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = LiquidacionQuerys(db, ctx)

    # ================= Reglas =================

    def get_config(self):
        return self.tools.output(200, "Reglas de liquidación.", {
            **self.rules(), "puede_propinas": self.can("propinas"), "puede_domiciliarios": self.can("domiciliarios"),
            "roles": {k: v for k, v in ROLES_TEXTO.items() if k not in ("admin_empresa", "domiciliario")},
        })

    def save_config(self, data: dict):
        config = self.querys.config()
        if not config:
            self.querys.insert_data(LiquidacionConfigModel, {}, commit=False)
            config = self.querys.config()
        antes = self.rules()
        if self.can("propinas"):
            config.periodo = data.get("periodo") or config.periodo
            config.modelo = data.get("modelo") or config.modelo
            config.porcentaje_individual = int(data.get("porcentaje_individual") if data.get("porcentaje_individual") is not None
                                               else config.porcentaje_individual)
            if not 0 <= config.porcentaje_individual <= 100:
                raise CustomException("El porcentaje individual va de 0 a 100.")
            config.metodo = data.get("metodo") or config.metodo
            if "por_zona" in data:
                config.por_zona = bool(data["por_zona"])
            if data.get("pesos") is not None:
                pesos = {}
                for rol, peso in data["pesos"].items():
                    if rol not in ROLES_TEXTO:
                        raise CustomException(f"El rol {rol} no existe.")
                    valor = float(peso or 0)
                    if not 0 <= valor <= 10:
                        raise CustomException("Los puntos por rol van de 0 a 10.")
                    pesos[rol] = valor
                config.pesos = pesos
            if data.get("retencion") is not None:
                retencion = Decimal(str(data["retencion"]))
                if not 0 <= retencion <= 50:
                    raise CustomException("La retención va de 0 a 50 %.")
                config.retencion = retencion
            if data.get("propina_domicilio"):
                config.propina_domicilio = data["propina_domicilio"]
        if self.can("domiciliarios"):
            config.pago_domicilio = data.get("pago_domicilio") or config.pago_domicilio
            if data.get("pago_porcentaje") is not None:
                porcentaje = Decimal(str(data["pago_porcentaje"]))
                if not 0 <= porcentaje <= 100:
                    raise CustomException("El porcentaje del envío va de 0 a 100.")
                config.pago_porcentaje = porcentaje
            if data.get("pago_base") is not None:
                config.pago_base = max(int(data["pago_base"]), 0)
        if config.pago_domicilio in ("porcentaje", "mixto") and not config.pago_porcentaje and not config.pago_base:
            raise CustomException("Indica el porcentaje del envío o la base que se le paga al domiciliario.")
        self.db.flush()
        # Las reglas nuevas aplican a liquidaciones nuevas; las calculadas guardan las suyas (RN-PRP-02)
        self.querys.audit("reglas_liquidacion", "liquidacion_config", config.id, antes=antes, despues=self.rules(), commit=False)
        self.db.commit()
        return self.get_config()

    def rules(self):
        config = self.querys.config()
        if not config:
            return {"periodo": "quincenal", "modelo": "colectiva", "porcentaje_individual": 50, "metodo": "horas_puntos",
                    "por_zona": False, "pesos": dict(PESOS_DEFECTO), "retencion": 0, "propina_domicilio": "pozo",
                    "pago_domicilio": "zona", "pago_porcentaje": 0, "pago_base": 0}
        return {"periodo": config.periodo, "modelo": config.modelo, "porcentaje_individual": config.porcentaje_individual,
                "metodo": config.metodo, "por_zona": config.por_zona, "pesos": {**PESOS_DEFECTO, **(config.pesos or {})},
                "retencion": float(config.retencion or 0), "propina_domicilio": config.propina_domicilio,
                "pago_domicilio": config.pago_domicilio, "pago_porcentaje": float(config.pago_porcentaje or 0),
                "pago_base": config.pago_base}

    # ================= Periodos =================

    def list(self, data: dict):
        tipo = self.require(data["tipo"])
        filas = [self.format(l) for l in self.querys.list_liquidaciones(tipo)]
        return self.tools.output(200, "Liquidaciones." if filas else "Aún no hay liquidaciones.", filas)

    def preview(self, data: dict):
        """ Periodo abierto: lo que se lleva acumulado, sin guardar nada (doc 26A, sección 4) """
        tipo = self.require(data["tipo"])
        reglas = self.rules()
        fecha = date.fromisoformat(data["fecha"]) if data.get("fecha") else dia_actual(self.ctx)
        desde, hasta = periodo_de(fecha, reglas["periodo"])
        armado = self.build(tipo, desde, hasta, reglas, self.querys.ajustes(tipo))
        guardada = self.querys.por_periodo(tipo, desde)
        return self.tools.output(200, "Periodo.", {
            "tipo": tipo, "desde": desde, "hasta": hasta, "estado": "abierta", "estado_texto": "Abierta",
            "reglas": reglas, "resumen": armado["resumen"], "total": armado["total"],
            "lineas": [self.format_line_dict(l) for l in armado["lineas"]],
            "liquidacion_id": guardada.id if guardada else None,
        })

    def calculate(self, data: dict):
        """ Cierra el periodo en un borrador editable. Recalcular conserva las horas editadas, quién participa
            y los ajustes. Solo hay un borrador a la vez por tipo: así ninguna propina entra en dos. """
        tipo = self.require(data["tipo"])
        hoy = dia_actual(self.ctx)
        existente = self.querys.get_own(LiquidacionModel, data["liquidacion_id"], "liquidación", lock=True) \
            if data.get("liquidacion_id") else None
        if existente:
            if existente.estado != "calculada":
                raise CustomException("La liquidación ya está aprobada: corrígela con un ajuste en el siguiente periodo.", 409)
            reglas, desde, hasta = existente.reglas, existente.desde, existente.hasta
        else:
            reglas = self.rules()
            fecha = date.fromisoformat(data["fecha"]) if data.get("fecha") else hoy
            desde, hasta = periodo_de(fecha, reglas["periodo"])
            if desde > hoy:
                raise CustomException("Ese periodo todavía no empieza.")
            previa = self.querys.por_periodo(tipo, desde, lock=True)
            if previa and previa.estado != "calculada":
                raise CustomException("Ese periodo ya está liquidado.", 409)
            borrador = self.querys.calculada(tipo)
            if borrador and borrador.id != (previa.id if previa else None):
                raise CustomException(f"Termina primero la liquidación del {borrador.desde.strftime('%d/%m')} al "
                                      f"{borrador.hasta.strftime('%d/%m')}: apruébala o descártala.", 409)
            existente = previa

        if existente:
            liquidacion = existente
            anteriores = {self.key_of(l): l for l in self.querys.lineas(liquidacion.id)}
            self.querys.delete_lineas(liquidacion.id)
        else:
            liquidacion_id = self.querys.insert_data(LiquidacionModel, {
                "tipo": tipo, "desde": desde, "hasta": hasta, "estado": "calculada", "reglas": reglas, "insumos": {}},
                commit=False)
            liquidacion = self.db.get(LiquidacionModel, liquidacion_id)
            anteriores = {}
            # Los ajustes pendientes de periodos aprobados entran en esta (RN-PRP-03)
            for ajuste in self.querys.ajustes(tipo):
                ajuste.liquidacion_id = liquidacion.id
            self.db.flush()

        armado = self.build(tipo, desde, hasta, reglas, self.querys.ajustes(tipo, liquidacion.id), anteriores)
        self.save_lines(liquidacion, armado)
        liquidacion.calculada_en, liquidacion.calculada_por = now(), self.ctx.get("usuario_id")
        self.querys.audit("liquidacion_calculada", "liquidacion", liquidacion.id, despues={"total": liquidacion.total},
                          commit=False)
        self.db.commit()
        mensaje = "Liquidación calculada. Revisa y aprueba."
        if hasta >= hoy:
            mensaje = "Liquidación calculada con lo que va del periodo: lo que entre después irá en la siguiente."
        return self.tools.output(200, mensaje, self.detail(liquidacion))

    def get(self, data: dict):
        liquidacion = self.querys.get_own(LiquidacionModel, data["liquidacion_id"], "liquidación")
        self.require(liquidacion.tipo)
        return self.tools.output(200, "Liquidación.", self.detail(liquidacion))

    def edit_line(self, data: dict):
        """ Horas trabajadas o si participa del pozo: se reparte de nuevo con las mismas propinas """
        linea = self.querys.get_own(LiquidacionLineaModel, data["linea_id"], "línea")
        liquidacion = self.draft(linea.liquidacion_id)
        if liquidacion.tipo != "propinas":
            raise CustomException("En la liquidación de domiciliarios se corrige con un ajuste.", 409)
        antes = {"horas": float(linea.horas), "participa": linea.participa}
        if data.get("horas") is not None:
            horas = Decimal(str(data["horas"]))
            if not 0 <= horas <= 744:
                raise CustomException("Las horas no son válidas.")
            linea.horas, linea.horas_editadas = horas, True
        if data.get("participa") is not None:
            linea.participa = bool(data["participa"])
        self.querys.audit("liquidacion_linea_editada", "liquidacion", liquidacion.id, antes=antes,
                          despues={"horas": float(linea.horas), "participa": linea.participa, "persona": linea.nombre},
                          motivo=clean_text(data.get("motivo")), commit=False)
        self.db.flush()
        anteriores = {self.key_of(l): l for l in self.querys.lineas(liquidacion.id)}
        armado = self.redistribute(liquidacion, anteriores)
        self.querys.delete_lineas(liquidacion.id)
        self.save_lines(liquidacion, armado)
        self.db.commit()
        return self.tools.output(200, "Reparto actualizado.", self.detail(liquidacion))

    def adjust(self, data: dict):
        """ Ajuste manual con motivo (RN-PRP-04). En una liquidación aprobada no se edita: el ajuste queda
            pendiente y entra en la siguiente (RN-PRP-03). """
        liquidacion = self.querys.get_own(LiquidacionModel, data["liquidacion_id"], "liquidación", lock=True)
        self.require(liquidacion.tipo)
        linea = self.querys.get_own(LiquidacionLineaModel, data["linea_id"], "línea")
        if linea.liquidacion_id != liquidacion.id:
            raise CustomException("Esa persona no está en esta liquidación.")
        try:
            valor = int(str(data["valor"]).strip())
        except ValueError:
            raise CustomException("El valor del ajuste no es válido.")
        if not valor:
            raise CustomException("El ajuste no puede ser cero.")
        motivo = clean_text(data["motivo"])
        pendiente = liquidacion.estado != "calculada"
        self.querys.insert_data(LiquidacionAjusteModel, {
            "tipo": liquidacion.tipo, "liquidacion_id": None if pendiente else liquidacion.id,
            "origen_liquidacion_id": liquidacion.id if pendiente else None, "usuario_id": linea.usuario_id,
            "domiciliario_id": linea.domiciliario_id, "valor": valor, "motivo": motivo,
            "creado_por": self.ctx.get("usuario_id")}, commit=False)
        self.querys.audit("liquidacion_ajuste", "liquidacion", liquidacion.id, despues={"persona": linea.nombre, "valor": valor,
                                                                                      "pendiente": pendiente},
                          motivo=motivo, commit=False)
        if not pendiente:
            # Se reasigna el JSON para que el cambio se guarde
            linea.detalle = {**(linea.detalle or {}), "ajustes": [*(linea.detalle or {}).get("ajustes", []),
                                                                  {"valor": valor, "motivo": motivo, "fecha": now().isoformat()}]}
            linea.ajustes += valor
            linea.total += valor
            liquidacion.total += valor
        self.db.commit()
        mensaje = "Ajuste registrado: entra en la siguiente liquidación." if pendiente else "Ajuste aplicado."
        return self.tools.output(200, mensaje, self.detail(liquidacion))

    def discard(self, data: dict):
        """ Descartar el borrador: sus ajustes quedan pendientes para la próxima vez """
        liquidacion = self.draft(data["liquidacion_id"])
        for ajuste in self.querys.ajustes(liquidacion.tipo, liquidacion.id):
            ajuste.liquidacion_id = None
        self.querys.delete_lineas(liquidacion.id)
        self.querys.audit("liquidacion_descartada", "liquidacion", liquidacion.id, commit=False)
        self.db.flush()
        self.db.delete(liquidacion)
        self.db.commit()
        return self.tools.output(200, "Borrador descartado.", {})

    def approve(self, data: dict):
        """ Congela la liquidación (RN-PRP-03) y marca lo liquidado para que no entre otra vez (RN-PRP-06) """
        liquidacion = self.draft(data["liquidacion_id"])
        lineas = self.querys.lineas(liquidacion.id)
        pendientes = [l for l in lineas if (l.detalle or {}).get("por_rendir")]
        if pendientes:
            nombres = ", ".join(f"{l.nombre} ({self.tools.format_number(l.detalle['por_rendir'])})" for l in pendientes)
            raise CustomException(f"Hay efectivo de domicilios por rendir: {nombres}. Ríndelo en caja y recalcula.", 409)
        insumos = liquidacion.insumos or {}
        for modelo, ids, columna in ((CuentaModel, insumos.get("cuentas"), "liquidacion_propina_id"),
                                     (EntregaModel, insumos.get("entregas"), "liquidacion_id"),
                                     (RendicionModel, insumos.get("rendiciones"), "liquidacion_id")):
            if not ids:
                continue
            filas = self.querys.scoped(modelo).filter(modelo.id.in_(ids)).with_for_update().all()
            if any(getattr(f, columna) for f in filas):
                raise CustomException("Algo de este periodo ya se liquidó en otra parte. Recalcula antes de aprobar.", 409)
            for fila in filas:
                setattr(fila, columna, liquidacion.id)
        # Un saldo en contra (faltantes mayores que lo ganado) pasa al siguiente periodo
        for linea in lineas:
            if linea.total < 0:
                self.querys.insert_data(LiquidacionAjusteModel, {
                    "tipo": liquidacion.tipo, "origen_liquidacion_id": liquidacion.id, "usuario_id": linea.usuario_id,
                    "domiciliario_id": linea.domiciliario_id, "valor": linea.total,
                    "motivo": f"Saldo en contra del periodo {liquidacion.desde.strftime('%d/%m')} a {liquidacion.hasta.strftime('%d/%m')}",
                    "creado_por": self.ctx.get("usuario_id")}, commit=False)
        liquidacion.estado, liquidacion.aprobada_en, liquidacion.aprobada_por = "aprobada", now(), self.ctx.get("usuario_id")
        if not any(l.total > 0 for l in lineas):
            liquidacion.estado, liquidacion.pagada_en = "pagada", now()
        self.querys.audit("liquidacion_aprobada", "liquidacion", liquidacion.id, despues={"total": liquidacion.total},
                          commit=False)
        self.db.commit()
        return self.tools.output(200, "Liquidación aprobada. Ya no se modifica.", self.detail(liquidacion))

    def pay_line(self, data: dict):
        """ Registra el pago hecho por fuera del sistema (doc 26A, sección 7) y deja el comprobante """
        linea = self.querys.get_own(LiquidacionLineaModel, data["linea_id"], "línea", lock=True)
        liquidacion = self.querys.get_own(LiquidacionModel, linea.liquidacion_id, "liquidación", lock=True)
        self.require(liquidacion.tipo)
        if liquidacion.estado == "calculada":
            raise CustomException("Aprueba la liquidación antes de registrar pagos.", 409)
        if linea.pagado_en:
            raise CustomException("Ese pago ya está registrado.", 409)
        if linea.total <= 0:
            raise CustomException("No hay nada por pagar a esta persona.", 409)
        linea.pagado_en, linea.pagado_por = now(), self.ctx.get("usuario_id")
        linea.medio_pago, linea.referencia_pago = data["medio_pago"], clean_text(data.get("referencia"))
        self.db.flush()
        if all(l.pagado_en or l.total <= 0 for l in self.querys.lineas(liquidacion.id)):
            liquidacion.estado, liquidacion.pagada_en = "pagada", now()
        self.querys.audit("liquidacion_pagada", "liquidacion", liquidacion.id, despues={"persona": linea.nombre,
                                                                                      "valor": linea.total}, commit=False)
        self.db.commit()
        return self.tools.output(200, f"Pago a {linea.nombre} registrado.", self.detail(liquidacion))

    def mine(self, data: dict):
        """ Cada persona ve solo lo suyo (RN-PRP-05) """
        usuario_id = self.ctx["usuario_id"]
        filas = [{**self.format_line(linea), "liquidacion": self.format(liquidacion)}
                 for linea, liquidacion in self.querys.lineas_de_usuario(usuario_id)]
        reglas = self.rules()
        desde, hasta = periodo_de(dia_actual(self.ctx), reglas["periodo"])
        propinas, cuentas = self.querys.propinas_de_mesero(usuario_id, desde, hasta)
        return self.tools.output(200, "Tus liquidaciones." if filas else "Aún no tienes liquidaciones aprobadas.", {
            "liquidaciones": filas,
            # Propinas de sus mesas que aún no se han liquidado
            "periodo_actual": {"desde": desde, "hasta": hasta, "propinas_mesas": propinas, "cuentas": cuentas,
                               "modelo": reglas["modelo"]},
        })

    # ================= Cálculo =================

    def build(self, tipo, desde, hasta, reglas, ajustes, anteriores=None):
        if tipo == "propinas":
            return self.build_tips(desde, hasta, reglas, ajustes, anteriores or {})
        return self.build_couriers(hasta, reglas, ajustes)

    def build_tips(self, desde, hasta, reglas, ajustes, anteriores):
        domicilios = False if reglas.get("propina_domicilio") == "domiciliario" else None
        filas = self.querys.propinas_por_liquidar(hasta, domicilios)
        propinas = [{"cuenta_id": c.id, "monto": c.propina, "mesero_id": mesero_id, "zona_id": c.zona_id}
                    for c, mesero_id in filas]
        participantes = self.participants(desde, hasta, reglas, anteriores)
        return self.distribute(propinas, participantes, reglas, ajustes)

    def redistribute(self, liquidacion, anteriores):
        """ Mismo reparto con las propinas guardadas en el borrador y los participantes ya editados """
        participantes = []
        for linea in anteriores.values():
            if linea.usuario_id and (float(linea.peso) or float(linea.horas)):
                participantes.append({"clave": ("u", linea.usuario_id), "usuario_id": linea.usuario_id, "nombre": linea.nombre,
                                      "rol": linea.rol, "horas": float(linea.horas), "peso": float(linea.peso),
                                      "zonas": (linea.detalle or {}).get("zonas_asignadas"), "participa": linea.participa,
                                      "horas_editadas": linea.horas_editadas})
        return self.distribute(liquidacion.insumos.get("propinas", []), participantes, liquidacion.reglas,
                               self.querys.ajustes(liquidacion.tipo, liquidacion.id))

    def participants(self, desde, hasta, reglas, anteriores):
        """ Personal del restaurante con puntos en el pozo, con las horas de sus turnos (doc 08A) """
        usuarios = self.querys.list_usuarios()
        ids = [u.id for u in usuarios]
        horas = self.querys.horas(ids, desde, hasta)
        zonas = self.querys.zonas_de_usuarios(ids)
        pesos = reglas.get("pesos") or PESOS_DEFECTO
        resultado = []
        for usuario in usuarios:
            roles = [r.codigo for r in self.querys.get_roles_usuario(usuario.id)]
            if "domiciliario" in roles:
                continue
            rol = max(roles, key=lambda r: pesos.get(r, 0), default=None)
            peso = pesos.get(rol, 0) if rol else 0
            if not peso:
                continue
            fila = {"clave": ("u", usuario.id), "usuario_id": usuario.id, "nombre": usuario.nombre, "rol": rol,
                    "horas": round(horas.get(usuario.id, 0), 2), "peso": peso, "zonas": zonas.get(usuario.id),
                    "participa": True, "horas_editadas": False}
            anterior = anteriores.get(("u", usuario.id))
            if anterior:
                fila["participa"] = anterior.participa
                if anterior.horas_editadas:
                    fila["horas"], fila["horas_editadas"] = float(anterior.horas), True
            resultado.append(fila)
        return resultado

    def distribute(self, propinas, participantes, reglas, ajustes):
        reparto = repartir_propinas(propinas, participantes, reglas)
        zonas = self.querys.nombres_zonas()
        lineas = {}
        for p in participantes:
            lineas[p["clave"]] = self.empty_line(p["clave"], p["nombre"], p["rol"], horas=p["horas"], peso=p["peso"],
                                                 participa=p["participa"], horas_editadas=p.get("horas_editadas", False),
                                                 detalle={"zonas_asignadas": p["zonas"]})
        for mesero_id, valor in reparto["individual"].items():
            clave = ("u", mesero_id)
            if clave not in lineas:
                usuario = self.db.get(UsuarioModel, mesero_id)
                lineas[clave] = self.empty_line(clave, usuario.nombre if usuario else "Mesero", "mesero", detalle={})
            lineas[clave]["individual"] = valor
        for clave, detalle in reparto["pozo"].items():
            lineas[clave]["pozo"] = detalle["total"]
            lineas[clave]["detalle"]["pozo_por_zona"] = {zonas.get(z, "Todas") if z else "Todas": v
                                                         for z, v in detalle["zonas"].items()}
        self.apply_adjustments(lineas, ajustes)
        for linea in lineas.values():
            linea["total"] = linea["individual"] + linea["pozo"] + linea["ajustes"]

        por_zona, por_mesero = {}, {}
        for p in propinas:
            nombre = zonas.get(p["zona_id"], "Sin zona")
            por_zona[nombre] = por_zona.get(nombre, 0) + p["monto"]
            mesero = lineas.get(("u", p["mesero_id"]), {}).get("nombre") if p.get("mesero_id") else None
            if p.get("mesero_id") and not mesero:
                usuario = self.db.get(UsuarioModel, p["mesero_id"])
                mesero = usuario.nombre if usuario else "Mesero"
            por_mesero[mesero or "Sin mesero (mostrador y domicilios)"] = por_mesero.get(mesero or "Sin mesero (mostrador y domicilios)", 0) + p["monto"]
        avisos = []
        if reparto["sin_repartir"]:
            avisos.append(f"{self.tools.format_number(reparto['sin_repartir'])} quedan sin repartir: nadie tiene horas o puntos. "
                          "Escribe las horas trabajadas.")
        ordenadas = sorted(lineas.values(), key=lambda l: l["nombre"])
        return {
            "lineas": ordenadas, "total": sum(l["total"] for l in ordenadas),
            "insumos": {"propinas": propinas, "cuentas": [p["cuenta_id"] for p in propinas]},
            "resumen": {"propinas": reparto["total"], "cuentas": len(propinas), "retenido": reparto["retenido"],
                        "individual": sum(reparto["individual"].values()), "pozo": reparto["pozo_total"],
                        "sin_repartir": reparto["sin_repartir"], "por_zona": por_zona, "por_mesero": por_mesero,
                        "avisos": avisos},
        }

    def build_couriers(self, hasta, reglas, ajustes):
        lineas = {}
        domiciliarios = {d.id: d for d in self.querys.domiciliarios()}

        def linea_de(domiciliario_id):
            clave = ("d", domiciliario_id)
            if clave not in lineas:
                d = domiciliarios.get(domiciliario_id)
                lineas[clave] = self.empty_line(clave, f"{d.codigo} · {d.nombre}" if d else "Domiciliario", "domiciliario",
                                                detalle={"entregas": [], "faltantes": []})
            return lineas[clave]

        entregas = self.querys.entregas_por_liquidar(hasta)
        for entrega in entregas:
            linea = linea_de(entrega.domiciliario_id)
            pago = pago_entrega(entrega, reglas)
            linea["entregas"] += 1
            linea["pago_entregas"] += pago
            linea["detalle"]["entregas"].append({"entrega_id": entrega.id, "barrio": entrega.barrio, "tarifa": entrega.tarifa,
                                                 "pago": pago, "fecha": entrega.entregada_en.isoformat() if entrega.entregada_en else None})
        cuentas = []
        if reglas.get("propina_domicilio") == "domiciliario":
            for cuenta, _ in self.querys.propinas_por_liquidar(hasta, domicilios=True):
                domiciliario_id = self.querys.domiciliario_de_sesion(cuenta.sesion_mesa_id)
                if domiciliario_id:
                    linea_de(domiciliario_id)["propinas"] += cuenta.propina
                    cuentas.append(cuenta.id)
        rendiciones = []
        for rendicion in self.querys.faltantes_por_liquidar():
            linea = linea_de(rendicion.domiciliario_id)
            linea["descuentos"] += -rendicion.diferencia
            linea["detalle"]["faltantes"].append({"rendicion_id": rendicion.id, "valor": -rendicion.diferencia,
                                                  "fecha": rendicion.creado_en.isoformat()})
            rendiciones.append(rendicion.id)
        for domiciliario_id, valor in self.querys.por_rendir().items():
            linea_de(domiciliario_id)["detalle"]["por_rendir"] = valor
        for ajuste in ajustes:
            if ajuste.domiciliario_id:
                linea_de(ajuste.domiciliario_id)
        self.apply_adjustments(lineas, ajustes)
        for linea in lineas.values():
            linea["total"] = linea["pago_entregas"] + linea["propinas"] - linea["descuentos"] + linea["ajustes"]
        ordenadas = sorted(lineas.values(), key=lambda l: l["nombre"])
        avisos = [f"{l['nombre']} tiene {self.tools.format_number(l['detalle']['por_rendir'])} por rendir en caja."
                  for l in ordenadas if l["detalle"].get("por_rendir")]
        return {
            "lineas": ordenadas, "total": sum(l["total"] for l in ordenadas),
            "insumos": {"entregas": [e.id for e in entregas], "cuentas": cuentas, "rendiciones": rendiciones},
            "resumen": {"entregas": len(entregas), "pago_entregas": sum(l["pago_entregas"] for l in ordenadas),
                        "propinas": sum(l["propinas"] for l in ordenadas), "faltantes": sum(l["descuentos"] for l in ordenadas),
                        "avisos": avisos},
        }

    def empty_line(self, clave, nombre, rol, horas=0, peso=0, participa=True, horas_editadas=False, detalle=None):
        return {"clave": clave, "usuario_id": clave[1] if clave[0] == "u" else None,
                "domiciliario_id": clave[1] if clave[0] == "d" else None, "nombre": nombre, "rol": rol, "horas": horas,
                "peso": peso, "participa": participa, "horas_editadas": horas_editadas, "individual": 0, "pozo": 0,
                "entregas": 0, "pago_entregas": 0, "propinas": 0, "descuentos": 0, "ajustes": 0, "total": 0,
                "detalle": detalle or {}, "lista_ajustes": []}

    def apply_adjustments(self, lineas, ajustes):
        for ajuste in ajustes:
            clave = ("u", ajuste.usuario_id) if ajuste.usuario_id else ("d", ajuste.domiciliario_id)
            if clave not in lineas:
                usuario = self.db.get(UsuarioModel, ajuste.usuario_id) if ajuste.usuario_id else None
                lineas[clave] = self.empty_line(clave, usuario.nombre if usuario else "Persona", None)
            lineas[clave]["ajustes"] += ajuste.valor
            lineas[clave]["lista_ajustes"].append({"valor": ajuste.valor, "motivo": ajuste.motivo,
                                                   "fecha": ajuste.creado_en.isoformat() if ajuste.creado_en else None})

    def save_lines(self, liquidacion, armado):
        for linea in armado["lineas"]:
            detalle = {**linea["detalle"], "ajustes": linea["lista_ajustes"]}
            self.querys.insert_data(LiquidacionLineaModel, {
                "liquidacion_id": liquidacion.id, "detalle": detalle,
                **{k: linea[k] for k in ("usuario_id", "domiciliario_id", "nombre", "rol", "horas", "horas_editadas", "peso",
                                         "participa", "individual", "pozo", "entregas", "pago_entregas", "propinas",
                                         "descuentos", "ajustes", "total")},
            }, commit=False)
        liquidacion.insumos = armado["insumos"]
        liquidacion.resumen = armado["resumen"]
        liquidacion.total = armado["total"]
        self.db.flush()

    # ================= Apoyo =================

    def can(self, tipo):
        if tipo == "propinas":
            return "propinas" in self.ctx.get("modulos", set()) and "liquidaciones.gestionar" in self.ctx.get("permisos", set())
        return "domicilios" in self.ctx.get("modulos", set()) and "domicilios.liquidar" in self.ctx.get("permisos", set())

    def require(self, tipo):
        if tipo not in ("propinas", "domiciliarios"):
            raise CustomException("El tipo de liquidación no existe.")
        if not self.can(tipo):
            raise CustomException("No tienes permiso para esta liquidación o el módulo no está contratado.", 403)
        return tipo

    def draft(self, liquidacion_id):
        liquidacion = self.querys.get_own(LiquidacionModel, liquidacion_id, "liquidación", lock=True)
        self.require(liquidacion.tipo)
        if liquidacion.estado != "calculada":
            raise CustomException("La liquidación ya está aprobada y no se modifica (RN-PRP-03).", 409)
        return liquidacion

    def key_of(self, linea):
        return ("u", linea.usuario_id) if linea.usuario_id else ("d", linea.domiciliario_id)

    def detail(self, liquidacion):
        return {**self.format(liquidacion), "lineas": [self.format_line(l) for l in self.querys.lineas(liquidacion.id)],
                "pendientes": [{"valor": a.valor, "motivo": a.motivo} for a in self.querys.ajustes(liquidacion.tipo)
                               if a.origen_liquidacion_id == liquidacion.id]}

    def format(self, liquidacion):
        restaurante = self.db.get(RestauranteModel, self.ctx.get("restaurante_id"))
        return {
            "id": liquidacion.id, "tipo": liquidacion.tipo, "desde": liquidacion.desde, "hasta": liquidacion.hasta,
            "estado": liquidacion.estado, "estado_texto": ESTADOS_TEXTO[liquidacion.estado], "total": liquidacion.total,
            "reglas": liquidacion.reglas, "resumen": liquidacion.resumen or {},
            "calculada_en": liquidacion.calculada_en, "aprobada_en": liquidacion.aprobada_en,
            "aprobada_por": self.nombre(liquidacion.aprobada_por), "pagada_en": liquidacion.pagada_en,
            "restaurante": restaurante.nombre if restaurante else None,
        }

    def format_line(self, linea):
        return {
            "id": linea.id, "usuario_id": linea.usuario_id, "domiciliario_id": linea.domiciliario_id, "nombre": linea.nombre,
            "rol": linea.rol, "rol_texto": ROLES_TEXTO.get(linea.rol, linea.rol or ""), "horas": float(linea.horas),
            "horas_editadas": linea.horas_editadas, "peso": float(linea.peso), "participa": linea.participa,
            "individual": linea.individual, "pozo": linea.pozo, "entregas": linea.entregas,
            "pago_entregas": linea.pago_entregas, "propinas": linea.propinas, "descuentos": linea.descuentos,
            "ajustes": linea.ajustes, "total": linea.total, "detalle": linea.detalle or {},
            "pagado_en": linea.pagado_en, "pagado_por": self.nombre(linea.pagado_por), "medio_pago": linea.medio_pago,
            "referencia_pago": linea.referencia_pago,
        }

    def format_line_dict(self, linea):
        datos = {k: v for k, v in linea.items() if k not in ("clave", "lista_ajustes")}
        return {**datos, "id": None, "rol_texto": ROLES_TEXTO.get(linea["rol"], linea["rol"] or ""),
                "horas": float(linea["horas"] or 0), "peso": float(linea["peso"] or 0),
                "detalle": {**linea["detalle"], "ajustes": linea["lista_ajustes"]}, "pagado_en": None}

    def nombre(self, usuario_id):
        usuario = self.db.get(UsuarioModel, usuario_id) if usuario_id else None
        return usuario.nombre if usuario else None
