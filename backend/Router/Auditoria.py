from fastapi import APIRouter, Request, Depends
from Utils.decorator import http_decorator
from Class.Auditoria import Auditoria
from Middleware.jwt_bearer import JWTBearer
from Config.db import get_db
from sqlalchemy.orm import Session

auditoria_router = APIRouter()

@auditoria_router.post('/auditoria/list', tags=["Auditoría"], response_model=dict, dependencies=[Depends(JWTBearer(permisos=["auditoria.ver"]))])
@http_decorator
def list_audit(request: Request, db: Session = Depends(get_db)):
    data = getattr(request.state, "json_data", {})
    response = Auditoria(db, request.state.user).list(data)
    return response
