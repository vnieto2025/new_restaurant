from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Pos import Pos
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

pos_router = APIRouter()

@pos_router.post('/pos/carta', tags=["Venta directa"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["caja.cobrar", "caja.cobrar_externas"], modulo="caja"))])
@http_decorator
def menu(request: Request, db: Session = Depends(get_db)):
    response = Pos(db, request.state.user).menu()
    return response

@pos_router.post('/pos/vender', tags=["Venta directa"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["caja.cobrar", "caja.cobrar_externas"], modulo="caja"))])
@http_decorator
def sell(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Pos(db, request.state.user).sell(data)
    return response

@pos_router.post('/pos/cancelar', tags=["Venta directa"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["caja.cobrar", "caja.cobrar_externas"], modulo="caja"))])
@http_decorator
def cancel(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Pos(db, request.state.user).cancel(data)
    return response
