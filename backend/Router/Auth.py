from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Auth import Auth
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
