from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Cliente import Cliente
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

cliente_router = APIRouter()

@cliente_router.post('/cliente/buscar', tags=["Cliente"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["clientes.ver"]))])
@http_decorator
def search(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cliente(db, request.state.user).search(data)
    return response

@cliente_router.post('/cliente/list', tags=["Cliente"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["clientes.gestionar"]))])
@http_decorator
def list_customers(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cliente(db, request.state.user).list(data)
    return response

@cliente_router.post('/cliente/get', tags=["Cliente"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["clientes.ver"]))])
@http_decorator
def get(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cliente(db, request.state.user).get(data)
    return response

@cliente_router.post('/cliente/create', tags=["Cliente"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["clientes.ver"]))])
@http_decorator
def create(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cliente(db, request.state.user).create(data)
    return response

@cliente_router.post('/cliente/update', tags=["Cliente"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["clientes.gestionar"]))])
@http_decorator
def update(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cliente(db, request.state.user).update(data)
    return response

@cliente_router.post('/cliente/change_status', tags=["Cliente"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["clientes.gestionar"]))])
@http_decorator
def change_status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cliente(db, request.state.user).change_status(data)
    return response

@cliente_router.post('/cliente/direccion/save', tags=["Cliente"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["clientes.ver"]))])
@http_decorator
def save_address(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cliente(db, request.state.user).save_address(data)
    return response

@cliente_router.post('/cliente/direccion/delete', tags=["Cliente"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["clientes.ver"]))])
@http_decorator
def delete_address(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cliente(db, request.state.user).delete_address(data)
    return response

@cliente_router.post('/cliente/exportar', tags=["Cliente"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["clientes.exportar"]))])
@http_decorator
def export(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cliente(db, request.state.user).export(data)
    return response

@cliente_router.post('/cliente/anonimizar', tags=["Cliente"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["clientes.gestionar"]))])
@http_decorator
def anonymize(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cliente(db, request.state.user).anonymize(data)
    return response
