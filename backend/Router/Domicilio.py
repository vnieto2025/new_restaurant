from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Domicilio import Domicilio
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

domicilio_router = APIRouter()

@domicilio_router.post('/domicilio/zona/list', tags=["Domicilios"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["domicilios.gestionar", "domicilios.despachar", "ordenes.crear_externa"], modulo="domicilios"))])
@http_decorator
def list_zones(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Domicilio(db, request.state.user).list_zones(data)
    return response

@domicilio_router.post('/domicilio/zona/save', tags=["Domicilios"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["domicilios.gestionar"], modulo="domicilios"))])
@http_decorator
def save_zone(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Domicilio(db, request.state.user).save_zone(data)
    return response

@domicilio_router.post('/domicilio/domiciliario/list', tags=["Domicilios"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["domicilios.gestionar", "domicilios.despachar"], modulo="domicilios"))])
@http_decorator
def list_couriers(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Domicilio(db, request.state.user).list_couriers(data)
    return response

@domicilio_router.post('/domicilio/domiciliario/save', tags=["Domicilios"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["domicilios.gestionar"], modulo="domicilios"))])
@http_decorator
def save_courier(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Domicilio(db, request.state.user).save_courier(data)
    return response

@domicilio_router.post('/domicilio/domiciliario/change_status', tags=["Domicilios"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["domicilios.gestionar"], modulo="domicilios"))])
@http_decorator
def change_courier_status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Domicilio(db, request.state.user).change_courier_status(data)
    return response
