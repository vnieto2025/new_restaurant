from datetime import timedelta
from decimal import Decimal
from sqlalchemy import func
from Utils.tools import Tools, CustomException, now
from Utils.estados import NUEVO, EN_PROCESO, DESPACHADO, CANCELADO
from Querys.base import Querys
from Models.restaurante_model import RestauranteModel
from Models.orden_model import OrdenModel
from Models.orden_item_model import OrdenItemModel
from Models.comanda_model import ComandaModel
from Models.punto_produccion_model import PuntoProduccionModel
from Models.sesion_mesa_model import SesionMesaModel
from Models.mesa_model import MesaModel
from Models.historial_estado_model import HistorialEstadoModel
from Models.usuario_model import UsuarioModel
from Models.turno_caja_model import TurnoCajaModel
from Models.insumo_model import InsumoModel
from Models.resolucion_model import ResolucionModel
from Class.Caja import dia_actual

# Alertas del dueño (doc 27, sección 2): módulo que las habilita, umbral sugerido y en qué se mide (RN-DAS-03)
ALERTAS = {
    "comandas_demoradas": {"nombre": "Comandas demoradas", "modulo": "pedidos", "umbral": 20, "unidad": "minutos",
                           "ayuda": "Si el punto de producción no tiene tiempo objetivo"},
    "listos_sin_entregar": {"nombre": "Platos listos sin entregar", "modulo": "pedidos", "umbral": 10, "unidad": "minutos"},
    "mesas_abiertas": {"nombre": "Mesas abiertas mucho tiempo", "modulo": "base", "umbral": 3, "unidad": "horas"},
    "cancelaciones": {"nombre": "Muchas cancelaciones de una persona", "modulo": "base", "umbral": 5, "unidad": "ítems en la jornada"},
    "diferencia_caja": {"nombre": "Diferencias de caja", "modulo": "caja", "umbral": 5000, "unidad": "pesos"},
    "inventario": {"nombre": "Stock bajo o negativo", "modulo": "inventario", "umbral": None, "unidad": None},
    "resoluciones": {"nombre": "Numeración por agotarse o vencerse", "modulo": "caja", "umbral": 15, "unidad": "días antes de vencer"},
}
MAX_DETALLE = 5


def pesos(valor: int) -> str:
    return f"{'-' if valor < 0 else ''}$ {abs(int(valor)):,}".replace(",", ".")


def config_de(restaurante) -> dict:
    config = restaurante.alertas or {}
    return {"umbrales": config.get("umbrales") or {}, "apagadas": config.get("apagadas") or [],
            "silenciadas": config.get("silenciadas") or {}}


