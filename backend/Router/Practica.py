from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Practica import Practica
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

practica_router = APIRouter()

@practica_router.post('/practica/estado', tags=["Práctica"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["restaurante.configurar"]))])
@http_decorator
def practice_status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Practica(db, request.state.user).get(data)
    return response

@practica_router.post('/practica/crear', tags=["Práctica"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["restaurante.configurar"]))])
@http_decorator
def create_practice(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Practica(db, request.state.user).create(data)
    return response

@practica_router.post('/practica/reiniciar', tags=["Práctica"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["restaurante.configurar"]))])
@http_decorator
def reset_practice(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Practica(db, request.state.user).reset(data)
    return response
