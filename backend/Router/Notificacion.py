from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Notificacion import Notificacion
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

notificacion_router = APIRouter()

@notificacion_router.post('/notificacion/config/get', tags=["Avisos"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["notificaciones.configurar"], modulo="pedidos"))])
@http_decorator
def get_config(request: Request, db: Session = Depends(get_db)):
    response = Notificacion(db, request.state.user).get_config()
    return response

@notificacion_router.post('/notificacion/config/save', tags=["Avisos"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["notificaciones.configurar"], modulo="pedidos"))])
@http_decorator
def save_config(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Notificacion(db, request.state.user).save_config(data)
    return response

@notificacion_router.post('/notificacion/pendientes', tags=["Avisos"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["notificaciones.enviar", "notificaciones.configurar"], modulo="pedidos"))])
@http_decorator
def pending(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Notificacion(db, request.state.user).pending(data)
    return response

@notificacion_router.post('/notificacion/enviada', tags=["Avisos"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["notificaciones.enviar", "notificaciones.configurar"], modulo="pedidos"))])
@http_decorator
def mark_sent(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Notificacion(db, request.state.user).mark_sent(data)
    return response

@notificacion_router.post('/notificacion/descartar', tags=["Avisos"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["notificaciones.enviar", "notificaciones.configurar"], modulo="pedidos"))])
@http_decorator
def discard(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Notificacion(db, request.state.user).discard(data)
    return response

@notificacion_router.post('/notificacion/reintentar', tags=["Avisos"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["notificaciones.enviar", "notificaciones.configurar"], modulo="pedidos"))])
@http_decorator
def retry(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Notificacion(db, request.state.user).retry(data)
    return response

@notificacion_router.post('/notificacion/list', tags=["Avisos"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["notificaciones.configurar"], modulo="pedidos"))])
@http_decorator
def list_notifications(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Notificacion(db, request.state.user).list(data)
    return response

@notificacion_router.post('/notificacion/prueba', tags=["Avisos"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["notificaciones.configurar"], modulo="pedidos"))])
@http_decorator
def test(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Notificacion(db, request.state.user).test(data)
    return response

@notificacion_router.post('/notificacion/procesar', tags=["Avisos"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["notificaciones.configurar"], modulo="pedidos"))])
@http_decorator
def process(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Notificacion(db, request.state.user).process(data)
    return response