class Alertas:
    """ Lo que necesita atención ahora (doc 27): se calcula al consultar, con umbrales configurables;
        cada alerta se puede apagar o silenciar por el resto de la jornada (RN-DAS-03). """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = Querys(db, ctx)
        self.hoy = dia_actual(ctx)

    def restaurante(self, lock=False):
        query = self.db.query(RestauranteModel).filter(RestauranteModel.id == self.ctx["restaurante_id"])
        return (query.with_for_update() if lock else query).one()

    def disponibles(self):
        modulos = self.ctx.get("modulos", set())
        return [codigo for codigo, alerta in ALERTAS.items() if alerta["modulo"] in modulos]

    # ---- Consulta ----

    def list(self, data: dict = None):
        config = config_de(self.restaurante())
        result = []
        for codigo in self.disponibles():
            if codigo in config["apagadas"]:
                continue
            umbral = config["umbrales"].get(codigo, ALERTAS[codigo]["umbral"])
            alerta = getattr(self, f"alerta_{codigo}")(umbral)
            if alerta:
                silenciada = config["silenciadas"].get(codigo) == str(self.hoy)
                result.append({"codigo": codigo, "nombre": ALERTAS[codigo]["nombre"], "silenciada": silenciada, **alerta})
        return self.tools.output(200, "Alertas." if result else "Sin alertas.", result)

    def alerta_comandas_demoradas(self, umbral):
        filas = self.querys.scoped(ComandaModel).join(OrdenItemModel, OrdenItemModel.comanda_id == ComandaModel.id).join(
            PuntoProduccionModel, PuntoProduccionModel.id == ComandaModel.punto_produccion_id).filter(
            OrdenItemModel.estado.in_([NUEVO, EN_PROCESO])).with_entities(
            ComandaModel.id, ComandaModel.creado_en, PuntoProduccionModel.nombre, PuntoProduccionModel.tiempo_objetivo).distinct().all()
        ahora = now()
        demoradas = {}
        for _, creado_en, punto, objetivo in filas:
            if ahora - creado_en > timedelta(minutes=objetivo or umbral):
                demoradas.setdefault(punto, []).append(int((ahora - creado_en).total_seconds() // 60))
        if not demoradas:
            return None
        total = sum(len(v) for v in demoradas.values())
        return {"nivel": "urgente", "cantidad": total, "enlace": "admin",
                "titulo": f"{total} {'comanda lleva' if total == 1 else 'comandas llevan'} más del tiempo objetivo",
                "detalle": [f"{punto}: {len(minutos)}, la más antigua de {max(minutos)} min" for punto, minutos in demoradas.items()]}

    def alerta_listos_sin_entregar(self, umbral):
        limite = now() - timedelta(minutes=umbral)
        filas = self.querys.scoped(OrdenItemModel).join(OrdenModel, OrdenModel.id == OrdenItemModel.orden_id).join(
            MesaModel, MesaModel.id == OrdenModel.mesa_id).filter(
            OrdenItemModel.estado == DESPACHADO, OrdenItemModel.actualizado_en < limite,
            OrdenItemModel.combo_item_id.is_(None) | OrdenItemModel.es_combo.is_(True)).with_entities(
            MesaModel.nombre, func.count(OrdenItemModel.id)).group_by(MesaModel.nombre).all()
        if not filas:
            return None
        total = sum(int(n) for _, n in filas)
        return {"nivel": "urgente", "cantidad": total, "enlace": "admin",
                "titulo": f"{total} {'plato listo lleva' if total == 1 else 'platos listos llevan'} más de {umbral} min sin entregarse",
                "detalle": [f"{mesa}: {n}" for mesa, n in filas][:MAX_DETALLE]}

    def alerta_mesas_abiertas(self, umbral):
        limite = now() - timedelta(hours=umbral)
        filas = self.querys.scoped(SesionMesaModel).join(MesaModel, MesaModel.id == SesionMesaModel.mesa_id).filter(
            SesionMesaModel.estado == "abierta", SesionMesaModel.abierta_en < limite).with_entities(
            MesaModel.nombre, SesionMesaModel.abierta_en).order_by(SesionMesaModel.abierta_en).all()
        if not filas:
            return None
        ahora = now()
        return {"nivel": "aviso", "cantidad": len(filas), "enlace": "caja" if "caja" in self.ctx.get("modulos", set()) else "admin",
                "titulo": f"{len(filas)} {'mesa o pedido lleva' if len(filas) == 1 else 'mesas o pedidos llevan'} más de {umbral} h abiertos",
                "detalle": [f"{mesa}: {int((ahora - abierta).total_seconds() // 3600)} h" for mesa, abierta in filas][:MAX_DETALLE]}

    def alerta_cancelaciones(self, umbral):
        filas = self.querys.scoped(HistorialEstadoModel).join(OrdenItemModel, OrdenItemModel.id == HistorialEstadoModel.orden_item_id).join(
            OrdenModel, OrdenModel.id == OrdenItemModel.orden_id).filter(
            HistorialEstadoModel.estado_nuevo == CANCELADO, HistorialEstadoModel.usuario_id.isnot(None),
            OrdenModel.jornada == self.hoy, OrdenItemModel.combo_item_id.is_(None)).with_entities(
            HistorialEstadoModel.usuario_id, func.count(func.distinct(OrdenItemModel.id))).group_by(HistorialEstadoModel.usuario_id).all()
        altas = [(usuario_id, int(n)) for usuario_id, n in filas if int(n) >= umbral]
        if not altas:
            return None
        nombres = {u.id: u.nombre for u in self.db.query(UsuarioModel).filter(UsuarioModel.id.in_([u for u, _ in altas]))}
        return {"nivel": "aviso", "cantidad": len(altas), "enlace": "admin-reportes",
                "titulo": f"{len(altas)} {'persona canceló' if len(altas) == 1 else 'personas cancelaron'} {umbral} o más ítems hoy",
                "detalle": [f"{nombres.get(u, '?')}: {n} ítems" for u, n in sorted(altas, key=lambda x: -x[1])][:MAX_DETALLE]}

    def alerta_diferencia_caja(self, umbral):
        turnos = self.querys.scoped(TurnoCajaModel).filter(
            TurnoCajaModel.jornada == self.hoy, TurnoCajaModel.estado == "cerrado",
            func.abs(TurnoCajaModel.diferencia) >= max(int(umbral), 1)).all()
        if not turnos:
            return None
        nombres = {u.id: u.nombre for u in self.db.query(UsuarioModel).filter(UsuarioModel.id.in_([t.usuario_id for t in turnos]))}
        return {"nivel": "urgente", "cantidad": len(turnos), "enlace": "caja",
                "titulo": f"{len(turnos)} {'turno cerró' if len(turnos) == 1 else 'turnos cerraron'} con diferencia de caja",
                "detalle": [f"{nombres.get(t.usuario_id, '?')}: {'sobraron' if t.diferencia > 0 else 'faltaron'} {pesos(abs(t.diferencia))}"
                            for t in turnos][:MAX_DETALLE]}

    def alerta_inventario(self, umbral):
        insumos = self.querys.scoped(InsumoModel).filter(InsumoModel.activo.is_(True), (InsumoModel.stock < 0) | (
            (InsumoModel.stock_minimo > 0) & (InsumoModel.stock <= InsumoModel.stock_minimo))).order_by(InsumoModel.nombre).all()
        if not insumos:
            return None
        negativos = [i for i in insumos if i.stock < 0]
        fmt = lambda v: f"{Decimal(v).normalize():f}".replace(".", ",")
        return {"nivel": "urgente" if negativos else "aviso", "cantidad": len(insumos), "enlace": "admin-inventario",
                "titulo": (f"{len(negativos)} con stock negativo y " if negativos else "")
                          + f"{len(insumos) - len(negativos)} {'insumo' if len(insumos) - len(negativos) == 1 else 'insumos'} bajo el mínimo",
                "detalle": [f"{i.nombre}: {fmt(i.stock)} {i.unidad} (mínimo {fmt(i.stock_minimo)})" for i in insumos][:MAX_DETALLE]}

    def alerta_resoluciones(self, umbral):
        avisos = []
        for r in self.querys.scoped(ResolucionModel).filter(ResolucionModel.activo.is_(True)).all():
            restantes = r.hasta - (r.ultimo if r.ultimo is not None else r.desde - 1)
            nombre = f"{r.prefijo or 'Sin prefijo'} ({r.tipo_documento})"
            if restantes <= r.alerta_restantes:
                avisos.append(f"{nombre}: quedan {restantes} números")
            if r.vigente_hasta and r.vigente_hasta <= self.hoy + timedelta(days=int(umbral)):
                dias = (r.vigente_hasta - self.hoy).days
                avisos.append(f"{nombre}: {'vencida' if dias < 0 else f'vence en {dias} días'}")
        if not avisos:
            return None
        return {"nivel": "aviso", "cantidad": len(avisos), "enlace": "admin-facturacion",
                "titulo": "Pide a la DIAN una nueva numeración", "detalle": avisos[:MAX_DETALLE]}

    # ---- Configuración ----

    def silence(self, data: dict):
        codigo = data["codigo"]
        if codigo not in self.disponibles():
            raise CustomException("Esa alerta no existe.")
        restaurante = self.restaurante(lock=True)
        config = config_de(restaurante)
        # Solo se guardan las de hoy: las de jornadas pasadas ya no silencian nada
        silenciadas = {k: v for k, v in config["silenciadas"].items() if v == str(self.hoy)}
        if data.get("silenciar", True) is False:
            silenciadas.pop(codigo, None)
        else:
            silenciadas[codigo] = str(self.hoy)
        restaurante.alertas = {**config, "silenciadas": silenciadas}
        self.querys.audit("alerta_silenciada" if codigo in silenciadas else "alerta_reactivada", "restaurante", restaurante.id,
                          despues={"alerta": codigo, "jornada": str(self.hoy)}, commit=False)
        self.db.commit()
        return self.tools.output(200, "Alerta silenciada por hoy." if codigo in silenciadas else "Alerta activa de nuevo.")

    def get_config(self, data: dict = None):
        config = config_de(self.restaurante())
        return self.tools.output(200, "Configuración de alertas.", [{
            "codigo": codigo, "nombre": ALERTAS[codigo]["nombre"], "unidad": ALERTAS[codigo]["unidad"],
            "ayuda": ALERTAS[codigo].get("ayuda"), "umbral_sugerido": ALERTAS[codigo]["umbral"],
            "umbral": config["umbrales"].get(codigo, ALERTAS[codigo]["umbral"]), "activa": codigo not in config["apagadas"],
        } for codigo in self.disponibles()])

    def save_config(self, data: dict):
        disponibles = self.disponibles()
        umbrales, apagadas = {}, []
        for fila in data["alertas"]:
            codigo = fila.get("codigo")
            if codigo not in disponibles:
                raise CustomException("Esa alerta no existe.")
            if fila.get("activa") is False:
                apagadas.append(codigo)
            if ALERTAS[codigo]["umbral"] is not None and fila.get("umbral") not in (None, ""):
                try:
                    umbral = int(fila["umbral"])
                except (TypeError, ValueError):
                    raise CustomException(f"El umbral de «{ALERTAS[codigo]['nombre']}» debe ser un número entero.")
                if umbral < 1 or umbral > 10_000_000:
                    raise CustomException(f"El umbral de «{ALERTAS[codigo]['nombre']}» no es válido.")
                if umbral != ALERTAS[codigo]["umbral"]:
                    umbrales[codigo] = umbral
        restaurante = self.restaurante(lock=True)
        antes = config_de(restaurante)
        restaurante.alertas = {**antes, "umbrales": umbrales, "apagadas": apagadas}
        self.querys.audit("alertas_configuradas", "restaurante", restaurante.id,
                          antes={"umbrales": antes["umbrales"], "apagadas": antes["apagadas"]},
                          despues={"umbrales": umbrales, "apagadas": apagadas}, commit=False)
        self.db.commit()
        return self.get_config()
