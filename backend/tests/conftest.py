"""
Las pruebas corren contra una base de Postgres aparte (DB_NAME_TEST en .env),
que se borra y se vuelve a crear al iniciar cada corrida.
"""
import os
import sys
import uuid
from pathlib import Path
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
load_dotenv(BACKEND / ".env")
os.environ["DB_NAME"] = os.getenv("DB_NAME_TEST", "restaurant_test")
os.environ["PUBLIC_URL"] = "http://carta.test"
# La cola de emisión se procesa a mano en las pruebas (/documento/enviar), no en segundo plano
os.environ["EMISION_AUTOMATICA"] = "0"
os.environ["MENSAJES_AUTOMATICOS"] = "0"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
import Models  # noqa: E402,F401
from sqlalchemy.orm import sessionmaker  # noqa: E402
from Config.db import BASE, engine, admin_engine  # noqa: E402
from Utils import rls  # noqa: E402
from Utils.limiter import limiter  # noqa: E402
import seed  # noqa: E402

assert engine.url.database == os.environ["DB_NAME"], "Las pruebas no deben tocar la base de desarrollo"
assert os.getenv("DB_APP_USER"), "Las pruebas necesitan DB_APP_USER para que RLS esté activo"
assert engine.url.username == os.getenv("DB_APP_USER")

PASSWORD = seed.DEMO_PASSWORD


@pytest.fixture(scope="session", autouse=True)
def database():
    BASE.metadata.drop_all(bind=admin_engine)
    BASE.metadata.create_all(bind=admin_engine)
    rls.configurar(admin_engine, os.getenv("DB_APP_USER"), os.getenv("DB_APP_PASS"))
    db = sessionmaker(bind=admin_engine)()
    try:
        seed.seed_catalog(db)
        seed.create_superadmin(db, "soporte", "Soporte12345", "Soporte plataforma")
        seed.seed_demo(db)
    finally:
        db.close()
    yield


@pytest.fixture(scope="session")
def client(database):
    from main import app
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_limits():
    limiter.reset()
    yield
    limiter.reset()


class Api:
    """ Cliente que habla como el frontend: POST, JSON y header accept """

    def __init__(self, client, token=None):
        self.client = client
        self.token = token

    def post(self, path, body=None, expect=None):
        headers = {"accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        response = self.client.post(path, json=body or {}, headers=headers)
        if expect is not None:
            assert response.status_code == expect, f"{path}: {response.status_code} {response.text}"
        return response

    def data(self, path, body=None, expect=200):
        return self.post(path, body, expect).json()["data"]


def login(client, usuario, password=PASSWORD, restaurante_id=None):
    response = Api(client).post("/login", {"usuario": usuario, "password": password,
                                           "restaurante_id": restaurante_id})
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    return Api(client, data["token"]), data


@pytest.fixture(scope="session")
def esquina(client):
    """ Sesiones de los usuarios demo de La Esquina """
    sesiones = {}
    for usuario in ["esquina", "admin.esquina", "mesero.salon", "mesero.terraza",
                    "cocina.esquina", "bar.esquina", "caja.esquina"]:
        sesiones[usuario] = login(client, usuario)
    return sesiones


@pytest.fixture(scope="session")
def napoli(client):
    return {usuario: login(client, usuario) for usuario in ["napoli", "mesero.napoli", "cocina.napoli"]}


def key():
    return uuid.uuid4().hex


def find(rows, **filters):
    for row in rows:
        if all(row.get(k) == v for k, v in filters.items()):
            return row
    raise AssertionError(f"No se encontró {filters} en {[r.get('nombre') for r in rows]}")


def product_id(api, nombre):
    return find(api.data("/producto/list", {"todos": True}), nombre=nombre)["id"]


def option_id(api, grupo, opcion):
    """ Id de una opción de modificador por nombre de grupo y de opción """
    return find(find(api.data("/modificador/list"), nombre=grupo)["opciones"], nombre=opcion)["id"]


def ensure_shift(api):
    """ Deja abierto el turno de caja (lo comparten las pruebas de la sesión) """
    estado = api.data("/caja/estado")
    if not estado["turno"]:
        api.data("/caja/turno/abrir", {"fondo_inicial": 100000}, expect=201)
    return api.data("/caja/estado")


def medio(api, nombre):
    return find(api.data("/caja/estado")["medios"], nombre=nombre)["id"]


def pay_table(api, mesa_id=None, sesion_mesa_id=None):
    """ Cobra en efectivo todo lo que tenga la mesa o el pedido """
    ensure_shift(api)
    cuenta = api.data("/cuenta/abrir", {"mesa_id": mesa_id, "sesion_mesa_id": sesion_mesa_id})
    return api.data("/cuenta/pagar", {"cuenta_id": cuenta["id"], "clave_idempotencia": key(), "pagos": [
        {"medio_pago_id": medio(api, "Efectivo"), "monto": cuenta["saldo"]}]})


def table(api, nombre, incluir_externa=False):
    return find(api.data("/mesa/list", {"incluir_externa": incluir_externa}), nombre=nombre)


def qr_token(api, mesa_nombre):
    row = find(api.data("/qr/list"), mesa=mesa_nombre)
    return row["url"].rsplit("/", 1)[1]
