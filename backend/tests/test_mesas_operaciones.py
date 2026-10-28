from conftest import key, find, product_id, table, pay_table


def pedir(api, mesa_id, admin, producto="Agua sin gas", cantidad=1):
    return api.data("/orden/create", {"mesa_id": mesa_id, "clave_idempotencia": key(),
                                      "items": [{"producto_id": product_id(admin, producto), "cantidad": cantidad}]}, expect=201)


def test_trasladar_mesa_mueve_ordenes_y_cuenta(esquina):
    mesero, _ = esquina["mesero.salon"]
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    origen, destino = table(admin, "Mesa 1"), table(admin, "Mesa 2")
    for mesa in [origen, destino]:
        if mesa["estado"] != "libre":
            pay_table(caja, mesa_id=mesa["id"])

    orden = pedir(mesero, origen["id"], admin)
    caja.data("/cuenta/abrir", {"mesa_id": origen["id"]})

    # El mesero no traslada (permiso específico, doc 29)
    assert mesero.post("/mesa/trasladar", {"mesa_id": origen["id"], "destino_id": destino["id"]}).status_code == 403
    caja.data("/mesa/trasladar", {"mesa_id": origen["id"], "destino_id": destino["id"]})

    assert table(admin, "Mesa 1")["estado"] == "libre"
    assert table(admin, "Mesa 2")["estado"] == "con_orden"
    assert mesero.data("/orden/get", {"orden_id": orden["id"]})["mesa"] == "Mesa 2"
    cuenta = caja.data("/cuenta/abrir", {"mesa_id": destino["id"]})
    assert cuenta["mesa"] == "Mesa 2" and cuenta["subtotal"] == 3500

    # No se traslada a una mesa ocupada
    pedir(mesero, origen["id"], admin)
    response = caja.post("/mesa/trasladar", {"mesa_id": origen["id"], "destino_id": destino["id"]})
    assert response.status_code == 409 and "Unir" in response.json()["message"]
    pay_table(caja, mesa_id=origen["id"])
    pay_table(caja, mesa_id=destino["id"])


def test_unir_mesas_se_cobran_juntas(esquina):
    mesero, _ = esquina["mesero.salon"]
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    principal, otra = table(admin, "Mesa 1"), table(admin, "Mesa 2")
    pedir(mesero, principal["id"], admin, "Limonada natural", 2)
    pedir(mesero, otra["id"], admin, "Papas a la francesa", 1)
    caja.data("/cuenta/abrir", {"mesa_id": otra["id"]})

    caja.data("/mesa/unir", {"mesa_id": principal["id"], "otras": [otra["id"]]})
    assert table(admin, "Mesa 2")["estado"] == "libre"
    cuenta = caja.data("/cuenta/abrir", {"mesa_id": principal["id"]})
    assert cuenta["subtotal"] == 12000 + 7000 and len(cuenta["ordenes"]) == 2

    # Una mesa con pagos no se une
    pedir(mesero, otra["id"], admin)
    cuenta_otra = caja.data("/cuenta/abrir", {"mesa_id": otra["id"]})
    caja.data("/cuenta/pagar", {"cuenta_id": cuenta_otra["id"], "clave_idempotencia": key(), "pagos": [
        {"medio_pago_id": find(caja.data("/caja/estado")["medios"], nombre="Efectivo")["id"], "monto": 1000}]})
    response = caja.post("/mesa/unir", {"mesa_id": principal["id"], "otras": [otra["id"]]})
    assert response.status_code == 409
    pay_table(caja, mesa_id=principal["id"])
    pay_table(caja, mesa_id=otra["id"])


def test_reasignar_mesero(esquina):
    mesero, sesion = esquina["mesero.salon"]
    admin, _ = esquina["admin.esquina"]
    caja, _ = esquina["caja.esquina"]
    mesa = table(admin, "Mesa 1")
    pedir(mesero, mesa["id"], admin)

    meseros = admin.data("/mesa/meseros", {"mesa_id": mesa["id"]})
    assert [m["nombre"] for m in meseros] == ["Carlos Mesero"]
    # Ana atiende Terraza, no Salón
    ana = admin.data("/usuario/list")
    ana_id = find(ana, usuario="mesero.terraza")["id"]
    assert admin.post("/mesa/reasignar", {"mesa_id": mesa["id"], "mesero_id": ana_id}).status_code == 400
    assert caja.post("/mesa/reasignar", {"mesa_id": mesa["id"], "mesero_id": sesion["usuario"]["id"]}).status_code == 403
    admin.data("/mesa/reasignar", {"mesa_id": mesa["id"], "mesero_id": sesion["usuario"]["id"]})
    assert any(r["accion"] == "mesa_reasignada" for r in admin.data("/auditoria/list"))
    pay_table(caja, mesa_id=mesa["id"])
