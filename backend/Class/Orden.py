import secrets
from sqlalchemy.exc import IntegrityError
from Utils.tools import Tools, CustomException, clean_text, jornada, now
from Utils.estados import (
    PENDIENTE, NUEVO, EN_PROCESO, DESPACHADO, ENTREGADO, CANCELADO, PENDIENTES_DE_ENTREGA,
)
from Utils.realtime import realtime, channels_for
from Querys.orden import OrdenQuerys
from Querys.mesa import MesaQuerys
from Querys.carta import CartaQuerys
from Querys.modificador import ModificadorQuerys
from Querys.horario import HorarioQuerys
from Models.orden_model import OrdenModel
from Models.orden_item_model import OrdenItemModel
from Models.orden_item_modificador_model import OrdenItemModificadorModel
from Models.comanda_model import ComandaModel
from Models.mesa_model import MesaModel
from Models.zona_model import ZonaModel
from Models.sesion_mesa_model import SesionMesaModel
from Class.Mesa import check_zone_scope
from Class.Cliente import Cliente
from Class.Caja import dia_actual
from Querys.facturacion import FacturacionQuerys
from Utils.contexto import modulos_activos
from Models.cierre_jornada_model import CierreJornadaModel

MAX_CANTIDAD = 50
MAX_ITEMS = 40

# Canales en los que el cliente pide por su cuenta desde el QR
CANALES_QR = ["qr_mesa", "qr_rapido"]


