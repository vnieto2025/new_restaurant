from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Reporte import Reporte
from Class.Analisis import Analisis
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

reporte_router = APIRouter()

@reporte_router.post('/reporte/ventas', tags=["Reportes"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["reportes.ver"]))])
@http_decorator
def sales(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Reporte(db, request.state.user).sales(data)
    return response

@reporte_router.post('/reporte/cancelaciones', tags=["Reportes"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["reportes.ver"]))])
@http_decorator
def cancellations(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Reporte(db, request.state.user).cancellations(data)
    return response

@reporte_router.post('/reporte/meseros', tags=["Reportes"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["reportes.ver"]))])
@http_decorator
def waiters(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Reporte(db, request.state.user).waiters(data)
    return response

@reporte_router.post('/reporte/mesero', tags=["Reportes"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["reportes.ver", "reportes.propio"]))])
@http_decorator
def waiter_report(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Reporte(db, request.state.user).waiter_report(data)
    return response

@reporte_router.post('/reporte/dashboard', tags=["Reportes"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["reportes.ver"]))])
@http_decorator
def dashboard(request: Request, db: Session = Depends(get_db)):
    response = Reporte(db, request.state.user).dashboard()
    return response

@reporte_router.post('/reporte/analisis', tags=["Reportes"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["reportes.ver"]))])
@http_decorator
def analysis(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Analisis(db, request.state.user).analysis(data)
    return response

@reporte_router.post('/reporte/sedes', tags=["Reportes"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["reportes.ver"]))])
@http_decorator
def branches(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Analisis(db, request.state.user).branches(data)
    return response
