from Class.PuestaEnMarcha import PuestaEnMarcha
from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Restaurante import Restaurante
from Class.Qr import Qr
from Class.Suscripcion import Suscripcion
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

restaurante_router = APIRouter()

@restaurante_router.post('/restaurante/get', tags=["Restaurante"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["restaurante.configurar", "restaurante.pausar"]))])
@http_decorator
def get(request: Request, db: Session = Depends(get_db)):
    response = Restaurante(db, request.state.user).get()
    return response

@restaurante_router.post('/restaurante/update', tags=["Restaurante"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["restaurante.configurar"]))])
@http_decorator
def update(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Restaurante(db, request.state.user).update(data)
    return response

@restaurante_router.post('/restaurante/change_status', tags=["Restaurante"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["restaurante.pausar"]))])
@http_decorator
def change_status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Restaurante(db, request.state.user).change_status(data)
    return response

@restaurante_router.post('/qr/list', tags=["QR"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["qr.gestionar"], modulo="pedidos"))])
@http_decorator
def list_qr(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Qr(db, request.state.user).list(data)
    return response

@restaurante_router.post('/qr/regenerar', tags=["QR"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["qr.gestionar"], modulo="pedidos"))])
@http_decorator
def regenerate_qr(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Qr(db, request.state.user).regenerate(data)
    return response

# Plan, módulos y estado de la cuenta del servicio (doc 42)
@restaurante_router.post('/restaurante/plan', tags=["Restaurante"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["restaurante.configurar"]))])
@http_decorator
def my_plan(request: Request, db: Session = Depends(get_db)):
    return Suscripcion(db, request.state.user).my_plan()

# Asistente de configuración inicial (doc 41, sección 2)
@restaurante_router.post('/restaurante/puesta_en_marcha', tags=["Restaurante"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["restaurante.configurar"]))])
@http_decorator
def setup_status(request: Request, db: Session = Depends(get_db)):
    response = PuestaEnMarcha(db, request.state.user).get()
    return response

@restaurante_router.post('/restaurante/puesta_en_marcha/marcar', tags=["Restaurante"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["restaurante.configurar"]))])
@http_decorator
def setup_mark(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = PuestaEnMarcha(db, request.state.user).mark(data)
    return response
