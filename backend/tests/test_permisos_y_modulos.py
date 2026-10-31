from conftest import Api, login, key, find, product_id, table


def test_mesero_no_administra_catalogo_ni_estructura(esquina):
    mesero, _ = esquina["mesero.salon"]
    response = mesero.post("/producto/create", {"categoria_id": 1, "nombre": "X", "precio": 1})
    assert response.status_code == 403
    assert response.json()["detail"]["codigo"] == "permiso_insuficiente"
    assert mesero.post("/zona/create", {"nombre": "Nueva"}).status_code == 403
    assert mesero.post("/usuario/list").status_code == 403


def test_mesero_solo_opera_sus_zonas(esquina):
    mesero_salon, _ = esquina["mesero.salon"]
    mesero_terraza, _ = esquina["mesero.terraza"]
    admin, _ = esquina["admin.esquina"]

    assert {m["zona_id"] for m in mesero_terraza.data("/mesa/list")} == {
        find(admin.data("/zona/list"), nombre="Terraza")["id"]}

    mesa_salon = table(admin, "Mesa 1")
    response = mesero_terraza.post("/orden/create", {
        "mesa_id": mesa_salon["id"], "clave_idempotencia": key(),
        "items": [{"producto_id": product_id(admin, "Limonada natural"), "cantidad": 1}]})
    assert response.status_code == 403

    orden = mesero_salon.data("/orden/create", {
        "mesa_id": mesa_salon["id"], "clave_idempotencia": key(),
        "items": [{"producto_id": product_id(admin, "Limonada natural"), "cantidad": 1}]}, expect=201)
    assert mesero_terraza.post("/orden/get", {"orden_id": orden["id"]}).status_code == 403


def test_cocina_solo_ve_su_punto(esquina):
    cocina, sesion = esquina["cocina.esquina"]
    assert [p["nombre"] for p in sesion["puntos"]] == ["Cocina"]
    admin, _ = esquina["admin.esquina"]
    bar = find(admin.data("/punto_produccion/list"), nombre="Bar")
    assert cocina.post("/cocina/comandas", {"punto_produccion_id": bar["id"]}).status_code == 403
    assert cocina.post("/orden/create", {}).status_code == 403


def test_nadie_se_cambia_sus_propios_roles(esquina):
    admin, sesion = esquina["admin.esquina"]
    yo = find(admin.data("/usuario/list"), usuario="admin.esquina")
    response = admin.post("/usuario/update", {**yo, "usuario_id": yo["id"], "roles": ["admin_restaurante", "cajero"]})
    assert response.status_code == 400
    assert admin.post("/usuario/change_status", {"usuario_id": yo["id"], "activo": False}).status_code == 400


def test_admin_restaurante_no_crea_admin_de_empresa(esquina):
    admin, _ = esquina["admin.esquina"]
    response = admin.post("/usuario/create", {"usuario": "nuevo.dueno", "nombre": "Nuevo", "password": "clave12345",
                                              "roles": ["admin_empresa"]})
    assert response.status_code == 400


def test_usuario_desactivado_pierde_la_sesion_al_instante(client, esquina):
    admin, _ = esquina["admin.esquina"]
    nuevo = admin.data("/usuario/create", {"usuario": "temporal", "nombre": "Mesero temporal", "password": "clave12345",
                                           "roles": ["mesero"], "zonas": [find(admin.data("/zona/list"), nombre="Salón")["id"]]},
                       expect=201)
    temporal, _ = login(client, "temporal", "clave12345")
    temporal.data("/mesa/list")

    admin.data("/usuario/change_status", {"usuario_id": nuevo["id"], "activo": False})
    assert temporal.post("/mesa/list").status_code == 401


def test_cambio_de_rol_aplica_de_inmediato(client, esquina):
    admin, _ = esquina["admin.esquina"]
    salon = find(admin.data("/zona/list"), nombre="Salón")["id"]
    nuevo = admin.data("/usuario/create", {"usuario": "rotativo", "nombre": "Rotativo", "password": "clave12345",
                                           "roles": ["mesero"], "zonas": [salon]}, expect=201)
    rotativo, _ = login(client, "rotativo", "clave12345")
    assert rotativo.post("/producto/agotado", {"producto_id": 1, "agotado": False}).status_code == 403

    admin.data("/usuario/update", {**nuevo, "usuario_id": nuevo["id"], "roles": ["mesero", "cajero"]})
    assert rotativo.post("/orden/list").status_code == 200
    assert "ordenes.crear_externa" in rotativo.data("/auth/sesion")["permisos"]


