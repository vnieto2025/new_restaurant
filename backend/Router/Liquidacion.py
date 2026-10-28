from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Liquidacion import Liquidacion
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

liquidacion_router = APIRouter()

@liquidacion_router.post('/liquidacion/config/get', tags=["Liquidaciones"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["liquidaciones.gestionar", "domicilios.liquidar"]))])
@http_decorator
def get_config(request: Request, db: Session = Depends(get_db)):
    response = Liquidacion(db, request.state.user).get_config()
    return response

@liquidacion_router.post('/liquidacion/config/save', tags=["Liquidaciones"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["liquidaciones.gestionar", "domicilios.liquidar"]))])
@http_decorator
def save_config(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Liquidacion(db, request.state.user).save_config(data)
    return response

@liquidacion_router.post('/liquidacion/list', tags=["Liquidaciones"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["liquidaciones.gestionar", "domicilios.liquidar"]))])
@http_decorator
def list_settlements(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Liquidacion(db, request.state.user).list(data)
    return response

@liquidacion_router.post('/liquidacion/periodo', tags=["Liquidaciones"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["liquidaciones.gestionar", "domicilios.liquidar"]))])
@http_decorator
def preview(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Liquidacion(db, request.state.user).preview(data)
    return response

@liquidacion_router.post('/liquidacion/calcular', tags=["Liquidaciones"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["liquidaciones.gestionar", "domicilios.liquidar"]))])
@http_decorator
def calculate(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Liquidacion(db, request.state.user).calculate(data)
    return response

@liquidacion_router.post('/liquidacion/get', tags=["Liquidaciones"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["liquidaciones.gestionar", "domicilios.liquidar"]))])
@http_decorator
def get(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Liquidacion(db, request.state.user).get(data)
    return response

@liquidacion_router.post('/liquidacion/linea', tags=["Liquidaciones"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["liquidaciones.gestionar", "domicilios.liquidar"]))])
@http_decorator
def edit_line(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Liquidacion(db, request.state.user).edit_line(data)
    return response

@liquidacion_router.post('/liquidacion/ajustar', tags=["Liquidaciones"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["liquidaciones.gestionar", "domicilios.liquidar"]))])
@http_decorator
def adjust(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Liquidacion(db, request.state.user).adjust(data)
    return response

@liquidacion_router.post('/liquidacion/descartar', tags=["Liquidaciones"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["liquidaciones.gestionar", "domicilios.liquidar"]))])
@http_decorator
def discard(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Liquidacion(db, request.state.user).discard(data)
    return response

@liquidacion_router.post('/liquidacion/aprobar', tags=["Liquidaciones"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["liquidaciones.gestionar", "domicilios.liquidar"]))])
@http_decorator
def approve(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Liquidacion(db, request.state.user).approve(data)
    return response

@liquidacion_router.post('/liquidacion/pagar', tags=["Liquidaciones"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["liquidaciones.gestionar", "domicilios.liquidar"]))])
@http_decorator
def pay_line(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Liquidacion(db, request.state.user).pay_line(data)
    return response

@liquidacion_router.post('/liquidacion/mias', tags=["Liquidaciones"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["liquidaciones.ver_propia"]))])
@http_decorator
def mine(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Liquidacion(db, request.state.user).mine(data)
    return response
