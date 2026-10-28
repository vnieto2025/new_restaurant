from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Cuenta import Cuenta
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

cuenta_router = APIRouter()

@cuenta_router.post('/cuenta/pendientes', tags=["Cuenta"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["caja.cobrar", "caja.cobrar_externas"], modulo="caja"))])
@http_decorator
def pending(request: Request, db: Session = Depends(get_db)):
    response = Cuenta(db, request.state.user).pending()
    return response

@cuenta_router.post('/cuenta/abrir', tags=["Cuenta"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["caja.cobrar", "caja.cobrar_externas", "ordenes.pedir_cuenta"], modulo="caja"))])
@http_decorator
def open_account(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cuenta(db, request.state.user).open(data)
    return response

@cuenta_router.post('/cuenta/solicitar', tags=["Cuenta"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["ordenes.pedir_cuenta"], modulo="caja"))])
@http_decorator
def request(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cuenta(db, request.state.user).request(data)
    return response

@cuenta_router.post('/cuenta/get', tags=["Cuenta"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["caja.ver", "caja.cobrar", "caja.cobrar_externas", "ordenes.pedir_cuenta"], modulo="caja"))])
@http_decorator
def get(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cuenta(db, request.state.user).get(data)
    return response

@cuenta_router.post('/cuenta/ajustar', tags=["Cuenta"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["caja.cobrar", "caja.cobrar_externas"], modulo="caja"))])
@http_decorator
def adjust(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cuenta(db, request.state.user).adjust(data)
    return response

@cuenta_router.post('/cuenta/pagar', tags=["Cuenta"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["caja.cobrar", "caja.cobrar_externas"], modulo="caja"))])
@http_decorator
def pay(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cuenta(db, request.state.user).pay(data)
    return response

@cuenta_router.post('/cuenta/anular_pago', tags=["Cuenta"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["caja.anular"], modulo="caja"))])
@http_decorator
def void_payment(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cuenta(db, request.state.user).void_payment(data)
    return response

@cuenta_router.post('/cuenta/anular', tags=["Cuenta"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["caja.anular"], modulo="caja"))])
@http_decorator
def void(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cuenta(db, request.state.user).void(data)
    return response

@cuenta_router.post('/cuenta/list', tags=["Cuenta"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["caja.ver", "caja.cobrar", "caja.cobrar_externas"], modulo="caja"))])
@http_decorator
def list_accounts(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Cuenta(db, request.state.user).list(data)
    return response
