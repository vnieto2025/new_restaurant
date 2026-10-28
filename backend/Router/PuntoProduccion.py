from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.PuntoProduccion import PuntoProduccion
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

punto_produccion_router = APIRouter()

@punto_produccion_router.post('/punto_produccion/list', tags=["Punto de producción"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["cocina.operar", "estructura.gestionar", "catalogo.gestionar"], modulo="pedidos"))])
@http_decorator
def list_points(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = PuntoProduccion(db, request.state.user).list(data)
    return response

@punto_produccion_router.post('/punto_produccion/create', tags=["Punto de producción"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["estructura.gestionar"], modulo="pedidos"))])
@http_decorator
def create(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = PuntoProduccion(db, request.state.user).create(data)
    return response

@punto_produccion_router.post('/punto_produccion/update', tags=["Punto de producción"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["estructura.gestionar"], modulo="pedidos"))])
@http_decorator
def update(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = PuntoProduccion(db, request.state.user).update(data)
    return response

@punto_produccion_router.post('/punto_produccion/change_status', tags=["Punto de producción"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["estructura.gestionar"], modulo="pedidos"))])
@http_decorator
def change_status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = PuntoProduccion(db, request.state.user).change_status(data)
    return response
