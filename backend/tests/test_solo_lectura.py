"""
Estados del contrato (doc 02A, sección 3): suspendido consulta y descarga sin operar; cancelado solo descarga durante
un plazo; lo público no recibe pedidos ni cobros; y reactivar devuelve todo sin perder datos.
"""
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
import pytest
from conftest import Api, key, login, product_id, table, qr_token
from main import app
from Middleware.jwt_bearer import JWTBearer
from Utils.acceso import RUTAS_LECTURA, RUTAS_EXPORTACION, acceso_de, DIAS_EXPORTACION
from Config.db import SessionLocal
from Models.contrato_model import ContratoModel
from Models.turno_mesero_model import TurnoMeseroModel


@pytest.fixture
def contrato_napoli(client, napoli):
    """ Cambia el contrato de Napoli durante la prueba y al final lo deja activo """
    soporte, _ = login(client, "soporte", "Soporte12345")
    restaurante_id = napoli["napoli"][1]["restaurante"]["id"]

    def cambiar(estado):
        soporte.data("/plataforma/contrato/update", {"restaurante_id": restaurante_id, "estado": estado, "modulos": ["pedidos"]})
    yield cambiar
    cambiar("activo")


def rutas_con_sesion():
    # FastAPI guarda cada router incluido como un objeto aparte: se recorren sus rutas originales
    rutas = [ruta for incluido in app.routes for ruta in getattr(getattr(incluido, "original_router", None), "routes", [])]
    encontradas = [r.path for r in rutas if any(isinstance(d.dependency, JWTBearer) for d in getattr(r, "dependencies", []))]
    assert len(encontradas) > 200  # si esto se vacía, las pruebas de abajo no estarían revisando nada
    return encontradas


def test_lista_de_lectura_sin_rutas_inventadas():
    assert RUTAS_LECTURA <= set(rutas_con_sesion())


def test_toda_ruta_fuera_de_la_lista_queda_bloqueada(client, napoli, contrato_napoli):
    admin, _ = napoli["napoli"]
    contrato_napoli("suspendido")
    for ruta in set(rutas_con_sesion()) - RUTAS_LECTURA:
        respuesta = admin.post(ruta)
        assert respuesta.status_code == 403, ruta
        assert respuesta.json()["detail"]["codigo"] in ("solo_lectura", "permiso_insuficiente", "modulo_no_contratado"), ruta


