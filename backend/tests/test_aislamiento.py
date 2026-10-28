"""
Aislamiento entre empresas (RG-16, doc 02A): ninguna petición devuelve ni modifica datos de otra empresa.
Cada prueba toma ids reales de Napoli e intenta usarlos con una sesión de La Esquina.
"""
import pytest
from conftest import Api, key, find, product_id, table, qr_token
from Utils.jwt_manager import create_token


@pytest.fixture(scope="module")
def ajenos(napoli):
    """ Ids reales de la otra empresa """
    admin, sesion = napoli["napoli"]
    mesero, _ = napoli["mesero.napoli"]
    mesa = table(admin, "Mesa 1")
    producto = product_id(admin, "Pizza margarita")
    orden = mesero.data("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(),
                                          "items": [{"producto_id": producto, "cantidad": 1}]}, expect=201)
    return {
        "restaurante_id": sesion["restaurante"]["id"],
        "zona": find(admin.data("/zona/list"), nombre="Salón"),
        "mesa": mesa,
        "producto": producto,
        "categoria": find(admin.data("/categoria/list"), nombre="Pizzas"),
        "carta": admin.data("/carta/list")[0],
        "punto": admin.data("/punto_produccion/list")[0],
        "orden": orden,
        "usuario": find(admin.data("/usuario/list"), usuario="mesero.napoli"),
    }


def test_listados_solo_muestran_lo_propio(esquina, ajenos):
    admin, _ = esquina["esquina"]
    assert ajenos["zona"]["id"] not in [z["id"] for z in admin.data("/zona/list", {"todas": True})]
    assert ajenos["mesa"]["id"] not in [m["id"] for m in admin.data("/mesa/list", {"todas": True})]
    assert ajenos["producto"] not in [p["id"] for p in admin.data("/producto/list", {"todos": True})]
    assert ajenos["orden"]["id"] not in [o["id"] for o in admin.data("/orden/list", {"vista": "jornada"})]
    assert "mesero.napoli" not in [u["usuario"] for u in admin.data("/usuario/list", {"todos": True})]
    assert all((r["entidad"], r["entidad_id"]) != ("orden", ajenos["orden"]["id"]) for r in admin.data("/auditoria/list"))


@pytest.mark.parametrize("path,body", [
    ("/orden/get", lambda a: {"orden_id": a["orden"]["id"]}),
    ("/orden/aprobar", lambda a: {"orden_id": a["orden"]["id"]}),
    ("/orden/entregar", lambda a: {"orden_id": a["orden"]["id"]}),
    ("/orden/cancelar_item", lambda a: {"orden_item_id": a["orden"]["items"][0]["id"], "motivo": "intento"}),
    ("/orden/agregar_items", lambda a: {"orden_id": a["orden"]["id"], "clave_idempotencia": key(),
                                        "items": [{"producto_id": a["producto"], "cantidad": 1}]}),
    ("/orden/carta", lambda a: {"mesa_id": a["mesa"]["id"]}),
    ("/mesa/cerrar", lambda a: {"mesa_id": a["mesa"]["id"]}),
    ("/mesa/change_status", lambda a: {"mesa_id": a["mesa"]["id"], "bloqueada": True}),
    ("/qr/regenerar", lambda a: {"mesa_id": a["mesa"]["id"]}),
    ("/zona/change_status", lambda a: {"zona_id": a["zona"]["id"], "activo": False}),
    ("/producto/agotado", lambda a: {"producto_id": a["producto"], "agotado": True}),
    ("/carta/get", lambda a: {"carta_id": a["carta"]["id"]}),
    ("/usuario/get", lambda a: {"usuario_id": a["usuario"]["id"]}),
    ("/cocina/comandas", lambda a: {"punto_produccion_id": a["punto"]["id"]}),
    ("/cocina/abrir", lambda a: {"comanda_id": a["orden"]["comandas"][0]["id"]}),
])
def test_ids_de_otra_empresa_responden_como_inexistentes(esquina, ajenos, path, body):
    admin, _ = esquina["esquina"]
    response = admin.post(path, body(ajenos))
    assert response.status_code in [403, 404], f"{path} respondió {response.status_code}: {response.text}"


