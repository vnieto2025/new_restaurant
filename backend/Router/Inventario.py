from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Inventario import Inventario
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

inventario_router = APIRouter()

@inventario_router.post('/inventario/estado', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.ver", "inventario.movimientos", "inventario.contar"], modulo="inventario"))])
@http_decorator
def status(request: Request, db: Session = Depends(get_db)):
    response = Inventario(db, request.state.user).status()
    return response

@inventario_router.post('/inventario/movimientos', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.ver", "inventario.movimientos"], modulo="inventario"))])
@http_decorator
def movements(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Inventario(db, request.state.user).movements(data)
    return response

@inventario_router.post('/inventario/entrada', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.gestionar"], modulo="inventario"))])
@http_decorator
def entry(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Inventario(db, request.state.user).entry(data)
    return response

@inventario_router.post('/inventario/merma', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.movimientos"], modulo="inventario"))])
@http_decorator
def waste(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Inventario(db, request.state.user).waste(data)
    return response

@inventario_router.post('/inventario/ajuste', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.gestionar"], modulo="inventario"))])
@http_decorator
def adjust(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Inventario(db, request.state.user).adjust(data)
    return response

@inventario_router.post('/inventario/producir', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.movimientos"], modulo="inventario"))])
@http_decorator
def produce(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Inventario(db, request.state.user).produce(data)
    return response
