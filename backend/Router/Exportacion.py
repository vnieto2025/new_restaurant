from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Exportacion import Exportacion
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

exportacion_router = APIRouter()

@exportacion_router.post('/exportacion/catalogo', tags=["Exportación"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["datos.exportar"]))])
@http_decorator
def catalog(request: Request, db: Session = Depends(get_db)):
    response = Exportacion(db, request.state.user).catalog()
    return response

@exportacion_router.post('/exportacion/generar', tags=["Exportación"], dependencies=[Depends(JWTBearer(permisos=["datos.exportar"]))])
@http_decorator
def generate(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Exportacion(db, request.state.user).generate(data)
    return response
