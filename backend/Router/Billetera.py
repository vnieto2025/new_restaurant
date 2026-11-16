from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Billetera import Billetera
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

billetera_router = APIRouter()

CONFIGURAR = JWTBearer(permisos=["restaurante.configurar"])

@billetera_router.post('/billetera/list', tags=["Billeteras"], response_model=dict, dependencies=[Depends(CONFIGURAR)])
@http_decorator
def list_wallets(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Billetera(db, request.state.user).list(data)
    return response

@billetera_router.post('/billetera/save', tags=["Billeteras"], response_model=dict, dependencies=[Depends(CONFIGURAR)])
@http_decorator
def save_wallet(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Billetera(db, request.state.user).save(data)
    return response

@billetera_router.post('/billetera/delete', tags=["Billeteras"], response_model=dict, dependencies=[Depends(CONFIGURAR)])
@http_decorator
def delete_wallet(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Billetera(db, request.state.user).delete(data)
    return response