def test_modulo_no_contratado_y_contrato_suspendido(client, napoli):
    soporte, _ = login(client, "soporte", "Soporte12345")
    _, sesion = napoli["napoli"]
    mesero, _ = napoli["mesero.napoli"]
    restaurante_id = sesion["restaurante"]["id"]

    # Sin el módulo pedidos: la ruta responde 403 modulo_no_contratado (RN-API-03)
    soporte.data("/plataforma/contrato/update", {"restaurante_id": restaurante_id, "estado": "activo", "modulos": []})
    try:
        response = mesero.post("/mesa/list")
        assert response.status_code == 403
        assert response.json()["detail"]["codigo"] == "modulo_no_contratado"
        # Los permisos del módulo dejan de ser efectivos (RN-PER-04)
        assert "ordenes.crear_mesa" not in mesero.data("/auth/sesion")["permisos"]
    finally:
        soporte.data("/plataforma/contrato/update", {"restaurante_id": restaurante_id, "estado": "activo",
                                                     "modulos": ["pedidos"]})

    # Contrato suspendido: se consulta, pero no se crean órdenes (el detalle está en test_solo_lectura)
    soporte.data("/plataforma/contrato/update", {"restaurante_id": restaurante_id, "estado": "suspendido",
                                                 "modulos": ["pedidos"]})
    try:
        assert mesero.post("/mesa/list").status_code == 200
        assert mesero.post("/orden/create").json()["detail"]["codigo"] == "solo_lectura"
        admin, _ = napoli["napoli"]
        assert admin.post("/zona/create").json()["detail"]["codigo"] == "solo_lectura"
    finally:
        soporte.data("/plataforma/contrato/update", {"restaurante_id": restaurante_id, "estado": "activo",
                                                     "modulos": ["pedidos"]})
    assert mesero.post("/mesa/list").status_code == 200


def test_dependencias_de_modulos(client, napoli):
    soporte, _ = login(client, "soporte", "Soporte12345")
    _, sesion = napoli["napoli"]
    response = soporte.post("/plataforma/contrato/update", {
        "restaurante_id": sesion["restaurante"]["id"], "estado": "activo", "modulos": ["domicilios"]})
    assert response.status_code == 400
    assert "requiere" in response.json()["message"]


def test_solo_plataforma_gestiona_empresas(client, esquina):
    admin, _ = esquina["esquina"]
    assert admin.post("/plataforma/empresa/list").status_code == 403


def test_alta_de_empresa_crea_lo_necesario_para_operar(client):
    soporte, _ = login(client, "soporte", "Soporte12345")
    empresa = soporte.data("/plataforma/empresa/create", {
        "nombre_comercial": "Panadería Sol",
        "admin": {"usuario": "sol", "nombre": "Dueña Sol", "password": "clave12345"},
        "restaurante": {"nombre": "Sol Centro", "tipo": "panaderia", "hora_inicio_jornada": "05:00"},
    }, expect=201)
    [restaurante] = empresa["restaurantes"]
    assert restaurante["contrato"]["estado"] == "prueba"
    assert restaurante["contrato"]["modulos"] == ["base", "pedidos"]
    assert restaurante["url_para_llevar"].startswith("http://carta.test/q/")

    # Lo creado automáticamente (doc 07, sección 3): cocina, carta, salón, mostrador y mesa externa
    dueno, sesion = login(client, "sol", "clave12345")
    assert [p["nombre"] for p in sesion["puntos"]] == ["Cocina"]
    assert {z["nombre"] for z in dueno.data("/zona/list")} == {"Salón", "Mostrador"}
    externa = find(dueno.data("/mesa/list", {"incluir_externa": True}), tipo="externa")
    assert externa["nombre"] == "Para llevar"
