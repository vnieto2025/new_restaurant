"""
Proceso en segundo plano que envía los avisos automáticos por WhatsApp (doc 31B, sección 5).
Igual que la cola de emisión: busca los restaurantes con avisos pendientes y procesa cada uno con la
sesión de su empresa (Row Level Security). Un fallo de un restaurante no detiene a los demás.
"""
import asyncio
import os
import logging
from sqlalchemy import text
from Config.db import SessionLocal, admin_engine

INTERVALO = int(os.getenv("MENSAJES_INTERVALO", "15"))
log = logging.getLogger("mensajeria")


class ColaMensajes:

    def __init__(self):
        self.task = None
        self.evento = None
        self.bucle = None

    @property
    def habilitada(self):
        return os.getenv("MENSAJES_AUTOMATICOS", "1") == "1"

    def start(self):
        if not self.habilitada:
            return
        self.evento = asyncio.Event()
        self.bucle = asyncio.get_running_loop()
        self.task = asyncio.create_task(self.loop())

    async def stop(self):
        if self.task:
            self.task.cancel()

    # Llamado desde un endpoint después de confirmar la transacción: envía sin esperar el intervalo
    def despertar(self):
        if self.evento and self.bucle:
            self.bucle.call_soon_threadsafe(self.evento.set)

    async def loop(self):
        while True:
            try:
                await asyncio.to_thread(procesar_todo)
            except Exception as error:  # noqa: BLE001
                log.exception("Cola de mensajes: %s", error)
            try:
                await asyncio.wait_for(self.evento.wait(), timeout=INTERVALO)
            except asyncio.TimeoutError:
                pass
            self.evento.clear()


def restaurantes_con_pendientes():
    """ (empresa_id, restaurante_id) con avisos por enviar; solo identificadores, con la conexión administrativa """
    with admin_engine.connect() as conexion:
        return conexion.execute(text(
            "SELECT DISTINCT empresa_id, restaurante_id FROM notificacion "
            "WHERE estado = 'pendiente' AND (proximo_intento_en IS NULL OR proximo_intento_en <= now())"
        )).all()


def procesar_todo():
    from Class.Notificacion import Notificacion
    for empresa_id, restaurante_id in restaurantes_con_pendientes():
        db = SessionLocal()
        db.info["empresa_id"] = empresa_id
        try:
            ctx = {"empresa_id": empresa_id, "restaurante_id": restaurante_id, "usuario_id": None,
                   "modulos": set(), "permisos": set()}
            Notificacion(db, ctx).process()
        except Exception as error:  # noqa: BLE001
            db.rollback()
            log.exception("Avisos del restaurante %s: %s", restaurante_id, error)
        finally:
            db.close()


cola_mensajes = ColaMensajes()
