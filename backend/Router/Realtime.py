from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from starlette.concurrency import run_in_threadpool
from Config.db import SessionLocal
from Utils.jwt_manager import validate_token
from Utils.contexto import cargar_contexto
from Utils.realtime import realtime
from Models.zona_model import ZonaModel
from Models.punto_produccion_model import PuntoProduccionModel

realtime_router = APIRouter()


def allowed_channels(ctx: dict, requested: list):
    """ Un cliente solo se suscribe a lo que tiene permiso de ver (doc 31, sección 6):
        su zona, su punto de producción o la vista general si atiende todo el restaurante. """
    # Con solo caja (plan Gestión, ADR-007) también hay cuentas que seguir en vivo
    if not {"pedidos", "caja"} & ctx.get("modulos", set()):
        return []

    restaurante_id = ctx["restaurante_id"]
    db = SessionLocal()
    try:
        zonas = {z.id for z in db.query(ZonaModel).filter(ZonaModel.restaurante_id == restaurante_id).all()}
        puntos = {p.id for p in db.query(PuntoProduccionModel).filter(
            PuntoProduccionModel.restaurante_id == restaurante_id).all()}
    finally:
        db.close()

    permitidos = []
    for channel in requested:
        tipo, _, valor = channel.partition(":")
        # Quien despacha o lleva domicilios oye los avisos de entregas, que van por el canal general; caja oye las cuentas
        if tipo == "ordenes" and ctx.get("zonas") is None and \
                {"ordenes.ver", "domicilios.despachar", "domicilios.entregar", "caja.ver", "caja.cobrar",
                 "caja.cobrar_externas"} & ctx["permisos"]:
            permitidos.append("ordenes")
        elif tipo == "zona" and valor.isdigit() and int(valor) in zonas and "ordenes.ver" in ctx["permisos"]:
            if ctx.get("zonas") is None or int(valor) in ctx["zonas"]:
                permitidos.append(channel)
        elif tipo == "punto" and valor.isdigit() and int(valor) in puntos and "cocina.operar" in ctx["permisos"]:
            if ctx.get("puntos") is None or int(valor) in ctx["puntos"]:
                permitidos.append(channel)
    return [f"r{restaurante_id}:{channel}" for channel in permitidos]


# ws://host/ws?token=<jwt>&canales=punto:3,zona:2,ordenes
@realtime_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = "", canales: str = ""):
    try:
        token_data = validate_token(token)
        ctx = await run_in_threadpool(cargar_contexto, token_data, None, websocket.headers.get("user-agent"))
        channels = await run_in_threadpool(allowed_channels, ctx, [c.strip() for c in canales.split(",") if c.strip()])
    except HTTPException:
        await websocket.close(code=4401)
        return

    if not channels:
        await websocket.close(code=4403)
        return

    await websocket.accept()
    realtime.subscribe(websocket, channels)
    await websocket.send_json({"tipo": "conectado", "canales": [c.split(":", 1)[1] for c in channels]})
    try:
        while True:
            # El cliente envía "ping" para mantener viva la conexión
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        realtime.unsubscribe(websocket)
