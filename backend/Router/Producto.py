from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Producto import Producto
from Class.ImportarProductos import ImportarProductos
from Class.CopiarProductos import CopiarProductos
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

@producto_router.post('/producto/importar/plantilla', tags=["Producto"], dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar"]))])
@http_decorator
def import_template(request: Request, db: Session = Depends(get_db)):
    response = ImportarProductos(db, request.state.user).template()
    return response

@producto_router.post('/producto/importar/revisar', tags=["Producto"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar"]))])
@http_decorator
def import_preview(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = ImportarProductos(db, request.state.user).preview(data)
    return response

@producto_router.post('/producto/importar/aplicar', tags=["Producto"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar"]))])
@http_decorator
def import_apply(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = ImportarProductos(db, request.state.user).apply(data)
    return response

@producto_router.post('/producto/duplicar', tags=["Producto"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar"]))])
@http_decorator
def duplicate(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = CopiarProductos(db, request.state.user).duplicate(data)
    return response

@producto_router.post('/producto/copiar', tags=["Producto"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["catalogo.gestionar"]))])
@http_decorator
def copy_to_branch(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = CopiarProductos(db, request.state.user).copy_to_branch(data)
    return response
