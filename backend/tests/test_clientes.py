"""
Clientes (doc 25) con tratamiento de datos (doc 32A): consentimiento, reconocimiento por teléfono,
historial, exportación y anonimización.
"""
from conftest import Api, key, find, product_id, table, qr_token


def test_registro_exige_autorizacion_y_telefono_unico(esquina):
    caja, _ = esquina["caja.esquina"]
    base = {"nombre": "Juana Pérez", "telefono": "300 123 4567"}
    response = caja.post("/cliente/create", base)
    assert response.status_code == 400 and "tratamiento" in response.json()["message"]

    cliente = caja.data("/cliente/create", {**base, "acepta_datos": True}, expect=201)
    assert cliente["telefono"] == "573001234567"
    assert cliente["acepta_datos"] is True and cliente["acepta_comercial"] is False

    response = caja.post("/cliente/create", {**base, "nombre": "Otra", "telefono": "3001234567", "acepta_datos": True})
    assert response.status_code == 400
    assert caja.post("/cliente/create", {"nombre": "X", "telefono": "12", "acepta_datos": True}).status_code == 400

    encontrados = caja.data("/cliente/buscar", {"texto": "1234567"})
    assert [c["nombre"] for c in encontrados] == ["Juana Pérez"]


def test_orden_de_mostrador_reconoce_o_crea_al_cliente(esquina):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    externa = table(caja, "Para llevar", incluir_externa=True)
    limonada = product_id(admin, "Limonada natural")

    def pedir(nombre, telefono, acepta):
        return caja.data("/orden/create", {"mesa_id": externa["id"], "clave_idempotencia": key(), "cliente_nombre": nombre,
                                           "cliente_telefono": telefono, "acepta_datos": acepta,
                                           "items": [{"producto_id": limonada, "cantidad": 1}]}, expect=201)

    # Sin autorización la orden guarda el teléfono para gestionarla, pero no se crea ficha
    sin_ficha = pedir("Mario", "3109998877", False)
    assert sin_ficha["cliente_id"] is None and sin_ficha["cliente_telefono"] == "3109998877"
    assert caja.data("/cliente/buscar", {"texto": "3109998877"}) == []

    # Con autorización se crea; la siguiente orden con el mismo teléfono lo reconoce
    primera = pedir("Mario Ruiz", "310 999 8877", True)
    segunda = pedir("Mario", "3109998877", False)
    assert primera["cliente_id"] and segunda["cliente_id"] == primera["cliente_id"]

    ficha = admin.data("/cliente/get", {"cliente_id": primera["cliente_id"]})
    assert ficha["historial"]["ordenes"] == 2
    assert ficha["historial"]["favoritos"][0]["nombre"] == "Limonada natural"
    # Consultar datos personales queda en la auditoría (RN-CLI-06)
    assert any(r["entidad_id"] == ficha["id"] for r in admin.data("/auditoria/list", {"accion": "cliente_consultado"}))


def test_qr_para_llevar_con_aviso_de_datos(client, esquina):
    admin, _ = esquina["admin.esquina"]
    token = qr_token(admin, "Para llevar")
    carta = Api(client).data("/publico/qr", {"token": token})
    assert "La Esquina Centro usará tu nombre y teléfono" in carta["aviso_datos"]
    pedido = Api(client).data("/publico/orden/create", {
        "token": token, "clave_idempotencia": key(), "cliente_nombre": "Sara", "cliente_telefono": "3205550000",
        "acepta_datos": True, "items": [{"producto_id": product_id(admin, "Agua sin gas"), "cantidad": 1}],
    }, expect=201)
    assert pedido["cliente_nombre"] == "Sara"
    cliente = find(admin.data("/cliente/buscar", {"texto": "3205550000"}), nombre="Sara")
    exportado = admin.data("/cliente/exportar", {"cliente_id": cliente["id"]})
    assert exportado["consentimientos"]["datos"]["canal"] == "carta"
    assert exportado["consentimientos"]["datos"]["version_aviso"] == 1


def test_consentimiento_comercial_revocable_y_anonimizacion(esquina):
    admin, _ = esquina["admin.esquina"]
    caja, _ = esquina["caja.esquina"]
    cliente = caja.data("/cliente/create", {"nombre": "Lucía Gómez", "telefono": "3017776655", "acepta_datos": True,
                                            "acepta_comercial": True, "correo": "lucia@correo.co"}, expect=201)
    assert cliente["acepta_comercial"] is True
    caja.data("/cliente/direccion/save", {"cliente_id": cliente["id"], "nombre": "Casa", "direccion": "Calle 45 # 12-30",
                                          "barrio": "Centro"})

    revocado = admin.data("/cliente/update", {**cliente, "cliente_id": cliente["id"], "acepta_comercial": False})
    assert revocado["acepta_comercial"] is False

    # El cajero no anonimiza ni exporta
    assert caja.post("/cliente/anonimizar", {"cliente_id": cliente["id"], "motivo": "Lo pidió"}).status_code == 403
    assert caja.post("/cliente/exportar", {"cliente_id": cliente["id"]}).status_code == 403

    externa = table(caja, "Para llevar", incluir_externa=True)
    orden = caja.data("/orden/create", {"mesa_id": externa["id"], "clave_idempotencia": key(), "cliente_nombre": "Lucía",
                                        "cliente_telefono": "3017776655",
                                        "items": [{"producto_id": product_id(admin, "Agua sin gas"), "cantidad": 1}]}, expect=201)
    admin.data("/cliente/anonimizar", {"cliente_id": cliente["id"], "motivo": "Solicitud de supresión del titular"})
    anonimo = admin.data("/cliente/get", {"cliente_id": cliente["id"]})
    assert anonimo["nombre"] == "Cliente anonimizado" and anonimo["telefono"] is None and anonimo["direcciones"] == []
    # La venta se conserva sin datos personales
    venta = caja.data("/orden/get", {"orden_id": orden["id"]})
    assert venta["total"] == 3500 and venta["cliente_nombre"] is None and venta["cliente_telefono"] is None


def test_clientes_aislados_entre_empresas(esquina, napoli):
    caja, _ = esquina["caja.esquina"]
    admin_napoli, _ = napoli["napoli"]
    cliente = caja.data("/cliente/create", {"nombre": "Pedro Solo", "telefono": "3112223344", "acepta_datos": True}, expect=201)
    assert admin_napoli.post("/cliente/get", {"cliente_id": cliente["id"]}).status_code == 404
    assert admin_napoli.data("/cliente/buscar", {"texto": "3112223344"}) == []
    # El mismo teléfono es otro cliente en otra empresa (RN-CLI-01)
    admin_napoli.data("/cliente/create", {"nombre": "Pedro en Napoli", "telefono": "3112223344", "acepta_datos": True}, expect=201)