def test_suspendido_consulta_y_descarga_pero_no_opera(client, napoli, contrato_napoli):
    admin, _ = napoli["napoli"]
    mesero, ficha = napoli["mesero.napoli"]
    publico = Api(client)
    mesa = table(mesero, "Mesa 1")
    producto = product_id(admin, "Pizza margarita")
    token = qr_token(admin, "Mesa 1")
    contrato_napoli("suspendido")

    sesion = admin.data("/auth/sesion")
    assert sesion["acceso"]["modo"] == "lectura" and "suspendido" in sesion["acceso"]["mensaje"] and "pedidos" in sesion["modulos"]
    # Sigue viendo su información
    assert admin.data("/producto/list") and mesero.data("/mesa/list") and admin.post("/reporte/ventas").status_code == 200
    assert admin.post("/exportacion/generar", {"conjunto": "productos", "formato": "csv"}).status_code == 200

    # No registra cambios
    orden = mesero.post("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(), "items": [{"producto_id": producto, "cantidad": 1}]})
    assert orden.status_code == 403 and orden.json()["detail"]["codigo"] == "solo_lectura"
    assert admin.post("/producto/update", {"producto_id": producto, "nombre": "Otro"}).json()["detail"]["codigo"] == "solo_lectura"
    # La contraseña y la sesión siguen funcionando
    assert admin.post("/auth/cambiar_password", {"password_actual": "mala-clave", "password_nueva": "x" * 10}).status_code == 400

    # Lo público no recibe pedidos
    assert publico.data("/publico/qr", {"token": token})["disponible"] is False
    assert publico.post("/publico/orden/create", {"token": token, "clave_idempotencia": key(),
                                                  "items": [{"producto_id": producto, "cantidad": 1}]}).status_code == 409

    # Entrar no abre turno de mesero: entrar a consultar no es trabajar
    db = SessionLocal()
    try:
        db.query(TurnoMeseroModel).filter(TurnoMeseroModel.usuario_id == ficha["usuario"]["id"], TurnoMeseroModel.estado == "abierto").update(
            {"estado": "cerrado", "fin": datetime.now(timezone.utc)})
        db.commit()
    finally:
        db.close()
    _, ingreso = login(client, "mesero.napoli")
    assert ingreso["acceso"]["modo"] == "lectura"
    assert mesero.data("/turno_mesero/actual") is None

    contrato_napoli("activo")
    assert admin.data("/auth/sesion")["acceso"]["modo"] == "completo"
    creada = mesero.post("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(), "items": [{"producto_id": producto, "cantidad": 1}]})
    assert creada.status_code == 201


def test_cancelado_solo_exporta_durante_el_plazo(client, napoli, contrato_napoli):
    admin, _ = napoli["napoli"]
    mesero, _ = napoli["mesero.napoli"]
    contrato_napoli("cancelado")

    sesion = admin.data("/auth/sesion")
    hasta = date.fromisoformat(str(sesion["acceso"]["hasta"]))
    assert sesion["acceso"]["modo"] == "exportacion" and hasta > date.today()
    assert set(sesion["permisos"]) <= {"datos.exportar", "nomina.exportar", "clientes.exportar"}
    # Baja también lo de sus módulos (RN-ONB-04), pero nada más
    assert admin.post("/exportacion/generar", {"conjunto": "productos", "formato": "xlsx"}).status_code == 200
    assert admin.post("/exportacion/generar", {"conjunto": "ordenes", "formato": "csv", "desde": str(date.today() - timedelta(days=5)), "hasta": str(date.today())}).status_code in (200, 409)
    assert admin.post("/producto/list").status_code == 403
    # Quien no puede exportar ya no entra
    assert mesero.post("/auth/sesion").status_code == 401

    # Terminado el plazo, nadie entra
    db = SessionLocal()
    try:
        contrato = db.query(ContratoModel).filter(ContratoModel.restaurante_id == sesion["restaurante"]["id"]).first()
        contrato.cancelado_en = datetime.now(timezone.utc) - timedelta(days=DIAS_EXPORTACION + 2)
        db.commit()
    finally:
        db.close()
    assert admin.post("/auth/sesion").status_code == 401
    respuesta = Api(client).post("/login", {"usuario": "napoli", "password": "demo1234"})
    assert respuesta.status_code == 403 and "plazo" in respuesta.json()["message"]


def test_modo_de_acceso_segun_estados():
    hoy = date(2026, 10, 30)
    hace = lambda dias: datetime(2026, 10, 30, tzinfo=timezone.utc) - timedelta(days=dias)  # noqa: E731
    empresa = lambda estado="activa", cancelada_en=None: SimpleNamespace(estado=estado, cancelada_en=cancelada_en)  # noqa: E731
    contrato = lambda estado="activo", fin=None, cancelado_en=None: SimpleNamespace(estado=estado, fecha_fin=fin, cancelado_en=cancelado_en)  # noqa: E731

    assert acceso_de(empresa(), contrato(), hoy)[0] == "completo"
    assert acceso_de(empresa(), contrato("prueba", hoy), hoy)[0] == "completo"
    assert acceso_de(empresa(), contrato("prueba", hoy - timedelta(days=1)), hoy)[0] == "lectura"
    assert acceso_de(empresa("suspendida"), contrato(), hoy)[0] == "lectura"
    assert acceso_de(empresa(), contrato("suspendido"), hoy)[0] == "lectura"
    assert acceso_de(empresa("cancelada", hace(10)), contrato(), hoy)[0] == "exportacion"
    assert acceso_de(empresa("cancelada", hace(DIAS_EXPORTACION)), contrato(), hoy)[0] == "exportacion"
    assert acceso_de(empresa("cancelada", hace(DIAS_EXPORTACION + 1)), contrato(), hoy)[0] is None
    assert acceso_de(empresa(), contrato("cancelado", None, hace(DIAS_EXPORTACION + 1)), hoy)[0] is None
    assert acceso_de(empresa(), None, hoy)[0] == "completo"
    assert RUTAS_EXPORTACION < RUTAS_LECTURA
