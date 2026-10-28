from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Mesa import Mesa
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

mesa_router = APIRouter()

@mesa_router.post('/mesa/list', tags=["Mesa"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["ordenes.ver", "estructura.gestionar"], modulo="pedidos"))])
@http_decorator
def list_tables(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Mesa(db, request.state.user).list(data)
    return response

@mesa_router.post('/mesa/create', tags=["Mesa"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["estructura.gestionar"], modulo="pedidos"))])
@http_decorator
def create(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Mesa(db, request.state.user).create(data)
    return response

@mesa_router.post('/mesa/create_lote', tags=["Mesa"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["estructura.gestionar"], modulo="pedidos"))])
@http_decorator
def create_batch(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Mesa(db, request.state.user).create_batch(data)
    return response

@mesa_router.post('/mesa/update', tags=["Mesa"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["estructura.gestionar"], modulo="pedidos"))])
@http_decorator
def update(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Mesa(db, request.state.user).update(data)
    return response

@mesa_router.post('/mesa/change_status', tags=["Mesa"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["estructura.gestionar"], modulo="pedidos"))])
@http_decorator
def change_status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Mesa(db, request.state.user).change_status(data)
    return response

@mesa_router.post('/mesa/abrir', tags=["Mesa"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["ordenes.crear_mesa"], modulo="pedidos"))])
@http_decorator
def open_table(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Mesa(db, request.state.user).open(data)
    return response

@mesa_router.post('/mesa/cerrar', tags=["Mesa"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["mesas.cerrar"], modulo="pedidos"))])
@http_decorator
def close_table(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Mesa(db, request.state.user).close(data)
    return response

@mesa_router.post('/mesa/trasladar', tags=["Mesa"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["mesas.trasladar"], modulo="pedidos"))])
@http_decorator
def move_table(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Mesa(db, request.state.user).move(data)
    return response

@mesa_router.post('/mesa/unir', tags=["Mesa"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["mesas.trasladar"], modulo="pedidos"))])
@http_decorator
def merge_tables(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Mesa(db, request.state.user).merge(data)
    return response

@mesa_router.post('/mesa/reasignar', tags=["Mesa"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["mesas.reasignar"], modulo="pedidos"))])
@http_decorator
def reassign_table(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Mesa(db, request.state.user).reassign(data)
    return response

@mesa_router.post('/mesa/meseros', tags=["Mesa"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["mesas.reasignar"], modulo="pedidos"))])
@http_decorator
def waiters(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Mesa(db, request.state.user).waiters(data)
    return response
