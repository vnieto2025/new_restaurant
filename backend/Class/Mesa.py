from Utils.tools import Tools, CustomException, clean_text
from Utils.estados import PENDIENTE, NUEVO, EN_PROCESO, DESPACHADO, PENDIENTES_DE_ENTREGA
from Utils.realtime import realtime, channels_for
from Querys.mesa import MesaQuerys
from Models.mesa_model import MesaModel
from Models.zona_model import ZonaModel
from Class.Qr import Qr
from Querys.usuario import UsuarioQuerys

MAX_LOTE = 100

# Para el mesero, qué es lo más urgente de una mesa (doc 10, sección 2)
URGENCIA = [PENDIENTE, DESPACHADO, NUEVO, EN_PROCESO]


def check_zone_scope(ctx: dict, zona_id: int):
    """ Un mesero solo opera las mesas de sus zonas (doc 29, sección 4) """
    if ctx.get("zonas") is not None and zona_id not in ctx["zonas"]:
        raise CustomException("Esta mesa no pertenece a sus zonas.", 403)


class Mesa:

    def __init__(self, db, ctx: dict):
        self.ctx = ctx
        self.tools = Tools()
        self.querys = MesaQuerys(db, ctx)

    # Mesas con su estado operativo, derivado de la sesión abierta (doc 10, sección 2)
    def list(self, data: dict):

        administra = "estructura.gestionar" in self.ctx["permisos"]
        mesas = self.querys.list_mesas(
            zona_ids=self.ctx.get("zonas"),
            zona_id=data.get("zona_id"),
            incluir_externa=data.get("incluir_externa") is True,
            incluir_inactivas=data.get("todas") is True and administra,
        )
        sesiones = self.querys.open_sessions([m.id for m in mesas])
        items = self.querys.items_by_session([s.id for s in sesiones.values()])
        pedidas = self.querys.sessions_with_bill_requested([s.id for s in sesiones.values()])

        result = [self.format_mesa(mesa, sesiones.get(mesa.id), items, pedidas) for mesa in mesas]
        msg = "Listado de mesas." if result else "Aún no hay mesas."
        return self.tools.output(200, msg, result)

    def create(self, data: dict):

        zona = self.get_zone(data["zona_id"])
        nombre = clean_text(data["nombre"])
        if self.querys.name_exists(zona.id, nombre):
            raise CustomException(f"Ya existe la mesa {nombre} en la zona {zona.nombre}.")

        mesa_id = self.insert_table(zona, nombre, data.get("capacidad"))
        self.querys.commit()
        mesa = self.querys.get_own(MesaModel, mesa_id, "mesa")
        return self.tools.output(201, "Mesa creada.", self.format_mesa(mesa))

    # Crear mesas en lote: "Mesa 1" a "Mesa 10" (doc 10, sección 6)
    def create_batch(self, data: dict):

        zona = self.get_zone(data["zona_id"])
        desde, hasta = int(data["desde"]), int(data["hasta"])
        prefijo = clean_text(data.get("prefijo")) or "Mesa"
        if desde <= 0 or hasta < desde:
            raise CustomException("El rango de mesas no es válido.")
        if hasta - desde + 1 > MAX_LOTE:
            raise CustomException(f"Se pueden crear máximo {MAX_LOTE} mesas a la vez.")

        creadas, omitidas = 0, []
        for numero in range(desde, hasta + 1):
            nombre = f"{prefijo} {numero}"
            if self.querys.name_exists(zona.id, nombre):
                omitidas.append(nombre)
                continue
            self.insert_table(zona, nombre, data.get("capacidad"))
            creadas += 1
        self.querys.commit()

        msg = f"Se crearon {creadas} mesas."
        if omitidas:
            msg += f" Ya existían: {', '.join(omitidas)}."
        return self.tools.output(201, msg, {"creadas": creadas, "omitidas": omitidas})

    # Function for update a table. Cambiar de zona solo sin sesión abierta (doc 09, sección 7)
    def update(self, data: dict):

        mesa = self.querys.get_own(MesaModel, data["mesa_id"], "mesa")
        nombre = clean_text(data["nombre"])
        zona = self.get_zone(data.get("zona_id") or mesa.zona_id)

        if mesa.tipo == "externa" and zona.id != mesa.zona_id:
            raise CustomException("La mesa externa no cambia de zona.")
        if zona.id != mesa.zona_id and self.querys.get_open_session(mesa.id):
            raise CustomException("La mesa tiene una sesión abierta. Ciérrela antes de cambiarla de zona.")
        if self.querys.name_exists(zona.id, nombre, exclude_id=mesa.id):
            raise CustomException(f"Ya existe la mesa {nombre} en la zona {zona.nombre}.")

        if zona.id != mesa.zona_id:
            Qr(self.querys.db, self.ctx).move_to_zone(mesa.id, zona.id)

        capacidad = data.get("capacidad")
        mesa = self.querys.update_data(MesaModel, mesa.id, {
            "nombre": nombre,
            "zona_id": zona.id,
            "capacidad": int(capacidad) if capacidad not in [None, ""] else None,
        }, "mesa")
        return self.tools.output(200, "Mesa actualizada.", self.format_mesa(mesa))

    # Activar/desactivar (configuración) o bloquear/desbloquear (operación) una mesa
    def change_status(self, data: dict):

        mesa = self.querys.get_own(MesaModel, data["mesa_id"], "mesa")
        fields = {}
        if "activo" in data:
            fields["activo"] = data["activo"] is True
        if "bloqueada" in data:
            fields["bloqueada"] = data["bloqueada"] is True
        if not fields:
            raise CustomException("Indique si la mesa se activa o se bloquea.")

        if mesa.tipo == "externa" and (fields.get("activo") is False or fields.get("bloqueada")):
            raise CustomException("La mesa externa no se puede desactivar ni bloquear.")
        if fields.get("activo") is False and self.querys.get_open_session(mesa.id):
            raise CustomException("La mesa tiene una sesión abierta. Ciérrela antes de desactivarla.")

        self.querys.update_data(MesaModel, mesa.id, fields, "mesa", commit=False)
        self.querys.audit("mesa_estado", "mesa", mesa.id, despues=fields)
        realtime.publish(self.ctx["restaurante_id"], channels_for(mesa.zona_id),
                         {"tipo": "mesa.actualizada", "mesa_id": mesa.id})
        return self.tools.output(200, "Mesa actualizada.")

    # El mesero abre la mesa y queda como responsable (doc 10, sección 3)
    def open(self, data: dict):

        mesa = self.get_operable_table(data["mesa_id"])
        sesion = self.querys.get_open_session(mesa.id, lock=True)
        if sesion:
            if not sesion.mesero_id:
                sesion.mesero_id = self.ctx["usuario_id"]
                self.querys.commit()
            return self.tools.output(200, "La mesa ya estaba abierta.", {"sesion_mesa_id": sesion.id})

        sesion = self.querys.open_session(mesa, self.ctx["usuario_id"])
        self.querys.commit()
        realtime.publish(self.ctx["restaurante_id"], channels_for(mesa.zona_id),
                         {"tipo": "mesa.actualizada", "mesa_id": mesa.id})
        return self.tools.output(201, "Mesa abierta.", {"sesion_mesa_id": sesion.id})

    # Libera la mesa. Con caja (fase 1) esto ocurre al cobrar la cuenta.
    def close(self, data: dict):

        mesa = self.querys.get_own(MesaModel, data["mesa_id"], "mesa")
        check_zone_scope(self.ctx, mesa.zona_id)
        sesion = self.querys.get_open_session(mesa.id, lock=True)
        if not sesion:
            raise CustomException("La mesa no tiene una sesión abierta.")

        resumen = self.querys.items_by_session([sesion.id]).get(sesion.id, {"estados": [], "total": 0})
        pendientes = [e for e in resumen["estados"] if e in PENDIENTES_DE_ENTREGA]
        if pendientes:
            raise CustomException(
                f"La mesa tiene {len(pendientes)} ítems sin entregar. Entréguelos o cancélelos antes de cerrarla.", 409)

        if "caja" in self.ctx.get("modulos", set()) and resumen["total"] > 0:
            raise CustomException("La mesa tiene consumo: se libera al cobrar la cuenta en caja.", 409)

        self.querys.close_session(sesion, self.ctx["usuario_id"])
        self.querys.audit("mesa_cerrada", "sesion_mesa", sesion.id, despues={"total": resumen["total"]})
        realtime.publish(self.ctx["restaurante_id"], channels_for(mesa.zona_id),
                         {"tipo": "mesa.actualizada", "mesa_id": mesa.id})
        return self.tools.output(200, "Mesa cerrada. Queda libre.")

    # Mover la mesa a otra libre: órdenes, cuenta y comandas siguen a la nueva mesa (doc 10, sección 4)
    def move(self, data: dict):

        origen = self.querys.get_own(MesaModel, data["mesa_id"], "mesa", lock=True)
        destino = self.get_operable_table(data["destino_id"])
        if origen.id == destino.id or destino.tipo != "normal" or origen.tipo != "normal":
            raise CustomException("Elige otra mesa normal como destino.")
        sesion = self.querys.get_open_session(origen.id, lock=True)
        if not sesion:
            raise CustomException("La mesa de origen no tiene nada abierto.", 409)
        if self.querys.get_open_session(destino.id):
            raise CustomException(f"{destino.nombre} está ocupada. Para juntarlas usa Unir mesas.", 409)

        sesion.mesa_id, sesion.zona_id = destino.id, destino.zona_id
        for orden in self.querys.ordenes_de_sesion(sesion.id):
            orden.mesa_id, orden.zona_id = destino.id, destino.zona_id
        cuenta = self.querys.cuenta_de_sesion(sesion.id)
        if cuenta:
            cuenta.mesa_id, cuenta.zona_id = destino.id, destino.zona_id
        self.querys.audit("mesa_trasladada", "sesion_mesa", sesion.id,
                          antes={"mesa": origen.nombre}, despues={"mesa": destino.nombre}, commit=False)
        self.querys.commit()

        self.notify_tables(origen, destino, "mesa.trasladada")
        return self.tools.output(200, f"{origen.nombre} pasó a {destino.nombre}.", {"mesa_id": destino.id})

    # Unir mesas: las órdenes de las otras pasan a la sesión de la principal y se cobran juntas
    def merge(self, data: dict):

        principal = self.get_operable_table(data["mesa_id"])
        otras_ids = [int(m) for m in data["otras"] if int(m) != principal.id]
        if not otras_ids:
            raise CustomException("Elige al menos otra mesa para unir.")

        sesion = self.querys.get_open_session(principal.id, lock=True) or self.querys.open_session(principal, self.ctx["usuario_id"])
        unidas = []
        for mesa_id in otras_ids:
            mesa = self.querys.get_own(MesaModel, mesa_id, "mesa", lock=True)
            check_zone_scope(self.ctx, mesa.zona_id)
            otra = self.querys.get_open_session(mesa.id, lock=True)
            if not otra:
                raise CustomException(f"{mesa.nombre} no tiene nada abierto.", 409)
            cuenta = self.querys.cuenta_de_sesion(otra.id)
            if cuenta and cuenta.pagado:
                raise CustomException(f"{mesa.nombre} ya tiene pagos: cóbrala por separado.", 409)
            for orden in self.querys.ordenes_de_sesion(otra.id):
                orden.sesion_mesa_id = sesion.id
            if cuenta:
                # Una cuenta sin pagos solo es un cálculo: se reemplaza por la de la mesa principal
                self.querys.db.delete(cuenta)
            self.querys.close_session(otra, self.ctx["usuario_id"])
            unidas.append(mesa)

        self.querys.audit("mesas_unidas", "sesion_mesa", sesion.id,
                          despues={"principal": principal.nombre, "unidas": [m.nombre for m in unidas]}, commit=False)
        self.querys.commit()

        for mesa in unidas:
            self.notify_tables(mesa, principal, "mesa.unida")
        nombres = ", ".join(m.nombre for m in unidas)
        return self.tools.output(200, f"{nombres} se unió a {principal.nombre}. Se cobran juntas.", {"mesa_id": principal.id})

    # Cambiar el mesero responsable, por ejemplo al cambiar de turno (RN-MSR-05)
    def reassign(self, data: dict):

        mesa = self.querys.get_own(MesaModel, data["mesa_id"], "mesa")
        sesion = self.querys.get_open_session(mesa.id, lock=True)
        if not sesion:
            raise CustomException("La mesa no tiene nada abierto.", 409)
        mesero = next((m for m in self.waiters_for(mesa.zona_id) if m["id"] == int(data["mesero_id"])), None)
        if not mesero:
            raise CustomException("Ese mesero no atiende la zona de esta mesa.")

        antes = self.querys.get_usuario_nombre(sesion.mesero_id)
        sesion.mesero_id = mesero["id"]
        self.querys.audit("mesa_reasignada", "sesion_mesa", sesion.id, antes={"mesero": antes},
                          despues={"mesero": mesero["nombre"]}, commit=False)
        self.querys.commit()
        realtime.publish(self.ctx["restaurante_id"], channels_for(mesa.zona_id), {"tipo": "mesa.actualizada", "mesa_id": mesa.id})
        return self.tools.output(200, f"{mesa.nombre} queda a cargo de {mesero['nombre']}.")

    def waiters(self, data: dict):
        mesa = self.querys.get_own(MesaModel, data["mesa_id"], "mesa")
        return self.tools.output(200, "Meseros de la zona.", self.waiters_for(mesa.zona_id))

    # Meseros activos que pueden atender una zona
    def waiters_for(self, zona_id):
        usuarios = UsuarioQuerys(self.querys.db, self.ctx)
        result = []
        for usuario in usuarios.list_usuarios():
            roles = [r.codigo for r in usuarios.get_roles_usuario(usuario.id)]
            if "mesero" not in roles:
                continue
            zonas = usuarios.get_zonas_usuario(usuario.id)
            if zonas and zona_id not in zonas:
                continue
            result.append({"id": usuario.id, "nombre": usuario.nombre})
        return result

    def notify_tables(self, origen, destino, tipo):
        realtime.publish(self.ctx["restaurante_id"], channels_for(origen.zona_id) + [f"zona:{destino.zona_id}"],
                         {"tipo": tipo, "mesa_id": origen.id, "destino_id": destino.id})

    def get_zone(self, zona_id):
        zona = self.querys.get_own(ZonaModel, zona_id, "zona")
        if zona.es_mostrador:
            raise CustomException("La zona de mostrador solo tiene la mesa externa.")
        return zona

    # Mesa en la que se puede operar ahora: activa, no bloqueada y de las zonas del usuario
    def get_operable_table(self, mesa_id):
        mesa = self.querys.get_own(MesaModel, mesa_id, "mesa")
        check_zone_scope(self.ctx, mesa.zona_id)
        if not mesa.activo:
            raise CustomException("La mesa está desactivada.")
        if mesa.bloqueada:
            raise CustomException("La mesa está bloqueada y no recibe órdenes.")
        return mesa

    def insert_table(self, zona, nombre: str, capacidad=None):
        mesa_id = self.querys.insert_data(MesaModel, {
            "zona_id": zona.id,
            "nombre": nombre,
            "capacidad": int(capacidad) if capacidad not in [None, ""] else None,
            "orden": self.querys.max_orden(zona.id) + 1,
        }, commit=False)
        Qr(self.querys.db, self.ctx).create_for_mesa(mesa_id, zona.id)
        return mesa_id

    def format_mesa(self, mesa, sesion=None, items: dict = None, pedidas: set = None):

        resumen = (items or {}).get(sesion.id, {"estados": [], "total": 0}) if sesion else {"estados": [], "total": 0}
        estados = resumen["estados"]
        pendientes = [e for e in estados if e in PENDIENTES_DE_ENTREGA]

        if mesa.bloqueada:
            estado = "bloqueada"
        elif not sesion:
            estado = "libre"
        elif sesion.id in (pedidas or set()):
            estado = "cuenta_solicitada"
        elif pendientes:
            estado = "con_orden"
        else:
            estado = "ocupada"

        urgente = next((u for u in URGENCIA if u in pendientes), None)
        return {
            "id": mesa.id,
            "nombre": mesa.nombre,
            "zona_id": mesa.zona_id,
            "capacidad": mesa.capacidad,
            "tipo": mesa.tipo,
            "activo": mesa.activo,
            "bloqueada": mesa.bloqueada,
            "estado": estado,
            "estado_urgente": urgente,
            "items_pendientes": len(pendientes),
            "por_aprobar": estados.count(PENDIENTE),
            "listos": estados.count(DESPACHADO),
            "sesion": {
                "id": sesion.id,
                "abierta_en": sesion.abierta_en,
                "mesero_id": sesion.mesero_id,
                "mesero": self.querys.get_usuario_nombre(sesion.mesero_id),
                "total": resumen["total"],
            } if sesion else None,
        }
