from conftest import Api, login


def test_login_devuelve_sesion_con_restaurante_y_permisos(client):
    api, data = login(client, "mesero.salon")
    assert data["restaurante"]["nombre"] == "La Esquina Centro"
    assert "ordenes.crear_mesa" in data["permisos"]
    assert "catalogo.gestionar" not in data["permisos"]
    assert [z["nombre"] for z in data["zonas"]] == ["Salón"]
    assert "pedidos" in data["modulos"]

    sesion = api.data("/auth/sesion")
    assert sesion["usuario"]["usuario"] == "mesero.salon"


def test_login_con_clave_incorrecta_falla_y_se_audita(client, esquina):
    response = Api(client).post("/login", {"usuario": "mesero.salon", "password": "otra-clave"})
    assert response.status_code == 400
    assert response.json()["message"] == "Usuario o contraseña incorrectos."

    admin, _ = esquina["admin.esquina"]
    acciones = [r["accion"] for r in admin.data("/auditoria/list", {"accion": "login_fallido"})]
    assert "login_fallido" in acciones


def test_login_se_bloquea_tras_intentos_fallidos(client):
    for _ in range(5):
        Api(client).post("/login", {"usuario": "mesero.terraza", "password": "mal"}, expect=400)
    response = Api(client).post("/login", {"usuario": "mesero.terraza", "password": "demo1234"})
    assert response.status_code == 429


def test_sin_token_o_token_invalido_responde_401(client):
    assert Api(client).post("/zona/list").status_code == 401
    assert Api(client, "token-falso").post("/zona/list").status_code == 401


def test_sin_header_accept_no_se_procesa(client, esquina):
    api, _ = esquina["admin.esquina"]
    response = client.post("/zona/list", json={}, headers={"Authorization": f"Bearer {api.token}"})
    assert response.status_code == 406


def test_validaciones_de_entrada(client, esquina):
    admin, _ = esquina["admin.esquina"]
    response = admin.post("/zona/create", {"nombre": "", "modo_qr": "libre"})
    assert response.status_code == 400
    assert "nombre" in response.json()["message"]

    response = admin.post("/zona/create", {"nombre": "Patio", "modo_qr": "cualquiera"})
    assert response.status_code == 400

    response = admin.post("/zona/create", {})
    assert response.status_code == 422
