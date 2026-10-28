from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Zona import Zona
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

zona_router = APIRouter()

@zona_router.post('/zona/list', tags=["Zona"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["ordenes.ver", "estructura.gestionar"], modulo="pedidos"))])
@http_decorator
def list_zones(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Zona(db, request.state.user).list(data)
    return response

@zona_router.post('/zona/create', tags=["Zona"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["estructura.gestionar"], modulo="pedidos"))])
@http_decorator
def create(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Zona(db, request.state.user).create(data)
    return response

@zona_router.post('/zona/update', tags=["Zona"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["estructura.gestionar"], modulo="pedidos"))])
@http_decorator
def update(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Zona(db, request.state.user).update(data)
    return response

@zona_router.post('/zona/change_status', tags=["Zona"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["estructura.gestionar"], modulo="pedidos"))])
@http_decorator
def change_status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Zona(db, request.state.user).change_status(data)
    return response
