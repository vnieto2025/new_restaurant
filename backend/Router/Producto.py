from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Producto import Producto
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

producto_router = APIRouter()

@producto_router.post('/producto/list', tags=["Producto"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar", "productos.agotar"]))])
@http_decorator
def list_products(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Producto(db, request.state.user).list(data)
    return response

@producto_router.post('/producto/create', tags=["Producto"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar"]))])
@http_decorator
def create(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Producto(db, request.state.user).create(data)
    return response

@producto_router.post('/producto/update', tags=["Producto"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar"]))])
@http_decorator
def update(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Producto(db, request.state.user).update(data)
    return response

@producto_router.post('/producto/change_status', tags=["Producto"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar"]))])
@http_decorator
def change_status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Producto(db, request.state.user).change_status(data)
    return response

@producto_router.post('/producto/agotado', tags=["Producto"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["productos.agotar"]))])
@http_decorator
def sold_out(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Producto(db, request.state.user).sold_out(data)
    return response
