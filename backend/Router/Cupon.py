from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Cupon import Cupon
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

cupon_router = APIRouter()

@cupon_router.post('/cupon/list', tags=["Cupones"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["cupones.gestionar", "cupones.ver"], modulo="fidelizacion"))])
@http_decorator
def list_coupons(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cupon(db, request.state.user).list(data)
    return response

@cupon_router.post('/cupon/get', tags=["Cupones"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["cupones.gestionar", "cupones.ver"], modulo="fidelizacion"))])
@http_decorator
def get(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cupon(db, request.state.user).get(data)
    return response

@cupon_router.post('/cupon/save', tags=["Cupones"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["cupones.gestionar"], modulo="fidelizacion"))])
@http_decorator
def save(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cupon(db, request.state.user).save(data)
    return response

@cupon_router.post('/cupon/change_status', tags=["Cupones"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["cupones.gestionar"], modulo="fidelizacion"))])
@http_decorator
def change_status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cupon(db, request.state.user).change_status(data)
    return response

@cupon_router.post('/cupon/enviar', tags=["Cupones"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["cupones.gestionar"], modulo="fidelizacion"))])
@http_decorator
def send(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cupon(db, request.state.user).send(data)
    return response

@cupon_router.post('/cupon/resultados', tags=["Cupones"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["cupones.ver"], modulo="fidelizacion"))])
@http_decorator
def results(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cupon(db, request.state.user).results(data)
    return response

@cupon_router.post('/cupon/aplicar', tags=["Cupones"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["cupones.aplicar"], modulo="fidelizacion"))])
@http_decorator
def apply(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cupon(db, request.state.user).apply(data)
    return response

@cupon_router.post('/cupon/quitar', tags=["Cupones"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["cupones.aplicar"], modulo="fidelizacion"))])
@http_decorator
def remove(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cupon(db, request.state.user).remove(data)
    return response

@cupon_router.post('/cupon/cliente', tags=["Cupones"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["cupones.aplicar"], modulo="fidelizacion"))])
@http_decorator
def identify(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cupon(db, request.state.user).identify(data)
    return response
