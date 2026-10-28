from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Dispositivo import Dispositivo
from Class.TurnoMesero import TurnoMesero
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

dispositivo_router = APIRouter()

GESTIONAR = JWTBearer(permisos=["estructura.gestionar"], modulo="pedidos")

@dispositivo_router.post('/dispositivo/list', tags=["Dispositivo"], response_model=dict, dependencies=[Depends(GESTIONAR)])
@http_decorator
def list_devices(request: Request, db: Session = Depends(get_db)):
    response = Dispositivo(db, request.state.user).list()
    return response

@dispositivo_router.post('/dispositivo/create', tags=["Dispositivo"], response_model=dict, dependencies=[Depends(GESTIONAR)])
@http_decorator
def create(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Dispositivo(db, request.state.user).create(data)
    return response

@dispositivo_router.post('/dispositivo/codigo', tags=["Dispositivo"], response_model=dict, dependencies=[Depends(GESTIONAR)])
@http_decorator
def new_pairing_code(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Dispositivo(db, request.state.user).new_pairing_code(data)
    return response

@dispositivo_router.post('/dispositivo/change_status', tags=["Dispositivo"], response_model=dict, dependencies=[Depends(GESTIONAR)])
@http_decorator
def change_status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Dispositivo(db, request.state.user).change_status(data)
    return response

# Rutas de la tablet: se identifican con el código o con el secreto del dispositivo

@dispositivo_router.post('/dispositivo/emparejar', tags=["Dispositivo"], response_model=dict)
@http_decorator
def pair(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Dispositivo(db).pair(data, request.client.host if request.client else None)
    return response

@dispositivo_router.post('/dispositivo/info', tags=["Dispositivo"], response_model=dict)
@http_decorator
def info(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Dispositivo(db).info(data)
    return response

@dispositivo_router.post('/dispositivo/pin', tags=["Dispositivo"], response_model=dict)
@http_decorator
def pin_login(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Dispositivo(db).pin_login(data, request.client.host if request.client else None,
                                         request.headers.get("user-agent"))
    return response

@dispositivo_router.post('/turno_mesero/actual', tags=["Turno mesero"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["ordenes.crear_mesa"]))])
@http_decorator
def current_turn(request: Request, db: Session = Depends(get_db)):
    response = TurnoMesero(db, request.state.user).current()
    return response

@dispositivo_router.post('/turno_mesero/cerrar', tags=["Turno mesero"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["ordenes.crear_mesa"]))])
@http_decorator
def close_turn(request: Request, db: Session = Depends(get_db)):
    response = TurnoMesero(db, request.state.user).close()
    return response
