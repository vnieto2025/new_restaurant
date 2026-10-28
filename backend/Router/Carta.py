from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Carta import Carta
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

carta_router = APIRouter()

@carta_router.post('/carta/list', tags=["Carta"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar"]))])
@http_decorator
def list_menus(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Carta(db, request.state.user).list(data)
    return response

@carta_router.post('/carta/get', tags=["Carta"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar"]))])
@http_decorator
def get(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Carta(db, request.state.user).get(data)
    return response

@carta_router.post('/carta/create', tags=["Carta"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar"]))])
@http_decorator
def create(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Carta(db, request.state.user).create(data)
    return response

@carta_router.post('/carta/update', tags=["Carta"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar"]))])
@http_decorator
def update(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Carta(db, request.state.user).update(data)
    return response

@carta_router.post('/carta/change_status', tags=["Carta"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar"]))])
@http_decorator
def change_status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Carta(db, request.state.user).change_status(data)
    return response
