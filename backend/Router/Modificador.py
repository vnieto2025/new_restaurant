from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Modificador import Modificador
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

modificador_router = APIRouter()

@modificador_router.post('/modificador/list', tags=["Modificador"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar"]))])
@http_decorator
def list_groups(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Modificador(db, request.state.user).list(data)
    return response

@modificador_router.post('/modificador/create', tags=["Modificador"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar"]))])
@http_decorator
def create(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Modificador(db, request.state.user).create(data)
    return response

@modificador_router.post('/modificador/update', tags=["Modificador"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar"]))])
@http_decorator
def update(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Modificador(db, request.state.user).update(data)
    return response

@modificador_router.post('/modificador/change_status', tags=["Modificador"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar"]))])
@http_decorator
def change_status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Modificador(db, request.state.user).change_status(data)
    return response