class Orden:

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = OrdenQuerys(db, ctx)
        self.mesas = MesaQuerys(db, ctx)

    # Carta de la zona de una mesa, para tomar la orden en la tablet o en el mostrador
    def menu(self, data: dict):

        mesa = self.get_table(data["mesa_id"])
        zona = self.querys.get_own(ZonaModel, mesa.zona_id, "zona")
        categorias = CartaQuerys(self.db, self.ctx).menu(HorarioQuerys(self.db, self.ctx).current_menu(zona))
        return self.tools.output(200, "Carta de la zona.", {
            "mesa": {"id": mesa.id, "nombre": mesa.nombre, "tipo": mesa.tipo},
            "zona": {"id": zona.id, "nombre": zona.nombre},
            "categorias": categorias,
        })

    # Orden desde la tablet del mesero (mesa normal) o desde el mostrador (mesa externa)
    def create(self, data: dict):

        mesa = self.get_table(data["mesa_id"], lock=True)
        canal = "mostrador" if mesa.tipo == "externa" else "tablet"
        entrega = data.get("entrega")
        if entrega:
            if mesa.tipo != "externa":
                raise CustomException("Un domicilio se registra como pedido externo, no en una mesa.")
            canal = "domicilio"
        es_mesero = "ordenes.crear_mesa" in self.ctx["permisos"]

        orden, creada = self.create_order(
            mesa=mesa,
            canal=canal,
            items=data["items"],
            clave=data["clave_idempotencia"],
            notas=data.get("notas"),
            cliente_nombre=data.get("cliente_nombre"),
            cliente_telefono=data.get("cliente_telefono"),
            mesero_id=self.ctx["usuario_id"] if canal == "tablet" and es_mesero else None,
            acepta_datos=data.get("acepta_datos") is True,
            entrega=entrega,
        )
        detalle = self.querys.format_orden(orden)
        if not creada:
            return self.tools.output(200, f"La orden {detalle['numero_texto']} ya estaba registrada.", detalle)
        return self.tools.output(201, f"Orden {detalle['numero_texto']} enviada.", detalle)

    def create_order(self, mesa, canal: str, items: list, clave: str, notas=None,
                     cliente_nombre=None, cliente_telefono=None, mesero_id=None, acepta_datos=False, entrega=None,
                     aprobacion=None):
        """ Crea una orden por cualquier canal (doc 15, sección 4). La mesa debe venir bloqueada
            (SELECT ... FOR UPDATE) para que dos envíos simultáneos a la misma mesa se ordenen.
            aprobacion: si la orden espera confirmación; sin indicarla, la decide el modo QR de la zona.
            Devuelve (orden, creada). Un reintento con la misma clave devuelve la orden original. """

        clave = str(clave).strip()
        existente = self.querys.get_orden_by_clave(clave)
        if existente:
            self.db.rollback()
            return existente, False

        restaurante = self.querys.restaurante()
        if restaurante.estado in ["cerrado", "inactivo"]:
            raise CustomException(restaurante.mensaje_carta or "El restaurante está cerrado y no recibe órdenes.", 409)
        # Lo que pide el cliente por su cuenta (QR o domicilio web) respeta la pausa; el personal no
        por_cliente = canal in CANALES_QR or bool(self.ctx.get("publico"))
        if restaurante.estado == "pausado" and por_cliente:
            raise CustomException(restaurante.mensaje_carta or "El restaurante pausó la recepción de órdenes. Intenta en unos minutos.", 409)

        zona = self.querys.get_own(ZonaModel, mesa.zona_id, "zona")
        if not zona.activo:
            raise CustomException("La zona no está recibiendo órdenes.", 409)
        if not mesa.activo or mesa.bloqueada:
            raise CustomException("La mesa no está recibiendo órdenes.", 409)
        abierta, motivo = HorarioQuerys(self.db, self.ctx).reception_status(zona)
        if not abierta:
            raise CustomException(motivo, 409)
        if mesa.tipo == "externa" and canal in ["mostrador", "qr_rapido", "domicilio"] and not clean_text(cliente_nombre):
            raise CustomException("Indique el nombre del cliente para identificar la orden.")

        lineas = self.price_items(items, zona)
        preparada = None
        if entrega:
            from Class.Entrega import Entrega
            preparada = Entrega(self.db, self.ctx).prepare(entrega, sum(l["total"] for l in lineas), cliente_nombre, cliente_telefono)
            cliente_telefono = cliente_telefono or preparada["telefono"]
        canal_datos = "carta" if por_cliente else "mostrador"
        cliente = Cliente(self.db, self.ctx).for_order(clean_text(cliente_nombre), cliente_telefono, acepta_datos, canal_datos)

        if mesa.tipo == "externa":
            sesion = self.mesas.open_session(mesa)
        else:
            sesion = self.mesas.get_open_session(mesa.id, lock=True) or self.mesas.open_session(mesa, mesero_id)
        if mesero_id and not sesion.mesero_id:
            sesion.mesero_id = mesero_id

        dia = jornada(tz_name=restaurante.zona_horaria, inicio=restaurante.hora_inicio_jornada)
        if self.querys.scoped(CierreJornadaModel).filter(CierreJornadaModel.jornada == dia).first():
            raise CustomException("La jornada de hoy ya se cerró. Las órdenes se reciben desde la próxima jornada.", 409)
        pendiente = aprobacion if aprobacion is not None else (canal in CANALES_QR and zona.modo_qr == "aprobacion")

        try:
            orden_id = self.querys.insert_data(OrdenModel, {
                "numero": self.querys.next_number(dia),
                "jornada": dia,
                "canal": canal,
                "zona_id": zona.id,
                "mesa_id": mesa.id,
                "sesion_mesa_id": sesion.id,
                "mesero_id": mesero_id or sesion.mesero_id,
                "creado_por": self.ctx.get("usuario_id"),
                "cliente_id": cliente.id if cliente else None,
                "cliente_nombre": clean_text(cliente_nombre) or (cliente.nombre if cliente else None),
                "cliente_telefono": cliente.telefono if cliente else clean_text(cliente_telefono),
                "notas": clean_text(notas),
                "clave_idempotencia": clave,
                "token_seguimiento": secrets.token_urlsafe(24),
                "moneda": restaurante.moneda,
                "total": sum(linea["total"] for linea in lineas),
            }, commit=False)
        except CustomException:
            # Otro envío con la misma clave ganó la carrera: se devuelve esa orden
            self.db.rollback()
            existente = self.querys.get_orden_by_clave(clave)
            if existente:
                return existente, False
            raise

        orden = self.db.get(OrdenModel, orden_id)
        if preparada:
            from Class.Entrega import Entrega
            Entrega(self.db, self.ctx).attach(orden, preparada, cliente)
        nuevos = self.insert_items(orden, lineas, PENDIENTE if pendiente else NUEVO, clave)
        puntos = [] if pendiente else self.split_into_commands(orden, nuevos, es_adicion=False)
        en_cola = False
        if mesa.tipo == "externa":
            from Utils.notificaciones import notificar
            self.db.flush()
            en_cola = notificar(self.db, self.ctx, "orden_recibida", orden)

        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            existente = self.querys.get_orden_by_clave(clave)
            if existente:
                return existente, False
            raise

        tipo = "orden.por_aprobar" if pendiente else "orden.nueva"
        self.notify(orden, puntos, tipo)
        if en_cola:
            from Utils.mensajeria import cola_mensajes
            cola_mensajes.despertar()
        return orden, True

    # Agregar ítems a una orden enviada: crea comandas de adición (doc 15, sección 5)
    def add_items(self, data: dict):

        orden = self.querys.get_own(OrdenModel, data["orden_id"], "orden", lock=True)
        check_zone_scope(self.ctx, orden.zona_id)
        clave = str(data["clave_idempotencia"]).strip()

        if self.querys.items_by_lote(orden.id, clave):
            return self.tools.output(200, "Los ítems ya estaban agregados.", self.querys.format_orden(orden))

        sesion = self.db.get(SesionMesaModel, orden.sesion_mesa_id)
        if sesion.estado != "abierta":
            raise CustomException("La mesa de esta orden ya se cerró. Cree una orden nueva.", 409)
        items_actuales = self.querys.items_of(orden.id)
        if any(i.estado == PENDIENTE for i in items_actuales):
            raise CustomException("Apruebe la orden antes de agregarle ítems.", 409)

        mesa = self.get_table(orden.mesa_id, lock=True)
        zona = self.querys.get_own(ZonaModel, mesa.zona_id, "zona")
        lineas = self.price_items(data["items"], zona)

        nuevos = self.insert_items(orden, lineas, NUEVO, clave)
        puntos = self.split_into_commands(orden, nuevos, es_adicion=True)
        self.querys.recalc_total(orden)
        self.db.commit()

        self.notify(orden, puntos, "orden.adicion")
        return self.tools.output(200, "Ítems agregados y enviados a producción.", self.querys.format_orden(orden))

    def get(self, data: dict):
        orden = self.querys.get_own(OrdenModel, data["orden_id"], "orden")
        check_zone_scope(self.ctx, orden.zona_id)
        return self.tools.output(200, "Datos de la orden.", self.querys.format_orden(orden))

    # Órdenes de la jornada actual; por defecto solo las que tienen ítems sin entregar
    def list(self, data: dict):

        if data.get("mesa_id"):
            # Todo lo pedido en la sesión abierta de la mesa
            mesa = self.get_table(data["mesa_id"])
            sesion = self.mesas.get_open_session(mesa.id)
            ordenes = self.querys.list_ordenes(sesion_mesa_id=sesion.id, solo_activas=False) if sesion else []
        else:
            dia = jornada(tz_name=self.ctx.get("zona_horaria"), inicio=self.ctx.get("hora_inicio_jornada"))
            ordenes = self.querys.list_ordenes(
                jornada=dia,
                zona_ids=self.ctx.get("zonas"),
                zona_id=data.get("zona_id"),
                solo_activas=(data.get("vista") or "activas") == "activas",
            )

        result = [self.querys.format_orden(orden) for orden in ordenes]
        msg = "Listado de órdenes." if result else "No hay órdenes que mostrar."
        return self.tools.output(200, msg, result)

    # El mesero acepta una orden de QR: pasa a producción (doc 10A, sección 5)
    def approve(self, data: dict):

        orden = self.querys.get_own(OrdenModel, data["orden_id"], "orden", lock=True)
        check_zone_scope(self.ctx, orden.zona_id)
        self.check_approver(orden)
        pendientes = [i for i in self.querys.items_of(orden.id, lock=True) if i.estado == PENDIENTE]
        if not pendientes:
            raise CustomException("La orden no está pendiente de aprobación.", 409)

        for item in pendientes:
            self.querys.transition(item, NUEVO, "Aprobada por el mesero" if orden.canal != "domicilio" else "Domicilio confirmado")
        puntos = self.split_into_commands(orden, pendientes, es_adicion=False)

        orden.aprobada_por = self.ctx["usuario_id"]
        orden.aprobada_en = now()
        sesion = self.db.get(SesionMesaModel, orden.sesion_mesa_id)
        if not orden.mesero_id and "ordenes.crear_mesa" in self.ctx["permisos"]:
            orden.mesero_id = self.ctx["usuario_id"]
        if not sesion.mesero_id:
            sesion.mesero_id = orden.mesero_id
        self.db.commit()

        self.notify(orden, puntos, "orden.nueva")
        return self.tools.output(200, "Orden aprobada y enviada a producción.", self.querys.format_orden(orden))

    def reject(self, data: dict):

        orden = self.querys.get_own(OrdenModel, data["orden_id"], "orden", lock=True)
        check_zone_scope(self.ctx, orden.zona_id)
        self.check_approver(orden)
        pendientes = [i for i in self.querys.items_of(orden.id, lock=True) if i.estado == PENDIENTE]
        if not pendientes:
            raise CustomException("La orden no está pendiente de aprobación.", 409)

        motivo = clean_text(data["motivo"])
        for item in pendientes:
            self.querys.transition(item, CANCELADO, motivo)
            item.motivo_cancelacion = motivo
            item.tipo_cancelacion = "cancelacion"
        self.querys.recalc_total(orden)
        self.querys.audit("orden_rechazada", "orden", orden.id, motivo=motivo, commit=False)
        if orden.canal == "domicilio":
            from Class.Entrega import Entrega
            Entrega(self.db, self.ctx).cancel_unconfirmed(orden, motivo)
        self.close_external_session(orden)
        self.db.commit()

        self.notify(orden, [], "orden.actualizada")
        return self.tools.output(200, "Orden rechazada.", self.querys.format_orden(orden))

    # Quitar un ítem: el permiso depende de cuánto avanzó (doc 15, sección 5; doc 29)
    def cancel_item(self, data: dict):

        item = self.querys.get_own(OrdenItemModel, data["orden_item_id"], "ítem", lock=True)
        orden = self.querys.get_own(OrdenModel, item.orden_id, "orden", lock=True)
        check_zone_scope(self.ctx, orden.zona_id)

        avanzado = item.estado in [EN_PROCESO, DESPACHADO, ENTREGADO]
        requerido = "ordenes.cancelar_en_proceso" if avanzado else "ordenes.cancelar_nuevo"
        if requerido not in self.ctx["permisos"]:
            raise CustomException("Este ítem ya está en producción. Solo un administrador puede cancelarlo.", 403)

        motivo = clean_text(data["motivo"])
        tipo = data.get("tipo") or ("perdida" if avanzado else "cancelacion")
        estado_anterior = item.estado

        self.querys.transition(item, CANCELADO, motivo)
        item.motivo_cancelacion = motivo
        item.tipo_cancelacion = tipo
        self.querys.recalc_total(orden)
        # Las anulaciones se auditan siempre (RG-14)
        self.querys.audit("item_cancelado", "orden_item", item.id,
                          antes={"estado": estado_anterior}, despues={"estado": CANCELADO, "tipo": tipo},
                          motivo=motivo, commit=False)
        self.close_external_session(orden)
        self.db.commit()

        self.notify(orden, [item.punto_produccion_id], "orden.modificada")
        return self.tools.output(200, f"{item.nombre_producto} cancelado.", self.querys.format_orden(orden))

    # Confirmar que el cliente recibió lo despachado (doc 16)
    def deliver(self, data: dict):

        if data.get("orden_item_ids"):
            items = [self.querys.get_own(OrdenItemModel, i, "ítem", lock=True) for i in data["orden_item_ids"]]
            orden_ids = {item.orden_id for item in items}
            if len(orden_ids) != 1:
                raise CustomException("Los ítems deben ser de una misma orden.")
            orden = self.querys.get_own(OrdenModel, orden_ids.pop(), "orden", lock=True)
        elif data.get("orden_id"):
            orden = self.querys.get_own(OrdenModel, data["orden_id"], "orden", lock=True)
            items = [i for i in self.querys.items_of(orden.id, lock=True) if i.estado == DESPACHADO]
        else:
            raise CustomException("Indique la orden o los ítems entregados.")

        check_zone_scope(self.ctx, orden.zona_id)
        if not items:
            raise CustomException("No hay ítems listos para entregar en esta orden.", 409)

        for item in items:
            self.querys.transition(item, ENTREGADO)
        self.close_external_session(orden)
        self.db.commit()

        self.notify(orden, [i.punto_produccion_id for i in items], "orden.entregada")
        return self.tools.output(200, "Entregado.", self.querys.format_orden(orden))

    # Datos para la tirilla de la orden con precios (para llevar o pre-cuenta)
    def ticket(self, data: dict):
        orden = self.querys.get_own(OrdenModel, data["orden_id"], "orden")
        check_zone_scope(self.ctx, orden.zona_id)
        restaurante = self.querys.restaurante()
        detalle = self.querys.format_orden(orden)
        detalle["items"] = [i for i in detalle["items"] if i["estado"] != CANCELADO]
        detalle["restaurante"] = {"nombre": restaurante.nombre, "direccion": restaurante.direccion,
                                  "telefono": restaurante.telefono}
        detalle["hora_local"] = self.querys.local_time(orden.creado_en)
        # El domiciliario sale con la tirilla: dirección, teléfono y tarifa de envío
        from Querys.caja import CajaQuerys
        caja = CajaQuerys(self.db, self.ctx)
        detalle["entrega"] = caja.format_entrega_corta(caja.entrega_de_sesion(orden.sesion_mesa_id)) if orden.canal == "domicilio" else None
        return self.tools.output(200, "Tirilla de la orden.", detalle)

    def get_table(self, mesa_id, lock=False):
        mesa = self.querys.get_own(MesaModel, mesa_id, "mesa", lock=lock)
        if mesa.tipo == "externa":
            if not {"ordenes.crear_externa", "ordenes.agregar_items", "ordenes.ver"} & self.ctx.get("permisos", set()) \
                    and not self.ctx.get("publico"):
                raise CustomException("No tiene permiso para órdenes externas.", 403)
        elif not self.ctx.get("publico"):
            check_zone_scope(self.ctx, mesa.zona_id)
        return mesa

    def price_items(self, items: list, zona):
        """ Valida los ítems contra la carta de la zona y calcula los precios en el servidor:
            nunca se confía en el precio que manda el cliente (doc 15, sección 4). """

        if not items:
            raise CustomException("La orden no tiene ítems.")
        if len(items) > MAX_ITEMS:
            raise CustomException(f"Una orden puede tener máximo {MAX_ITEMS} líneas.")
        carta_id = HorarioQuerys(self.db, self.ctx).current_menu(zona)
        if not carta_id:
            raise CustomException("La zona no tiene carta asignada.", 409)

        ids = [int(item["producto_id"]) for item in items]
        disponibles = self.querys.products_in_menu(carta_id, ids)
        grupos = ModificadorQuerys(self.db, self.ctx).for_products(ids)
        puntos_activos = self.querys.active_points()
        impuestos = self.tax_resolver()

        lineas, fuera_de_carta, agotados = [], [], []
        for item in items:
            cantidad = int(item["cantidad"])
            if cantidad <= 0 or cantidad > MAX_CANTIDAD:
                raise CustomException(f"La cantidad debe estar entre 1 y {MAX_CANTIDAD}.")
            encontrado = disponibles.get(int(item["producto_id"]))
            if not encontrado:
                fuera_de_carta.append(int(item["producto_id"]))
                continue
            producto, categoria = encontrado
            if producto.agotado:
                agotados.append(producto.nombre)
                continue
            modificadores = self.validate_modifiers(producto, grupos.get(producto.id, []), item.get("modificadores"))
            unitario = producto.precio + sum(m["precio_extra"] for m in modificadores)
            lineas.append({
                "producto": producto,
                "cantidad": cantidad,
                "nota": clean_text(item.get("nota")),
                "precio_unitario": unitario,
                "total": unitario * cantidad,
                "modificadores": modificadores,
                "punto_produccion_id": self.resolve_destination(producto, categoria, zona, puntos_activos),
                **impuestos(producto, categoria),
            })

        if fuera_de_carta:
            nombres = self.querys.get_product_names(fuera_de_carta)
            lista = ", ".join(nombres.get(i, f"producto {i}") for i in fuera_de_carta)
            raise CustomException(f"No están disponibles en esta carta: {lista}.", 409)
        if agotados:
            raise CustomException(f"Agotado: {', '.join(agotados)}. Retíralo de la orden para continuar.", 409)
        return lineas

    def tax_resolver(self):
        """ Impuesto del producto, si no el de su categoría, si no el impuesto por defecto,
            con la tasa vigente hoy (RG-06). Sin impuesto configurado la línea va sin impuesto. """
        facturacion = FacturacionQuerys(self.db, self.ctx)
        tarifas = facturacion.tarifas_vigentes(dia_actual(self.ctx))
        defecto = facturacion.impuesto_defecto()

        def resolver(producto, categoria):
            impuesto_id = producto.impuesto_id or categoria.impuesto_id or (defecto.id if defecto else None)
            if impuesto_id not in tarifas:
                return {"impuesto_id": None, "impuesto_porcentaje": None}
            return {"impuesto_id": impuesto_id, "impuesto_porcentaje": tarifas[impuesto_id]}
        return resolver

    def validate_modifiers(self, producto, grupos: list, elegidas):
        """ Las opciones deben ser de los grupos del producto y respetar mínimos y máximos
            (RN-PRO-03). El precio extra sale del servidor, como el del producto. """
        opciones = {}
        for grupo in grupos:
            for opcion in grupo["opciones"]:
                opciones[opcion["id"]] = (grupo, opcion)

        ids = list(dict.fromkeys(int(o) for o in elegidas or []))
        if any(opcion_id not in opciones for opcion_id in ids):
            raise CustomException(f"Una de las opciones elegidas ya no está disponible para {producto.nombre}.", 409)

        for grupo in grupos:
            cantidad = sum(1 for opcion_id in ids if opciones[opcion_id][0]["id"] == grupo["id"])
            if cantidad < grupo["minimo"]:
                raise CustomException(f"Elige {grupo['nombre'].lower()} para {producto.nombre}.")
            if cantidad > grupo["maximo"]:
                raise CustomException(f"En {grupo['nombre'].lower()} de {producto.nombre} se pueden elegir máximo {grupo['maximo']}.")

        return [{
            "opcion_id": opcion_id,
            "grupo_nombre": opciones[opcion_id][0]["nombre"],
            "nombre": opciones[opcion_id][1]["nombre"],
            "precio_extra": opciones[opcion_id][1]["precio_extra"],
        } for opcion_id in ids]

    # Producto -> categoría -> zona -> despacho directo (doc 19, sección 3)
    def resolve_destination(self, producto, categoria, zona, puntos_activos: set):
        for punto_id in [producto.punto_produccion_id, categoria.punto_produccion_id, zona.punto_produccion_id]:
            if punto_id and punto_id in puntos_activos:
                return punto_id
        return None

    def insert_items(self, orden, lineas: list, estado: str, lote: str):
        nuevos = []
        for linea in lineas:
            producto = linea["producto"]
            item_id = self.querys.insert_data(OrdenItemModel, {
                "orden_id": orden.id,
                "producto_id": producto.id,
                "nombre_producto": producto.nombre,
                "precio_unitario": linea["precio_unitario"],
                "cantidad": linea["cantidad"],
                "total": linea["total"],
                "impuesto_id": linea["impuesto_id"],
                "impuesto_porcentaje": linea["impuesto_porcentaje"],
                "nota": linea["nota"],
                "punto_produccion_id": linea["punto_produccion_id"],
                "estado": estado,
                "lote": lote,
            }, commit=False)
            for modificador in linea["modificadores"]:
                self.querys.insert_data(OrdenItemModificadorModel, {**modificador, "orden_item_id": item_id}, commit=False)
            item = self.db.get(OrdenItemModel, item_id)
            self.querys.add_history(item, None, estado)
            nuevos.append(item)
        return nuevos

    def split_into_commands(self, orden, items: list, es_adicion: bool):
        """ Una comanda por punto de producción (doc 19, sección 4).
            Lo que no tiene punto se despacha de inmediato (bebida de nevera). """
        grupos = {}
        for item in items:
            if item.punto_produccion_id is None:
                self.querys.transition(item, DESPACHADO, "Despacho directo")
            else:
                grupos.setdefault(item.punto_produccion_id, []).append(item)

        for punto_id, propios in grupos.items():
            comanda_id = self.querys.insert_data(ComandaModel, {
                "orden_id": orden.id,
                "punto_produccion_id": punto_id,
                "es_adicion": es_adicion,
            }, commit=False)
            for item in propios:
                item.comanda_id = comanda_id
        self.db.flush()
        return list(grupos)

    # Cada orden externa tiene su propia sesión: se cierra cuando ya no queda nada pendiente
    def check_approver(self, orden):
        """ Quien despacha domicilios confirma los pedidos web de domicilio, no las órdenes de las mesas """
        if "ordenes.aprobar_qr" not in self.ctx["permisos"] and orden.canal != "domicilio":
            raise CustomException("Solo el mesero o el administrador aprueban las órdenes de QR.", 403)

    def close_external_session(self, orden):
        sesion = self.db.get(SesionMesaModel, orden.sesion_mesa_id)
        if not sesion.es_externa or sesion.estado != "abierta" or self.caja_activa():
            return
        self.db.flush()
        if not any(i.estado in PENDIENTES_DE_ENTREGA for i in self.querys.items_of(orden.id)):
            self.mesas.close_session(sesion, self.ctx.get("usuario_id"))

    def caja_activa(self):
        modulos = self.ctx.get("modulos")
        if modulos is None:
            modulos, _ = modulos_activos(self.db, self.querys.restaurante())
        return "caja" in modulos

    def notify(self, orden, puntos: list, tipo: str):
        realtime.publish(orden.restaurante_id, channels_for(orden.zona_id, puntos), {
            "tipo": tipo,
            "orden_id": orden.id,
            "numero": orden.numero,
            "mesa_id": orden.mesa_id,
            "zona_id": orden.zona_id,
        })
