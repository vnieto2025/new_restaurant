from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Receta import Receta
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

receta_router = APIRouter()

@receta_router.post('/receta/get', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.ver", "inventario.gestionar"], modulo="inventario"))])
@http_decorator
def get(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Receta(db, request.state.user).get(data)
    return response

@receta_router.post('/receta/save', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.gestionar"], modulo="inventario"))])
@http_decorator
def save(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Receta(db, request.state.user).save(data)
    return response

@receta_router.post('/receta/delete', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.gestionar"], modulo="inventario"))])
@http_decorator
def delete(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Receta(db, request.state.user).delete(data)
    return response

@receta_router.post('/receta/costos', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.ver", "inventario.gestionar"], modulo="inventario"))])
@http_decorator
def costs(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Receta(db, request.state.user).costs(data)
    return response

@receta_router.post('/receta/opcion/list', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.ver", "inventario.gestionar"], modulo="inventario"))])
@http_decorator
def option_supplies(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Receta(db, request.state.user).option_supplies(data)
    return response

@receta_router.post('/receta/opcion/save', tags=["Inventario"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["inventario.gestionar"], modulo="inventario"))])
@http_decorator
def save_option_supplies(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Receta(db, request.state.user).save_option_supplies(data)
    return response
