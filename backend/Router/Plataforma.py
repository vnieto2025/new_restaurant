from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Plataforma import Plataforma
from Class.Suscripcion import Suscripcion
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

plataforma_router = APIRouter()

PLATAFORMA = JWTBearer(permisos=["plataforma.gestionar"])

@plataforma_router.post('/plataforma/empresa/create', tags=["Plataforma"], response_model=dict, dependencies=[Depends(PLATAFORMA)])
@http_decorator
def create_company(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Plataforma(db, request.state.user).create_company(data)
    return response

@plataforma_router.post('/plataforma/empresa/list', tags=["Plataforma"], response_model=dict, dependencies=[Depends(PLATAFORMA)])
@http_decorator
def list_companies(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Plataforma(db, request.state.user).list_companies(data)
    return response

@plataforma_router.post('/plataforma/empresa/change_status', tags=["Plataforma"], response_model=dict, dependencies=[Depends(PLATAFORMA)])
@http_decorator
def change_company_status(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Plataforma(db, request.state.user).change_company_status(data)
    return response

@plataforma_router.post('/plataforma/restaurante/create', tags=["Plataforma"], response_model=dict, dependencies=[Depends(PLATAFORMA)])
@http_decorator
def create_restaurant(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Plataforma(db, request.state.user).create_restaurant(data)
    return response

@plataforma_router.post('/plataforma/contrato/update', tags=["Plataforma"], response_model=dict, dependencies=[Depends(PLATAFORMA)])
@http_decorator
def update_contract(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Plataforma(db, request.state.user).update_contract(data)
    return response

@plataforma_router.post('/plataforma/modulo/list', tags=["Plataforma"], response_model=dict, dependencies=[Depends(PLATAFORMA)])
@http_decorator
def list_modules(request: Request, db: Session = Depends(get_db)):
    response = Plataforma(db, request.state.user).list_modules()
    return response

@plataforma_router.post('/plataforma/plan/list', tags=["Plataforma"], response_model=dict, dependencies=[Depends(PLATAFORMA)])
@http_decorator
def list_plans(request: Request, db: Session = Depends(get_db)):
    return Suscripcion(db, request.state.user).plans()

@plataforma_router.post('/plataforma/suscripcion/pagos', tags=["Plataforma"], response_model=dict, dependencies=[Depends(PLATAFORMA)])
@http_decorator
def subscription_payments(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    return Suscripcion(db, request.state.user).payments(data)

@plataforma_router.post('/plataforma/suscripcion/pagar', tags=["Plataforma"], response_model=dict, dependencies=[Depends(PLATAFORMA)])
@http_decorator
def register_subscription_payment(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    return Suscripcion(db, request.state.user).register_payment(data)
