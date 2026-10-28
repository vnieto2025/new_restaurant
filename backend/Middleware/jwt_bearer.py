from fastapi.security import HTTPBearer
from fastapi import Request
from starlette.concurrency import run_in_threadpool
from Utils.jwt_manager import validate_token
from Utils.contexto import cargar_contexto, exigir, sesion_invalida


class JWTBearer(HTTPBearer):
    """ Autentica la petición y deja el contexto en request.state.user.

        permisos: basta con tener uno de la lista (doc 29).
        modulo: módulo que debe estar contratado; si no, responde 403 modulo_no_contratado (RN-API-03). """

    def __init__(self, permisos: list = None, modulo: str = None):
        super(JWTBearer, self).__init__(auto_error=False)
        self.permisos = permisos
        self.modulo = modulo

    async def __call__(self, request: Request):
        auth = await super().__call__(request)
        if not auth:
            raise sesion_invalida("Debe iniciar sesión.")
        token_data = validate_token(auth.credentials)

        ctx = await run_in_threadpool(
            cargar_contexto,
            token_data,
            request.client.host if request.client else None,
            request.headers.get("user-agent"),
        )
        exigir(ctx, self.permisos, self.modulo)

        # Deja los datos del usuario autenticado disponibles para la clase
        request.state.user = ctx
