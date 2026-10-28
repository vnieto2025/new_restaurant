from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Impuesto import Impuesto
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

impuesto_router = APIRouter()

@impuesto_router.post('/impuesto/list', tags=["Impuestos"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["impuestos.configurar", "catalogo.gestionar"]))])
@http_decorator
def list_taxes(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Impuesto(db, request.state.user).list(data)
    return response

@impuesto_router.post('/impuesto/create', tags=["Impuestos"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["impuestos.configurar"]))])
@http_decorator
def create(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Impuesto(db, request.state.user).create(data)
    return response

@impuesto_router.post('/impuesto/update', tags=["Impuestos"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["impuestos.configurar"]))])
@http_decorator
def update(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Impuesto(db, request.state.user).update(data)
    return response

@impuesto_router.post('/impuesto/change_status', tags=["Impuestos"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["impuestos.configurar"]))])
@http_decorator
def change_status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Impuesto(db, request.state.user).change_status(data)
    return response

@impuesto_router.post('/impuesto/tarifa', tags=["Impuestos"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["impuestos.configurar"]))])
@http_decorator
def set_rate(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Impuesto(db, request.state.user).set_rate(data)
    return response
