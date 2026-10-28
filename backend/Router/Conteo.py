from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Conteo import Conteo
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

conteo_router = APIRouter()

@conteo_router.post('/conteo/list', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.contar", "inventario.gestionar"], modulo="inventario"))])
@http_decorator
def list_counts(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Conteo(db, request.state.user).list(data)
    return response

@conteo_router.post('/conteo/create', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.contar"], modulo="inventario"))])
@http_decorator
def create(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Conteo(db, request.state.user).create(data)
    return response

@conteo_router.post('/conteo/get', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.contar", "inventario.gestionar"], modulo="inventario"))])
@http_decorator
def get(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Conteo(db, request.state.user).get(data)
    return response

@conteo_router.post('/conteo/save', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.contar"], modulo="inventario"))])
@http_decorator
def save(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Conteo(db, request.state.user).save(data)
    return response

@conteo_router.post('/conteo/aplicar', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.gestionar"], modulo="inventario"))])
@http_decorator
def apply(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Conteo(db, request.state.user).apply(data)
    return response

@conteo_router.post('/conteo/descartar', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.gestionar"], modulo="inventario"))])
@http_decorator
def discard(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Conteo(db, request.state.user).discard(data)
    return response
