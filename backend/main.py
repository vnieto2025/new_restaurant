import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import Models  # noqa: F401 (registra todas las tablas; el esquema lo crean las migraciones con seed.py)
from Middleware.get_json import JSONMiddleware
from Utils.realtime import realtime
from Router.Auth import auth_router
from Router.Plataforma import plataforma_router
from Router.Restaurante import restaurante_router
from Router.Usuario import usuario_router
from Router.Zona import zona_router
from Router.Mesa import mesa_router
from Router.PuntoProduccion import punto_produccion_router
from Router.Categoria import categoria_router
from Router.Producto import producto_router
from Router.Carta import carta_router
from Router.Orden import orden_router
from Router.Cocina import cocina_router
from Router.Publico import publico_router
from Router.Auditoria import auditoria_router
from Router.Modificador import modificador_router
from Router.Caja import caja_router
from Router.Cuenta import cuenta_router
from Router.Dispositivo import dispositivo_router
from Router.Horario import horario_router
from Router.Reporte import reporte_router
from Router.Exportacion import exportacion_router
from Router.Cliente import cliente_router
from Router.Impuesto import impuesto_router
from Router.Resolucion import resolucion_router
from Router.Facturacion import facturacion_router
from Router.Documento import documento_router
from Router.Insumo import insumo_router
from Router.Proveedor import proveedor_router
from Router.Compra import compra_router
from Router.Domicilio import domicilio_router
from Router.Entrega import entrega_router
from Router.Notificacion import notificacion_router
from Router.PagoLinea import pago_linea_router
from Router.PagoPublico import pago_publico_router
from Router.Cupon import cupon_router
from Router.Liquidacion import liquidacion_router
from Router.Pos import pos_router
from Router.Receta import receta_router
from Router.Inventario import inventario_router
from Router.Conteo import conteo_router
from Utils.emision import cola_emision
from Utils.mensajeria import cola_mensajes
from Router.Realtime import realtime_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Los endpoints son síncronos (corren en hilos); para avisar por WebSocket necesitan el loop
    realtime.bind_loop(asyncio.get_running_loop())
    # Cola de emisión de documentos de venta (doc 21, sección 6)
    cola_emision.start()
    cola_mensajes.start()
    yield
    await cola_emision.stop()
    await cola_mensajes.stop()


app = FastAPI(lifespan=lifespan)
app.title = "RestaurantERP"
app.version = "0.1.0"

app.add_middleware(JSONMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(auth_router)
app.include_router(plataforma_router)
app.include_router(restaurante_router)
app.include_router(usuario_router)
app.include_router(zona_router)
app.include_router(mesa_router)
app.include_router(punto_produccion_router)
app.include_router(categoria_router)
app.include_router(producto_router)
app.include_router(carta_router)
app.include_router(orden_router)
app.include_router(cocina_router)
app.include_router(publico_router)
app.include_router(auditoria_router)
app.include_router(modificador_router)
app.include_router(caja_router)
app.include_router(cuenta_router)
app.include_router(dispositivo_router)
app.include_router(horario_router)
app.include_router(reporte_router)
app.include_router(exportacion_router)
app.include_router(cliente_router)
app.include_router(impuesto_router)
app.include_router(resolucion_router)
app.include_router(facturacion_router)
app.include_router(documento_router)
app.include_router(insumo_router)
app.include_router(receta_router)
app.include_router(inventario_router)
app.include_router(conteo_router)
app.include_router(proveedor_router)
app.include_router(compra_router)
app.include_router(domicilio_router)
app.include_router(entrega_router)
app.include_router(notificacion_router)
app.include_router(pago_linea_router)
app.include_router(pago_publico_router)
app.include_router(cupon_router)
app.include_router(liquidacion_router)
app.include_router(pos_router)
app.include_router(realtime_router)

if __name__ == "__main__":
    import os
    import uvicorn
    # En producción no se define APP_ENV, así que por defecto arranca sin --reload.
    # En local, .env trae APP_ENV=development.
    is_dev = os.getenv("APP_ENV", "production") == "development"
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=is_dev)
