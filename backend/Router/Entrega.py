from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Entrega import Entrega
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

entrega_router = APIRouter()

@entrega_router.post('/entrega/list', tags=["Domicilios"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["domicilios.despachar", "domicilios.entregar"], modulo="domicilios"))])
@http_decorator
def list_deliveries(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Entrega(db, request.state.user).list(data)
    return response

@entrega_router.post('/entrega/asignar', tags=["Domicilios"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["domicilios.despachar"], modulo="domicilios"))])
@http_decorator
def assign(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Entrega(db, request.state.user).assign(data)
    return response

@entrega_router.post('/entrega/salir', tags=["Domicilios"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["domicilios.despachar", "domicilios.entregar"], modulo="domicilios"))])
@http_decorator
def depart(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Entrega(db, request.state.user).depart(data)
    return response

@entrega_router.post('/entrega/entregar', tags=["Domicilios"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["domicilios.despachar", "domicilios.entregar"], modulo="domicilios"))])
@http_decorator
def deliver(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Entrega(db, request.state.user).deliver(data)
    return response

@entrega_router.post('/entrega/fallida', tags=["Domicilios"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["domicilios.despachar", "domicilios.entregar"], modulo="domicilios"))])
@http_decorator
def fail(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Entrega(db, request.state.user).fail(data)
    return response

@entrega_router.post('/entrega/por_rendir', tags=["Domicilios"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["domicilios.rendir"], modulo="domicilios"))])
@http_decorator
def cash_pending(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Entrega(db, request.state.user).cash_pending(data)
    return response

@entrega_router.post('/entrega/rendir', tags=["Domicilios"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["domicilios.rendir"], modulo="domicilios"))])
@http_decorator
def render(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Entrega(db, request.state.user).render(data)
    return response
