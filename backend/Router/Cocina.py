from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Cocina import Cocina
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

cocina_router = APIRouter()

@cocina_router.post('/cocina/comandas', tags=["Cocina"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["cocina.operar"], modulo="pedidos"))])
@http_decorator
def commands(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cocina(db, request.state.user).commands(data)
    return response

@cocina_router.post('/cocina/abrir', tags=["Cocina"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["cocina.operar"], modulo="pedidos"))])
@http_decorator
def open_command(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cocina(db, request.state.user).open(data)
    return response

@cocina_router.post('/cocina/despachar', tags=["Cocina"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["cocina.operar"], modulo="pedidos"))])
@http_decorator
def dispatch(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cocina(db, request.state.user).dispatch(data)
    return response

@cocina_router.post('/cocina/reabrir', tags=["Cocina"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["cocina.reabrir"], modulo="pedidos"))])
@http_decorator
def reopen(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cocina(db, request.state.user).reopen(data)
    return response

@cocina_router.post('/cocina/agotado', tags=["Cocina"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["productos.agotar"], modulo="pedidos"))])
@http_decorator
def sold_out(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cocina(db, request.state.user).sold_out(data)
    return response

@cocina_router.post('/cocina/tirilla', tags=["Cocina"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["tirilla.imprimir"], modulo="pedidos"))])
@http_decorator
def ticket(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cocina(db, request.state.user).ticket(data)
    return response
