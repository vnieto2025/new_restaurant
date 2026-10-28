from fastapi import HTTPException
from jwt import encode, decode, ExpiredSignatureError
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

load_dotenv()

# Las pantallas de cocina y las tablets no deben cerrar sesión en pleno servicio (doc 18),
# por eso el token dura una jornada larga. Se ajusta con TOKEN_MINUTES.
TOKEN_MINUTES = int(os.getenv("TOKEN_MINUTES", "720"))

def create_token(data: dict):

    expiration = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES)
    payload = {
        **data,
        "exp": expiration
    }
    token = encode(payload=payload, key=os.getenv("MY_SECRET_KEY"), algorithm="HS256")
    return token

def validate_token(token: str) -> dict:

    try:
        data: dict = decode(token, key=os.getenv("MY_SECRET_KEY"), algorithms=["HS256"])
        return data
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="El token ha expirado")
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")
