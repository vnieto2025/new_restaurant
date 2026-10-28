from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Resolucion import Resolucion
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

resolucion_router = APIRouter()

@resolucion_router.post('/resolucion/list', tags=["Facturación"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["facturacion.configurar", "facturacion.ver"], modulo="facturacion"))])
@http_decorator
def list_ranges(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Resolucion(db, request.state.user).list(data)
    return response

@resolucion_router.post('/resolucion/create', tags=["Facturación"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["facturacion.configurar"], modulo="facturacion"))])
@http_decorator
def create(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Resolucion(db, request.state.user).create(data)
    return response

@resolucion_router.post('/resolucion/update', tags=["Facturación"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["facturacion.configurar"], modulo="facturacion"))])
@http_decorator
def update(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Resolucion(db, request.state.user).update(data)
    return response

@resolucion_router.post('/resolucion/change_status', tags=["Facturación"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["facturacion.configurar"], modulo="facturacion"))])
@http_decorator
def change_status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Resolucion(db, request.state.user).change_status(data)
    return response
