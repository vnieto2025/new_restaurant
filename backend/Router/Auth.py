from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Auth import Auth
from Class.DobleFactor import DobleFactor
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

auth_router = APIRouter()

@auth_router.post('/login', tags=["Auth"], response_model=dict)
@http_decorator
def login(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Auth(db).login(data, request.client.host if request.client else None,
                              request.headers.get("user-agent"))
    return response

@auth_router.post('/auth/sesion', tags=["Auth"], response_model=dict, dependencies=[Depends(JWTBearer())])
@http_decorator
def session(request: Request, db: Session = Depends(get_db)):
    response = Auth(db, request.state.user).session()
    return response

@auth_router.post('/auth/cambiar_restaurante', tags=["Auth"], response_model=dict, dependencies=[Depends(JWTBearer())])
@http_decorator
def change_restaurant(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Auth(db, request.state.user).change_restaurant(data)
    return response

@auth_router.post('/auth/cambiar_password', tags=["Auth"], response_model=dict, dependencies=[Depends(JWTBearer())])
@http_decorator
def change_password(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Auth(db, request.state.user).change_password(data)
    return response

@auth_router.post('/auth/2fa/estado', tags=["Auth"], response_model=dict, dependencies=[Depends(JWTBearer())])
@http_decorator
def two_factor_status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = DobleFactor(db, request.state.user).status(data)
    return response

@auth_router.post('/auth/2fa/iniciar', tags=["Auth"], response_model=dict, dependencies=[Depends(JWTBearer())])
@http_decorator
def two_factor_start(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = DobleFactor(db, request.state.user).start(data)
    return response

@auth_router.post('/auth/2fa/activar', tags=["Auth"], response_model=dict, dependencies=[Depends(JWTBearer())])
@http_decorator
def two_factor_activate(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = DobleFactor(db, request.state.user).activate(data)
    return response

@auth_router.post('/auth/2fa/desactivar', tags=["Auth"], response_model=dict, dependencies=[Depends(JWTBearer())])
@http_decorator
def two_factor_disable(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = DobleFactor(db, request.state.user).disable(data)
    return response

@auth_router.post('/auth/2fa/codigos', tags=["Auth"], response_model=dict, dependencies=[Depends(JWTBearer())])
@http_decorator
def two_factor_codes(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = DobleFactor(db, request.state.user).new_backup_codes(data)
    return response
