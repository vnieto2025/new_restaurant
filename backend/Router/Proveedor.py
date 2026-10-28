from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Proveedor import Proveedor
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

proveedor_router = APIRouter()

@proveedor_router.post('/proveedor/list', tags=["Compras"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["compras.ver", "compras.registrar", "proveedores.gestionar"], modulo="inventario"))])
@http_decorator
def list_suppliers(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Proveedor(db, request.state.user).list(data)
    return response

@proveedor_router.post('/proveedor/get', tags=["Compras"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["compras.ver", "proveedores.gestionar"], modulo="inventario"))])
@http_decorator
def get(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Proveedor(db, request.state.user).get(data)
    return response

@proveedor_router.post('/proveedor/create', tags=["Compras"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["proveedores.gestionar"], modulo="inventario"))])
@http_decorator
def create(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Proveedor(db, request.state.user).create(data)
    return response

@proveedor_router.post('/proveedor/update', tags=["Compras"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["proveedores.gestionar"], modulo="inventario"))])
@http_decorator
def update(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Proveedor(db, request.state.user).update(data)
    return response

@proveedor_router.post('/proveedor/change_status', tags=["Compras"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["proveedores.gestionar"], modulo="inventario"))])
@http_decorator
def change_status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Proveedor(db, request.state.user).change_status(data)
    return response

@proveedor_router.post('/proveedor/insumos', tags=["Compras"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["proveedores.gestionar"], modulo="inventario"))])
@http_decorator
def save_supplies(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Proveedor(db, request.state.user).save_supplies(data)
    return response
