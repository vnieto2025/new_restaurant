"""
Verificación en dos pasos (ADR-054): activar con una aplicación autenticadora, ingresar con código o
con un código de respaldo, no reutilizar un código, PIN bloqueado, exigirla a los administradores y
quitársela a quien perdió el celular.
"""
import re
import pytest
from Utils import totp
from Utils.limiter import limiter
from conftest import Api, login, find

CLAVE = "clave12345"
# Secretos de las cuentas que activan la verificación, para seguir entrando en las pruebas siguientes
SECRETOS = {}


def secreto_de(datos):
    return re.search(r"secret=([A-Z2-7]+)", datos["uri"]).group(1)


def codigo(secreto, desplazamiento=0):
    return totp.codigo(secreto, totp.paso_actual() + desplazamiento)


@pytest.fixture(scope="module")
def empresa(client):
    soporte, _ = login(client, "soporte", "Soporte12345")
    soporte.data("/plataforma/empresa/create", {
        "nombre_comercial": "Seguridad SAS", "modulos": ["pedidos"], "estado_contrato": "activo",
        "admin": {"usuario": "duena.2fa", "nombre": "Dueña Segura", "password": CLAVE},
        "restaurante": {"nombre": "Seguro Centro", "hora_inicio_jornada": "05:00"},
    }, expect=201)
    duena, _ = login(client, "duena.2fa", CLAVE)
    duena.data("/usuario/create", {"usuario": "admin.2fa", "nombre": "Admin Seguro", "password": CLAVE, "roles": ["admin_restaurante"]}, expect=201)
    salon = find(duena.data("/zona/list"), nombre="Salón")
    duena.data("/usuario/create", {"usuario": "mesero.2fa", "nombre": "Mesero Seguro", "password": CLAVE, "roles": ["mesero"],
                                   "zonas": [salon["id"]]}, expect=201)
    return duena


def activar(api):
    datos = api.data("/auth/2fa/iniciar", {"password": CLAVE})
    secreto = secreto_de(datos)
    respaldo = api.data("/auth/2fa/activar", {"codigo": codigo(secreto)})["codigos_respaldo"]
    return secreto, respaldo


def test_activar_e_ingresar_con_codigo(client, empresa):
    admin, sesion = login(client, "admin.2fa", CLAVE)
    assert sesion["seguridad"] == {"doble_factor": False, "debe_activar": False, "recomendado": True}
    assert "La clave no es correcta" in admin.post("/auth/2fa/iniciar", {"password": "otra"}).json()["message"]
    datos = admin.data("/auth/2fa/iniciar", {"password": CLAVE})
    assert datos["qr_svg"].startswith("<svg") and datos["uri"].startswith("otpauth://totp/RestaurantERP:admin.2fa")
    assert "no es correcto" in admin.post("/auth/2fa/activar", {"codigo": "000000"}).json()["message"]
    secreto = secreto_de(datos)
    respaldo = admin.data("/auth/2fa/activar", {"codigo": codigo(secreto)})["codigos_respaldo"]
    assert len(respaldo) == 10 and re.fullmatch(r"[A-Z0-9]{4}-[A-Z0-9]{4}", respaldo[0])

    # La clave sola ya no da sesión
    sin_codigo = Api(client).post("/login", {"usuario": "admin.2fa", "password": CLAVE}).json()
    assert sin_codigo["data"] == {"requiere_codigo": True}
    assert "token" not in sin_codigo["data"]
    assert Api(client).post("/login", {"usuario": "admin.2fa", "password": CLAVE, "codigo": "123456"}).status_code == 400

    # Con el código siguiente entra; el mismo código no sirve dos veces
    actual = codigo(secreto, 1)
    ok = Api(client).data("/login", {"usuario": "admin.2fa", "password": CLAVE, "codigo": actual})
    assert ok["token"] and ok["seguridad"]["doble_factor"] is True
    assert Api(client).post("/login", {"usuario": "admin.2fa", "password": CLAVE, "codigo": actual}).status_code == 400

    # Un código de respaldo sirve una sola vez
    ok = Api(client).data("/login", {"usuario": "admin.2fa", "password": CLAVE, "codigo": respaldo[0].lower()})
    assert ok["token"]
    assert Api(client).post("/login", {"usuario": "admin.2fa", "password": CLAVE, "codigo": respaldo[0]}).status_code == 400
    limiter.reset()
    estado = Api(client, ok["token"]).data("/auth/2fa/estado")
    assert estado["activo"] is True and estado["codigos_restantes"] == 9


