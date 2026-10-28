from Models.log_peticion_model import LogPeticionModel
from .tools import CustomException, Tools, now
from Rules import Rules
from Querys.base import Querys
from functools import wraps
from fastapi import Request
from sqlalchemy import exc
import traceback
import json
from urllib.parse import urlparse

tool = Tools()

# Campos que nunca se deben guardar en texto plano en los logs
SENSITIVE_FIELDS = ["password", "current_password", "new_password", "token", "pin"]

# Reemplaza los valores sensibles antes de guardar el log
def mask_sensitive_data(obj):
    if isinstance(obj, dict):
        return {
            key: "****" if key in SENSITIVE_FIELDS else mask_sensitive_data(value)
            for key, value in obj.items()
        }
    if isinstance(obj, list):
        return [mask_sensitive_data(item) for item in obj]
    return obj

def http_decorator(func):
    @wraps(func)
    def decorador(*args, **kwargs):
        # Verificar si el método es POST o PUT
        request: Request = kwargs.get("request")
        data_log = dict()
        if request.method in ['POST', 'PUT']:
            codigo = 200
            data = {}
            resultado = ""
            # Verificar si la solicitud tiene un encabezado Content-Type válido
            if request.headers.get('accept') == 'application/json':
                try:
                    # Intentar cargar el cuerpo de la solicitud como JSON
                    body = getattr(request.state, "json_data", {})
                    path = str(request.url.path)
                    # Parsear la URL
                    parsed_url = urlparse(path)
                    # Obtener la ruta
                    path = parsed_url.path
                    Rules(path, body)
                    # Corre la función
                    resultado = func(*args, **kwargs)
                except CustomException as ce:
                    print(f"[CustomException] {ce.message}")
                    print(traceback.format_exc())
                    codigo = ce.codigo
                    message = ce.message
                    data = ce.data
                    resultado = tool.result(message, codigo,
                                            "CustomException", data)
                except json.JSONDecodeError as json_e:
                    print(str(json_e))
                    print(traceback.extract_tb(json_e.__traceback__))
                    codigo = 403
                    message = "La petición tiene un formato inválido."
                    resultado = tool.result(message, codigo, "JSONDecodeError")
                except KeyError as ke:
                    print(str(ke))
                    print(traceback.extract_tb(ke.__traceback__))
                    codigo = 422
                    message = f"Los datos enviados no son correctos o están incompletos. Verifique la información e inténtelo nuevamente. campo:{ke}"
                    resultado = tool.result(message, codigo, "KeyError")
                except TypeError as te:
                    print(str(te))
                    print(traceback.extract_tb(te.__traceback__))
                    codigo = 400
                    message = "Ha ocurrido un error al procesar los datos."
                    resultado = tool.result(message, codigo, "TypeError")
                except ValueError as ve:
                    print(str(ve))
                    print(traceback.extract_tb(ve.__traceback__))
                    codigo = 400
                    message = "Ha ocurrido un error al procesar los datos."
                    resultado = tool.result(message, codigo, "ValueError")
                except exc.OperationalError as te:
                    print(str(te))
                    print(traceback.extract_tb(te.__traceback__))
                    codigo = 500
                    message = "Hubo un error de conexión. Por favor intentelo más tarde."
                    resultado = tool.result(message, codigo, "OperationalError")
                except UnboundLocalError as ul:
                    print(str(ul))
                    print(traceback.extract_tb(ul.__traceback__))
                    codigo = 500
                    message = "Hubo un problema interno del sistema. Por favor intentelo más tarde."
                    resultado = tool.result(message, codigo, "UnboundLocalError")
                except Exception as ex:
                    print(str(ex))
                    print(traceback.extract_tb(ex.__traceback__))
                    codigo = 500
                    message = "Hubo un problema interno del sistema. Por favor intentelo más tarde."
                    resultado = tool.result(message, codigo, "Exception")
                finally:
                    if codigo != 200:
                        resultado = tool.output(codigo, message, data)

                    # Acceder al contenido del JSONResponse
                    contenido_serializado = resultado.body  # Esto está en formato bytes
                    contenido = json.loads(contenido_serializado.decode("utf-8"))  # Convertirlo a dict

                    data_log = {
                        "service": request.url.path,
                        "method": request.method,
                        "request": str(mask_sensitive_data(body)),
                        "response": str(mask_sensitive_data(contenido)),
                        "ip": request.client.host,
                        "creado_en": now()
                    }
                    db = kwargs.get("db")
                    if db:
                        # Si la petición falló a mitad de una transacción, Postgres
                        # no acepta más consultas hasta hacer rollback.
                        db.rollback()
                        querys = Querys(db)
                        querys.insert_data(LogPeticionModel, data_log)

            else:
                resultado = tool.output(406, "La petición debe enviar el header accept: application/json.")

            return resultado
    return decorador
