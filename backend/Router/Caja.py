from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Caja import Caja
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

caja_router = APIRouter()

@caja_router.post('/caja/estado', tags=["Caja"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["caja.ver", "caja.cobrar", "caja.cobrar_externas", "caja.turno"], modulo="caja"))])
@http_decorator
def status(request: Request, db: Session = Depends(get_db)):
    response = Caja(db, request.state.user).status()
    return response

@caja_router.post('/caja/turno/abrir', tags=["Caja"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["caja.turno"], modulo="caja"))])
@http_decorator
def open_shift(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Caja(db, request.state.user).open_shift(data)
    return response

@caja_router.post('/caja/turno/cerrar', tags=["Caja"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["caja.turno"], modulo="caja"))])
@http_decorator
def close_shift(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Caja(db, request.state.user).close_shift(data)
    return response

@caja_router.post('/caja/turno/get', tags=["Caja"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["caja.ver", "caja.turno"], modulo="caja"))])
@http_decorator
def get_shift(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Caja(db, request.state.user).get_shift(data)
    return response

@caja_router.post('/caja/turno/list', tags=["Caja"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["caja.ver", "caja.turno"], modulo="caja"))])
@http_decorator
def list_shifts(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Caja(db, request.state.user).list_shifts(data)
    return response

@caja_router.post('/caja/movimiento/create', tags=["Caja"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["caja.movimientos"], modulo="caja"))])
@http_decorator
def movement(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Caja(db, request.state.user).movement(data)
    return response

@caja_router.post('/caja/medio_pago/list', tags=["Caja"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["caja.ver", "caja.medios"], modulo="caja"))])
@http_decorator
def list_payment_methods(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Caja(db, request.state.user).list_payment_methods(data)
    return response

@caja_router.post('/caja/medio_pago/save', tags=["Caja"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["caja.medios"], modulo="caja"))])
@http_decorator
def save_payment_method(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Caja(db, request.state.user).save_payment_method(data)
    return response

@caja_router.post('/caja/jornada/estado', tags=["Caja"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["caja.ver", "caja.cerrar_jornada"], modulo="caja"))])
@http_decorator
def day_status(request: Request, db: Session = Depends(get_db)):
    response = Caja(db, request.state.user).day_status()
    return response

@caja_router.post('/caja/jornada/cerrar', tags=["Caja"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["caja.cerrar_jornada"], modulo="caja"))])
@http_decorator
def close_day(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Caja(db, request.state.user).close_day(data)
    return response
