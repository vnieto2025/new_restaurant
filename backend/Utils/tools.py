from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from datetime import datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo
import unicodedata

DEFAULT_TIMEZONE = "America/Bogota"


# Fecha y hora actual en UTC (RG-08). Se usa como default de las columnas DateTime(timezone=True).
def now():
    return datetime.now(timezone.utc)


# Pasa una fecha a la zona horaria del restaurante para mostrarla o agruparla
def to_local(value: datetime, tz_name: str = DEFAULT_TIMEZONE):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(ZoneInfo(tz_name or DEFAULT_TIMEZONE))


# Jornada operativa (RG-09): el "día" del restaurante empieza a su hora de inicio de jornada.
# Con inicio a las 06:00, una orden de las 2:00 a.m. del sábado pertenece a la jornada del viernes.
def jornada(value: datetime = None, tz_name: str = DEFAULT_TIMEZONE, inicio: time = None):
    local = to_local(value or now(), tz_name)
    inicio = inicio or time(0, 0)
    corrida = local - timedelta(hours=inicio.hour, minutes=inicio.minute)
    return corrida.date()


# Pasa un texto a minúsculas, sin tildes y con espacios simples ("José  Pérez" -> "jose perez")
def normalize_text(text):
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.lower().split())


# Quita espacios repetidos de un texto; devuelve None si queda vacío
def clean_text(text):
    if text is None:
        return None
    text = " ".join(str(text).split())
    return text or None


class Tools:

    """ Esta funcion permite darle formato a la respuesta de la API """
    def output(self, codigo, message, data={}):

        response = JSONResponse(
            status_code=codigo,
            content=jsonable_encoder({
                "code": codigo,
                "message": message,
                "data": data,
            }),
            media_type="application/json"
        )
        return response

    def result(self, msg, code=400, error="", data=[]):
        return {
            "body": {
                "statusCode": code,
                "message": msg,
                "data": data,
                "Exception": error
            }
        }

    # Función para formatear los numeros
    def format_number(self, numero):
        formateado = f"{numero:,.0f}".replace(",", ".")
        return formateado


class CustomException(Exception):
    """ Esta clase hereda de la clase Exception y permite
        interrumpir la ejecucion de un metodo invocando una excepcion
        personalizada """
    def __init__(self, message="", codigo=400, data={}):
        self.codigo = codigo
        self.message = message
        self.data = data
        self.resultado = {
            "body": {
                "statusCode": codigo,
                "message": message,
                "data": data,
                "Exception": "CustomException"
            }
        }
