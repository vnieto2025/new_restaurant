"""
Avisos en tiempo real por WebSocket (doc 04, sección 4; ADR-004).

Los eventos son avisos, no la fuente de verdad: quien los recibe vuelve a pedir el estado a la API.
Se publican después de guardar en la base de datos.

Canales (siempre dentro de un restaurante):
    r<id>:punto:<id>   pantalla de un punto de producción
    r<id>:zona:<id>    tablets de una zona
    r<id>:ordenes      vista general (admin, caja, mostrador)
"""
import asyncio
import json
import threading
from collections import defaultdict


class Realtime:

    def __init__(self):
        self.channels = defaultdict(set)
        self.loop = None
        self.lock = threading.Lock()

    # Se llama al arrancar la app para poder publicar desde los endpoints síncronos
    def bind_loop(self, loop):
        self.loop = loop

    def subscribe(self, websocket, channels: list):
        with self.lock:
            for channel in channels:
                self.channels[channel].add(websocket)

    def unsubscribe(self, websocket):
        with self.lock:
            for channel in list(self.channels):
                self.channels[channel].discard(websocket)
                if not self.channels[channel]:
                    del self.channels[channel]

    async def _send(self, channel: str, message: str):
        with self.lock:
            sockets = list(self.channels.get(channel, []))
        for websocket in sockets:
            try:
                await websocket.send_text(message)
            except Exception:
                self.unsubscribe(websocket)

    # Publica un evento en varios canales. Se puede llamar desde un hilo (endpoints def).
    def publish(self, restaurante_id, channels: list, event: dict):
        if not self.loop:
            return
        message = json.dumps(event, default=str)
        for channel in set(channels):
            full = f"r{restaurante_id}:{channel}"
            try:
                running = asyncio.get_running_loop()
            except RuntimeError:
                running = None
            if running is self.loop:
                self.loop.create_task(self._send(full, message))
            else:
                asyncio.run_coroutine_threadsafe(self._send(full, message), self.loop)


realtime = Realtime()


# Canales a los que avisa un cambio en una orden
def channels_for(zona_id=None, puntos: list = None):
    channels = ["ordenes"]
    if zona_id:
        channels.append(f"zona:{zona_id}")
    for punto in puntos or []:
        if punto:
            channels.append(f"punto:{punto}")
    return channels
