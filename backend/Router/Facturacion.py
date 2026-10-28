from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Facturacion import Facturacion
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

facturacion_router = APIRouter()

@facturacion_router.post('/facturacion/config/get', tags=["Facturación"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["facturacion.configurar"], modulo="facturacion"))])
@http_decorator
def get_config(request: Request, db: Session = Depends(get_db)):
    response = Facturacion(db, request.state.user).get_config()
    return response

@facturacion_router.post('/facturacion/config/save', tags=["Facturación"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["facturacion.configurar"], modulo="facturacion"))])
@http_decorator
def save_config(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Facturacion(db, request.state.user).save_config(data)
    return response

@facturacion_router.post('/facturacion/estado', tags=["Facturación"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["facturacion.ver", "facturacion.configurar"], modulo="facturacion"))])
@http_decorator
def status(request: Request, db: Session = Depends(get_db)):
    response = Facturacion(db, request.state.user).status()
    return response
