from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Usuario import Usuario
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

usuario_router = APIRouter()

GESTIONAR = JWTBearer(permisos=["usuarios.gestionar"])

@usuario_router.post('/usuario/list', tags=["Usuario"], response_model=dict, dependencies=[Depends(GESTIONAR)])
@http_decorator
def list_users(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Usuario(db, request.state.user).list(data)
    return response

@usuario_router.post('/usuario/get', tags=["Usuario"], response_model=dict, dependencies=[Depends(GESTIONAR)])
@http_decorator
def get(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Usuario(db, request.state.user).get(data)
    return response

@usuario_router.post('/usuario/roles', tags=["Usuario"], response_model=dict, dependencies=[Depends(GESTIONAR)])
@http_decorator
def roles(request: Request, db: Session = Depends(get_db)):
    response = Usuario(db, request.state.user).roles()
    return response

@usuario_router.post('/usuario/create', tags=["Usuario"], response_model=dict, dependencies=[Depends(GESTIONAR)])
@http_decorator
def create(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Usuario(db, request.state.user).create(data)
    return response

@usuario_router.post('/usuario/update', tags=["Usuario"], response_model=dict, dependencies=[Depends(GESTIONAR)])
@http_decorator
def update(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Usuario(db, request.state.user).update(data)
    return response

@usuario_router.post('/usuario/pin', tags=["Usuario"], response_model=dict, dependencies=[Depends(GESTIONAR)])
@http_decorator
def set_pin(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Usuario(db, request.state.user).set_pin(data)
    return response

@usuario_router.post('/usuario/change_status', tags=["Usuario"], response_model=dict, dependencies=[Depends(GESTIONAR)])
@http_decorator
def change_status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Usuario(db, request.state.user).change_status(data)
    return response