def test_limite_de_codigos_y_pin(client, empresa):
    duena = empresa
    # El mesero entra con PIN en la tablet del Salón
    duena.data("/usuario/pin", {"usuario_id": find(duena.data("/usuario/list"), usuario="mesero.2fa")["id"], "pin": "5937"})
    creado = duena.data("/dispositivo/create", {"nombre": "Tablet Segura", "tipo": "zona",
                                                "zona_id": find(duena.data("/zona/list"), nombre="Salón")["id"]}, expect=201)
    tablet = Api(client).data("/dispositivo/emparejar", {"codigo": creado["codigo"]})["token"]
    assert Api(client).data("/dispositivo/pin", {"token": tablet, "pin": "5937"})["token"]
    mesero, _ = login(client, "mesero.2fa", CLAVE)
    activar(mesero)

    SECRETOS["duena.2fa"], _ = activar(duena)
    for _ in range(5):
        assert Api(client).post("/login", {"usuario": "duena.2fa", "password": CLAVE, "codigo": "111111"}).status_code == 400
    assert Api(client).post("/login", {"usuario": "duena.2fa", "password": CLAVE, "codigo": "111111"}).status_code == 429
    limiter.reset()

    # Con verificación en dos pasos el PIN ya no basta
    respuesta = Api(client).post("/dispositivo/pin", {"token": tablet, "pin": "5937"})
    assert respuesta.status_code == 409 and "usuario, clave y código" in respuesta.json()["message"]


def test_exigir_a_los_administradores_y_quitar(client, empresa):
    limiter.reset()
    duena_datos = Api(client).post("/login", {"usuario": "duena.2fa", "password": CLAVE}).json()["data"]
    assert duena_datos == {"requiere_codigo": True}
    duena = Api(client, Api(client).data("/login", {"usuario": "duena.2fa", "password": CLAVE,
                                                    "codigo": codigo(SECRETOS["duena.2fa"], 1)})["token"])

    # Un nuevo administrador sin doble factor: al exigirlo solo puede ir a activarla
    duena.data("/usuario/create", {"usuario": "nuevo.2fa", "nombre": "Admin Nuevo", "password": CLAVE, "roles": ["admin_restaurante"]}, expect=201)
    admin_2fa = find(duena.data("/usuario/list"), usuario="admin.2fa")
    assert admin_2fa["doble_factor"] is True
    assert duena.data("/usuario/2fa/exigir", {"exigir": True})["exigir"] is True
    nuevo, sesion = login(client, "nuevo.2fa", CLAVE)
    assert sesion["seguridad"]["debe_activar"] is True
    bloqueado = nuevo.post("/usuario/list")
    assert bloqueado.status_code == 403 and bloqueado.json()["detail"]["codigo"] == "activar_2fa"
    assert nuevo.data("/auth/2fa/estado")["exigido"] is True
    activar(nuevo)
    assert nuevo.post("/usuario/list").status_code == 200
    assert "exige" in nuevo.post("/auth/2fa/desactivar", {"password": CLAVE, "codigo": "000000"}).json()["message"]
    # Al mesero no se le exige: no es administrador
    assert nuevo.data("/auth/sesion")["seguridad"]["debe_activar"] is False
    mesero = nuevo

    # Perdió el celular: la dueña se la quita y debe activarla de nuevo; uno no se la quita a sí mismo
    assert "Mi cuenta" in duena.post("/usuario/2fa/quitar", {"usuario_id": find(duena.data("/usuario/list"), usuario="duena.2fa")["id"]}).json()["message"]
    duena.data("/usuario/2fa/quitar", {"usuario_id": admin_2fa["id"]})
    _, sesion = login(client, "admin.2fa", CLAVE)
    assert sesion["seguridad"] == {"doble_factor": False, "debe_activar": True, "recomendado": True}
    duena.data("/usuario/2fa/exigir", {"exigir": False})
    assert mesero.post("/usuario/2fa/exigir", {"exigir": True}).status_code == 403


def test_superadministrador_en_el_servidor_real(client, monkeypatch):
    monkeypatch.setenv("EXIGIR_2FA_PLATAFORMA", "1")
    soporte, sesion = login(client, "soporte", "Soporte12345")
    assert sesion["seguridad"]["debe_activar"] is True
    respuesta = soporte.post("/plataforma/empresa/list")
    assert respuesta.status_code == 403 and respuesta.json()["detail"]["codigo"] == "activar_2fa"
    assert soporte.data("/auth/2fa/estado")["activo"] is False
