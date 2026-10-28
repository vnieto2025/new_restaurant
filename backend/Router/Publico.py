from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Publico import Publico
from Config.db import get_db
from sqlalchemy.orm import Session

publico_router = APIRouter()

# Rutas sin sesión: el contexto sale del token del QR (doc 10A)

@publico_router.post('/publico/qr', tags=["Público"], response_model=dict)
@http_decorator
def resolve_qr(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Publico(db, request.client.host if request.client else None,
                       request.headers.get("user-agent")).qr(data)
    return response

@publico_router.post('/publico/orden/create', tags=["Público"], response_model=dict)
@http_decorator
def create_order(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Publico(db, request.client.host if request.client else None,
                       request.headers.get("user-agent")).create_order(data)
    return response

@publico_router.post('/publico/orden/estado', tags=["Público"], response_model=dict)
@http_decorator
def order_status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Publico(db, request.client.host if request.client else None,
                       request.headers.get("user-agent")).status(data)
    return response
