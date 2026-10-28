import secrets
from Utils.tools import Tools, CustomException, clean_text, jornada
from Utils.estados import ENTREGADO, CANCELADO
from Querys.caja import CajaQuerys
from Querys.mesa import MesaQuerys
from Querys.carta import CartaQuerys
from Querys.horario import HorarioQuerys
from Models.orden_model import OrdenModel
from Models.cuenta_model import CuentaModel
from Models.mesa_model import MesaModel
from Models.zona_model import ZonaModel
from Models.sesion_mesa_model import SesionMesaModel
from Models.cliente_model import ClienteModel
from Class.Caja import dia_actual
from Class.Cuenta import Cuenta
from Class.Orden import Orden

CANAL_POS = "pos"


class Pos:
    """ Venta directa en caja (doc 20, sección 9; ADR-007): se eligen productos y se cobra, sin mesas, cocina ni
        comandas. No depende del módulo de pedidos: crea una orden con los ítems ya entregados en la mesa externa
        y abre su cuenta, así facturación, inventario, cupones y reportes funcionan igual que con pedidos. """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = CajaQuerys(db, ctx)
        self.mesas = MesaQuerys(db, ctx)

    def menu(self):
        mesa, zona = self.counter()
        categorias = CartaQuerys(self.db, self.ctx).menu(HorarioQuerys(self.db, self.ctx).current_menu(zona))
        return self.tools.output(200, "Carta para vender.", {"categorias": categorias})

    def sell(self, data: dict):
        """ Registra la venta y deja su cuenta abierta para cobrarla con el panel de siempre (pago mixto,
            cupón, factura). Idempotente por clave: un doble toque no crea dos ventas. """
        clave = str(data["clave_idempotencia"]).strip()
        existente = self.querys.get_orden_by_clave(clave)
        if existente:
            cuenta = self.querys.get_cuenta_by_sesion(existente.sesion_mesa_id)
            return self.tools.output(200, "Esta venta ya estaba registrada.", Cuenta(self.db, self.ctx).format(cuenta))

        restaurante = self.querys.restaurante()
        if restaurante.estado in ["cerrado", "inactivo"]:
            raise CustomException("El restaurante está cerrado.", 409)
        dia = dia_actual(self.ctx)
        if self.querys.jornada_cerrada(dia):
            raise CustomException("La jornada de hoy ya se cerró: no se reciben más ventas hoy.", 409)
        if not self.querys.get_turno_abierto(self.querys.get_caja().id):
            raise CustomException("No hay un turno de caja abierto. Ábrelo antes de vender.", 409)

        mesa, zona = self.counter(lock=True)
        ordenes = Orden(self.db, self.ctx)
        lineas = ordenes.price_items(data["items"], zona)
        cliente = self.querys.get_own(ClienteModel, data["cliente_id"], "cliente") if data.get("cliente_id") else None
        nombre = clean_text(data.get("cliente_nombre")) or (cliente.nombre if cliente else None)

        sesion = self.mesas.open_session(mesa)
        orden_id = self.querys.insert_data(OrdenModel, {
            "numero": self.querys.next_number(dia), "jornada": dia, "canal": CANAL_POS, "zona_id": zona.id,
            "mesa_id": mesa.id, "sesion_mesa_id": sesion.id, "creado_por": self.ctx.get("usuario_id"),
            "cliente_id": cliente.id if cliente else None, "cliente_nombre": nombre,
            "cliente_telefono": cliente.telefono if cliente else None, "clave_idempotencia": clave,
            "token_seguimiento": secrets.token_urlsafe(24), "moneda": restaurante.moneda,
            "total": sum(l["total"] for l in lineas),
        }, commit=False)
        orden = self.db.get(OrdenModel, orden_id)
        # Se entrega en el mostrador al cobrar: no pasa por producción
        items = ordenes.insert_items(orden, lineas, ENTREGADO, clave)
        if "inventario" in self.ctx.get("modulos", set()):
            from Querys.inventario import al_cambiar_estado
            for item in items:
                al_cambiar_estado(self.db, self.ctx, item, ENTREGADO)

        self.querys.insert_data(CuentaModel, {"sesion_mesa_id": sesion.id, "mesa_id": mesa.id, "zona_id": zona.id,
                                              "cliente_id": cliente.id if cliente else None}, commit=False)
        cuenta = self.querys.get_cuenta_by_sesion(sesion.id, lock=True)
        cuentas = Cuenta(self.db, self.ctx)
        cuentas.refresh(cuenta)
        self.db.commit()
        cuentas.notify(cuenta, "cuenta.nueva")
        return self.tools.output(201, f"Venta {orden.numero:03d} lista para cobrar.", cuentas.format(cuenta))

    def cancel(self, data: dict):
        """ Deshacer una venta directa que no se cobró: el producto no salió, así que el inventario vuelve
            sin registrar merma. Con pagos, primero se anulan en caja. """
        cuenta = self.querys.get_own(CuentaModel, data["cuenta_id"], "cuenta", lock=True)
        if cuenta.estado != "abierta":
            raise CustomException("La venta ya no está abierta. Si se cobró, anula la cuenta.", 409)
        if cuenta.pagado:
            raise CustomException("La venta tiene pagos: anúlalos antes de cancelarla.", 409)
        ordenes = self.querys.ordenes_de_sesion(cuenta.sesion_mesa_id)
        if not ordenes or any(o.canal != CANAL_POS for o in ordenes):
            raise CustomException("Solo se cancelan así las ventas directas.", 409)
        motivo = clean_text(data.get("motivo")) or "Venta directa cancelada antes de cobrar"

        from Querys.inventario import InventarioQuerys
        inventario = InventarioQuerys(self.db, self.ctx)
        for orden in ordenes:
            for item in self.querys.items_of(orden.id, lock=True):
                if item.estado == CANCELADO:
                    continue
                if item.inventario_descontado:
                    for consumo in inventario.consumos_de_item(item.id):
                        inventario.mover(consumo.insumo_id, "reverso_consumo", -consumo.cantidad,
                                         costo_unitario=consumo.costo_unitario, motivo="Venta directa cancelada",
                                         orden_item_id=item.id)
                    item.inventario_descontado = False
                anterior = item.estado
                item.estado, item.motivo_cancelacion, item.tipo_cancelacion = CANCELADO, motivo[:200], "cancelacion"
                self.querys.add_history(item, anterior, CANCELADO, motivo)
            self.querys.recalc_total(orden)

        from Class.Cupon import Cupon
        Cupon(self.db, self.ctx).on_void(cuenta, motivo)
        cuenta.estado, cuenta.anulada_motivo, cuenta.anulada_por = "anulada", motivo[:200], self.ctx.get("usuario_id")
        cuenta.jornada = cuenta.jornada or dia_actual(self.ctx)
        sesion = self.db.get(SesionMesaModel, cuenta.sesion_mesa_id)
        if sesion.estado == "abierta":
            self.mesas.close_session(sesion, self.ctx.get("usuario_id"))
        self.querys.audit("venta_directa_cancelada", "cuenta", cuenta.id, motivo=motivo, commit=False)
        self.db.commit()
        Cuenta(self.db, self.ctx).notify(cuenta, "cuenta.anulada")
        return self.tools.output(200, "Venta cancelada.", {})

    def counter(self, lock=False):
        """ La mesa externa del restaurante (RN-RES-02) y su zona de mostrador, con su carta """
        mesa = self.querys.scoped(MesaModel).filter(MesaModel.tipo == "externa")
        mesa = (mesa.with_for_update() if lock else mesa).first()
        if not mesa:
            raise CustomException("El restaurante no tiene mostrador configurado.", 409)
        zona = self.querys.get_own(ZonaModel, mesa.zona_id, "zona")
        return mesa, zona
