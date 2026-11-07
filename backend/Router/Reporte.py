from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Reporte import Reporte
from Class.Analisis import Analisis
from Class.Alertas import Alertas
from Class.ResumenDiario import ResumenDiario
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

@reporte_router.post('/alerta/list', tags=["Alertas"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["reportes.ver"]))])
@http_decorator
def alerts(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Alertas(db, request.state.user).list(data)
    return response

@reporte_router.post('/alerta/silenciar', tags=["Alertas"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["restaurante.configurar"]))])
@http_decorator
def silence_alert(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Alertas(db, request.state.user).silence(data)
    return response

@reporte_router.post('/alerta/config/get', tags=["Alertas"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["restaurante.configurar"]))])
@http_decorator
def alerts_config(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Alertas(db, request.state.user).get_config(data)
    return response

@reporte_router.post('/alerta/config/save', tags=["Alertas"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["restaurante.configurar"]))])
@http_decorator
def save_alerts_config(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Alertas(db, request.state.user).save_config(data)
    return response

@reporte_router.post('/reporte/resumen_diario', tags=["Reportes"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["reportes.ver"]))])
@http_decorator
def daily_summary(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = ResumenDiario(db, request.state.user).get(data)
    return response

@reporte_router.post('/reporte/resumen_diario/config/get', tags=["Reportes"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["restaurante.configurar"]))])
@http_decorator
def daily_summary_config(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = ResumenDiario(db, request.state.user).get_config(data)
    return response

@reporte_router.post('/reporte/resumen_diario/config/save', tags=["Reportes"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["restaurante.configurar"]))])
@http_decorator
def save_daily_summary_config(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = ResumenDiario(db, request.state.user).save_config(data)
    return response
