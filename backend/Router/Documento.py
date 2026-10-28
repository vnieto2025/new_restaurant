from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Documento import Documento
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

documento_router = APIRouter()

@documento_router.post('/documento/list', tags=["Facturación"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["facturacion.ver"], modulo="facturacion"))])
@http_decorator
def list_documents(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Documento(db, request.state.user).list(data)
    return response

@documento_router.post('/documento/get', tags=["Facturación"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["facturacion.ver"], modulo="facturacion"))])
@http_decorator
def get(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Documento(db, request.state.user).get(data)
    return response

@documento_router.post('/documento/facturar', tags=["Facturación"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["facturacion.facturar", "facturacion.gestionar"], modulo="facturacion"))])
@http_decorator
def invoice_for(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Documento(db, request.state.user).invoice_for(data)
    return response

@documento_router.post('/documento/corregir', tags=["Facturación"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["facturacion.gestionar"], modulo="facturacion"))])
@http_decorator
def correct(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Documento(db, request.state.user).correct(data)
    return response

@documento_router.post('/documento/enviar', tags=["Facturación"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["facturacion.gestionar", "facturacion.facturar"], modulo="facturacion"))])
@http_decorator
def process(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Documento(db, request.state.user).process(data)
    return response

@documento_router.post('/documento/impuestos', tags=["Facturación"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["facturacion.ver", "reportes.ver"], modulo="facturacion"))])
@http_decorator
def tax_summary(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Documento(db, request.state.user).tax_summary(data)
    return response
