from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from Utils.decorator import http_decorator
from Class.PagoPublico import PagoPublico
from Class.PagoLinea import registrar_webhook
from Config.db import get_db
from sqlalchemy.orm import Session

pago_publico_router = APIRouter()

# Rutas sin sesión para que el cliente pague desde su celular (doc 20A)


def ip_de(request: Request):
    return request.client.host if request.client else None


@pago_publico_router.post('/publico/pago/cuenta', tags=["Pagos en línea"], response_model=dict)
@http_decorator
def account(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    return PagoPublico(db, ip_de(request)).info(data)

@pago_publico_router.post('/publico/pago/cupon', tags=["Pagos en línea"], response_model=dict)
@http_decorator
def coupon(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    return PagoPublico(db, ip_de(request)).apply_coupon(data)

@pago_publico_router.post('/publico/pago/crear', tags=["Pagos en línea"], response_model=dict)
@http_decorator
def create(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    return PagoPublico(db, ip_de(request)).create(data)

@pago_publico_router.post('/publico/pago/estado', tags=["Pagos en línea"], response_model=dict)
@http_decorator
def status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    return PagoPublico(db, ip_de(request)).status(data)

@pago_publico_router.post('/publico/pasarela/ver', tags=["Pagos en línea"], response_model=dict)
@http_decorator
def simulated_view(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    return PagoPublico(db, ip_de(request)).simulated_view(data)

@pago_publico_router.post('/publico/pasarela/responder', tags=["Pagos en línea"], response_model=dict)
@http_decorator
def simulated_answer(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    return PagoPublico(db, ip_de(request)).simulated_answer(data)


# Aviso de la pasarela: sin sesión ni encabezado accept; la autenticidad la da la firma (RN-API-06)
@pago_publico_router.post('/webhook/pagos/{pasarela}', tags=["Pagos en línea"])
async def webhook(pasarela: str, request: Request, db: Session = Depends(get_db)):
    cuerpo = await request.body()
    codigo, mensaje = registrar_webhook(db, pasarela, cuerpo, dict(request.headers))
    return JSONResponse(status_code=codigo, content={"message": mensaje})
