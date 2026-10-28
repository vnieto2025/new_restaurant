from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Categoria import Categoria
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

categoria_router = APIRouter()

@categoria_router.post('/categoria/list', tags=["Categoría"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar"]))])
@http_decorator
def list_categories(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Categoria(db, request.state.user).list(data)
    return response

@categoria_router.post('/categoria/create', tags=["Categoría"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar"]))])
@http_decorator
def create(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Categoria(db, request.state.user).create(data)
    return response

@categoria_router.post('/categoria/update', tags=["Categoría"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar"]))])
@http_decorator
def update(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Categoria(db, request.state.user).update(data)
    return response

@categoria_router.post('/categoria/change_status', tags=["Categoría"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar"]))])
@http_decorator
def change_status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Categoria(db, request.state.user).change_status(data)
    return response
