from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Insumo import Insumo
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

insumo_router = APIRouter()

@insumo_router.post('/insumo/list', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.ver", "inventario.gestionar", "inventario.movimientos", "inventario.contar", "compras.registrar", "compras.recibir", "proveedores.gestionar"], modulo="inventario"))])
@http_decorator
def list_supplies(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Insumo(db, request.state.user).list(data)
    return response

@insumo_router.post('/insumo/create', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.gestionar"], modulo="inventario"))])
@http_decorator
def create(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Insumo(db, request.state.user).create(data)
    return response

@insumo_router.post('/insumo/update', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.gestionar"], modulo="inventario"))])
@http_decorator
def update(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Insumo(db, request.state.user).update(data)
    return response

@insumo_router.post('/insumo/change_status', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.gestionar"], modulo="inventario"))])
@http_decorator
def change_status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Insumo(db, request.state.user).change_status(data)
    return response
