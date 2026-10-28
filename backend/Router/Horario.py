from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Horario import Horario
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

horario_router = APIRouter()

@horario_router.post('/horario/get', tags=["Horario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["restaurante.configurar", "estructura.gestionar"]))])
@http_decorator
def get(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Horario(db, request.state.user).get(data)
    return response

@horario_router.post('/horario/set', tags=["Horario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["restaurante.configurar", "estructura.gestionar"]))])
@http_decorator
def set_schedule(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Horario(db, request.state.user).set(data)
    return response
