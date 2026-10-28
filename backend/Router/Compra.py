from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Compra import Compra
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

compra_router = APIRouter()

@compra_router.post('/compra/list', tags=["Compras"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["compras.ver", "compras.registrar", "compras.recibir"], modulo="inventario"))])
@http_decorator
def list_purchases(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Compra(db, request.state.user).list(data)
    return response

@compra_router.post('/compra/get', tags=["Compras"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["compras.ver", "compras.registrar", "compras.recibir"], modulo="inventario"))])
@http_decorator
def get(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Compra(db, request.state.user).get(data)
    return response

@compra_router.post('/compra/create', tags=["Compras"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["compras.registrar"], modulo="inventario"))])
@http_decorator
def create(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Compra(db, request.state.user).create(data)
    return response

@compra_router.post('/compra/update', tags=["Compras"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["compras.registrar"], modulo="inventario"))])
@http_decorator
def update(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Compra(db, request.state.user).update(data)
    return response

@compra_router.post('/compra/solicitar', tags=["Compras"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["compras.registrar"], modulo="inventario"))])
@http_decorator
def request(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Compra(db, request.state.user).request(data)
    return response

@compra_router.post('/compra/recibir', tags=["Compras"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["compras.recibir"], modulo="inventario"))])
@http_decorator
def receive(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Compra(db, request.state.user).receive(data)
    return response

@compra_router.post('/compra/rapida', tags=["Compras"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["compras.registrar"], modulo="inventario"))])
@http_decorator
def quick(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Compra(db, request.state.user).quick(data)
    return response

@compra_router.post('/compra/cerrar', tags=["Compras"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["compras.registrar"], modulo="inventario"))])
@http_decorator
def close(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Compra(db, request.state.user).close(data)
    return response

@compra_router.post('/compra/anular', tags=["Compras"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["compras.anular"], modulo="inventario"))])
@http_decorator
def void(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Compra(db, request.state.user).void(data)
    return response

@compra_router.post('/compra/sugerida', tags=["Compras"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["compras.registrar", "compras.ver"], modulo="inventario"))])
@http_decorator
def suggested(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Compra(db, request.state.user).suggested(data)
    return response
