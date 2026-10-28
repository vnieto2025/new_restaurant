from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Orden import Orden
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

orden_router = APIRouter()

@orden_router.post('/orden/carta', tags=["Orden"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["ordenes.crear_mesa", "ordenes.crear_externa", "ordenes.agregar_items"], modulo="pedidos"))])
@http_decorator
def menu(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Orden(db, request.state.user).menu(data)
    return response

@orden_router.post('/orden/create', tags=["Orden"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["ordenes.crear_mesa", "ordenes.crear_externa"], modulo="pedidos"))])
@http_decorator
def create(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Orden(db, request.state.user).create(data)
    return response

@orden_router.post('/orden/agregar_items', tags=["Orden"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["ordenes.agregar_items"], modulo="pedidos"))])
@http_decorator
def add_items(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Orden(db, request.state.user).add_items(data)
    return response

@orden_router.post('/orden/get', tags=["Orden"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["ordenes.ver"], modulo="pedidos"))])
@http_decorator
def get(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Orden(db, request.state.user).get(data)
    return response

@orden_router.post('/orden/list', tags=["Orden"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["ordenes.ver"], modulo="pedidos"))])
@http_decorator
def list_orders(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Orden(db, request.state.user).list(data)
    return response

@orden_router.post('/orden/aprobar', tags=["Orden"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["ordenes.aprobar_qr"], modulo="pedidos"))])
@http_decorator
def approve(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Orden(db, request.state.user).approve(data)
    return response

@orden_router.post('/orden/rechazar', tags=["Orden"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["ordenes.aprobar_qr"], modulo="pedidos"))])
@http_decorator
def reject(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Orden(db, request.state.user).reject(data)
    return response

@orden_router.post('/orden/cancelar_item', tags=["Orden"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["ordenes.cancelar_nuevo", "ordenes.cancelar_en_proceso"], modulo="pedidos"))])
@http_decorator
def cancel_item(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Orden(db, request.state.user).cancel_item(data)
    return response

@orden_router.post('/orden/entregar', tags=["Orden"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["ordenes.entregar"], modulo="pedidos"))])
@http_decorator
def deliver(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Orden(db, request.state.user).deliver(data)
    return response

@orden_router.post('/orden/tirilla', tags=["Orden"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["ordenes.ver"], modulo="pedidos"))])
@http_decorator
def ticket(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Orden(db, request.state.user).ticket(data)
    return response