def test_no_se_pueden_usar_ids_ajenos_al_crear(esquina, ajenos):
    admin, _ = esquina["esquina"]
    # Producto con categoría ajena
    response = admin.post("/producto/create", {"categoria_id": ajenos["categoria"]["id"], "nombre": "Intruso", "precio": 1})
    assert response.status_code == 404
    # Zona con carta o punto ajenos
    assert admin.post("/zona/create", {"nombre": "Intrusa", "carta_id": ajenos["carta"]["id"]}).status_code == 404
    assert admin.post("/zona/create", {"nombre": "Intrusa", "punto_produccion_id": ajenos["punto"]["id"]}).status_code == 404
    # Orden en una mesa ajena o con un producto ajeno
    admin, _ = esquina["admin.esquina"]
    response = admin.post("/orden/create", {"mesa_id": ajenos["mesa"]["id"], "clave_idempotencia": key(),
                                            "items": [{"producto_id": ajenos["producto"], "cantidad": 1}]})
    assert response.status_code == 404
    mesa = table(admin, "Mesa 2")
    response = admin.post("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(),
                                            "items": [{"producto_id": ajenos["producto"], "cantidad": 1}]})
    assert response.status_code == 409
    # Usuario con zona ajena
    response = admin.post("/usuario/create", {"usuario": "intruso", "nombre": "Intruso", "password": "clave12345",
                                              "roles": ["mesero"], "zonas": [ajenos["zona"]["id"]]})
    assert response.status_code == 400


def test_empresa_y_restaurante_del_cliente_se_ignoran(esquina, napoli, ajenos):
    """ Mandar empresa_id o restaurante_id en el cuerpo no cambia dónde se guarda """
    admin, _ = esquina["esquina"]
    admin_napoli, _ = napoli["napoli"]
    zona = admin.data("/zona/create", {"nombre": "Patio", "empresa_id": 999, "restaurante_id": ajenos["restaurante_id"]},
                      expect=201)
    assert zona["id"] in [z["id"] for z in admin.data("/zona/list")]
    assert zona["id"] not in [z["id"] for z in admin_napoli.data("/zona/list", {"todas": True})]


def test_token_con_restaurante_ajeno_se_rechaza(client, esquina, ajenos):
    _, sesion = esquina["mesero.salon"]
    forjado = create_token({"usuario_id": sesion["usuario"]["id"], "restaurante_id": ajenos["restaurante_id"]})
    assert Api(client, forjado).post("/zona/list").status_code == 401

    admin, _ = esquina["esquina"]
    response = admin.post("/auth/cambiar_restaurante", {"restaurante_id": ajenos["restaurante_id"]})
    assert response.status_code == 403


def test_qr_ajeno_no_permite_pedir_productos_propios(client, esquina, napoli):
    """ El token del QR fija el restaurante: no se puede pedir un producto de otro restaurante con él """
    admin_napoli, _ = napoli["napoli"]
    token = qr_token(admin_napoli, "Mesa 2")
    hamburguesa = product_id(esquina["esquina"][0], "Hamburguesa clásica")
    response = Api(client).post("/publico/orden/create", {
        "token": token, "clave_idempotencia": key(), "items": [{"producto_id": hamburguesa, "cantidad": 1}]})
    assert response.status_code == 409


def test_idempotencia_por_restaurante(esquina, napoli):
    """ La misma clave en dos restaurantes crea dos órdenes distintas """
    clave = key()
    mesero, _ = esquina["mesero.salon"]
    mesero_napoli, _ = napoli["mesero.napoli"]
    uno = mesero.data("/orden/create", {"mesa_id": table(mesero, "Mesa 6")["id"], "clave_idempotencia": clave,
                                        "items": [{"producto_id": product_id(esquina["esquina"][0], "Agua sin gas"), "cantidad": 1}]},
                      expect=201)
    dos = mesero_napoli.data("/orden/create", {"mesa_id": table(mesero_napoli, "Mesa 3")["id"], "clave_idempotencia": clave,
                                               "items": [{"producto_id": product_id(napoli["napoli"][0], "Pizza napolitana"), "cantidad": 1}]},
                             expect=201)
    assert uno["id"] != dos["id"]


def test_websocket_no_suscribe_a_canales_ajenos(client, esquina, ajenos):
    cocina, _ = esquina["cocina.esquina"]
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws?token={cocina.token}&canales=punto:{ajenos['punto']['id']}") as ws:
            ws.receive_json()
