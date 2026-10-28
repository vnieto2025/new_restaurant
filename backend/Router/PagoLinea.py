from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.PagoLinea import PagoLinea
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

pago_linea_router = APIRouter()

@pago_linea_router.post('/pago_linea/config/get', tags=["Pagos en línea"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["pagos_linea.configurar"], modulo="pagos_linea"))])
@http_decorator
def get_config(request: Request, db: Session = Depends(get_db)):
    response = PagoLinea(db, request.state.user).get_config()
    return response

@pago_linea_router.post('/pago_linea/config/save', tags=["Pagos en línea"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["pagos_linea.configurar"], modulo="pagos_linea"))])
@http_decorator
def save_config(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = PagoLinea(db, request.state.user).save_config(data)
    return response

@pago_linea_router.post('/pago_linea/enlace', tags=["Pagos en línea"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["pagos_linea.cobrar"], modulo="pagos_linea"))])
@http_decorator
def link(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = PagoLinea(db, request.state.user).link(data)
    return response

@pago_linea_router.post('/pago_linea/list', tags=["Pagos en línea"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["pagos_linea.conciliar", "pagos_linea.reembolsar"], modulo="pagos_linea"))])
@http_decorator
def list_payments(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = PagoLinea(db, request.state.user).list(data)
    return response

@pago_linea_router.post('/pago_linea/reembolsar', tags=["Pagos en línea"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["pagos_linea.reembolsar"], modulo="pagos_linea"))])
@http_decorator
def refund(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = PagoLinea(db, request.state.user).refund(data)
    return response

@pago_linea_router.post('/pago_linea/conciliar', tags=["Pagos en línea"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["pagos_linea.conciliar"], modulo="pagos_linea"))])
@http_decorator
def reconcile(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = PagoLinea(db, request.state.user).reconcile(data)
    return response
