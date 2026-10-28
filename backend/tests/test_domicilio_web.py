"""
Domicilio pedido por el cliente desde la web (doc 17A, sección 2.6): enlace o QR de domicilios, carta con zonas
de envío, datos obligatorios con autorización, confirmación de quien despacha, rechazo sin cobro, pago en línea
solo después de confirmar y límites contra el spam.
"""
from conftest import Api, key, find, product_id, qr_token


def web(admin):
    datos = admin.data("/domicilio/web/get")
    return datos, datos["url"].rsplit("/", 1)[1]


def pedido(admin, token, zona_id, telefono="3157778899", cantidad=1, **extra):
    body = {
        "token": token, "clave_idempotencia": key(), "cliente_nombre": "Laura Web", "cliente_telefono": telefono,
        "acepta_datos": True, "notas": "Sin salsas",
        "items": [{"producto_id": product_id(admin, "Papas a la francesa"), "cantidad": cantidad}],
        "entrega": {"zona_envio_id": zona_id, "direccion": "Carrera 7 # 12-30 casa 4", "barrio": "La Candelaria",
                    "indicaciones": "Timbre de la izquierda", "forma_pago": "contra_entrega"},
    }
    for campo, valor in extra.items():
        if campo == "entrega":
            body["entrega"] = {**body["entrega"], **valor}
        else:
            body[campo] = valor
    return body


def entrega_de(api, numero_texto):
    datos = api.data("/entrega/list")
    return next(e for e in datos["activas"] + datos["cerradas"] if e["orden"] == numero_texto)


def test_pedido_web_se_confirma_y_sale(client, esquina):
    admin, _ = esquina["admin.esquina"]
    caja, _ = esquina["caja.esquina"]
    publico = Api(client)
    config, token = web(admin)
    assert config["activo"] and config["aprobacion"] and config["svg"].startswith("<svg") and config["pago_en_linea"]

    carta = publico.data("/publico/qr", {"token": token})
    assert carta["tipo"] == "domicilio" and carta["disponible"] and carta["con_aprobacion"]
    assert carta["pago_en_linea"] and "40 minutos" in carta["domicilio"]["mensaje"]
    centro = find(carta["domicilio"]["zonas"], nombre="Centro")
    assert centro["tarifa"] == 3000 and find(carta["domicilio"]["zonas"], nombre="Norte")["pedido_minimo"] == 20000

    creado = publico.data("/publico/orden/create", pedido(admin, token, centro["id"]), expect=201)
    assert creado["estado"] == "pendiente_aprobacion" and creado["mesa_tipo"] == "externa"
    estado = publico.data("/publico/orden/estado", {"seguimiento": creado["seguimiento"]})
    assert estado["entrega"]["estado"] == "pendiente_asignacion" and estado["entrega"]["tarifa"] == 3000
    assert estado["entrega"]["forma_pago"] == "contra_entrega"
    # Sin confirmar no se paga: el restaurante todavía puede rechazarlo
    assert estado["pago_en_linea"] is False
    assert publico.data("/publico/pago/cuenta", {"seguimiento": creado["seguimiento"]})["disponible"] is False
    assert publico.post("/publico/pago/crear", {"seguimiento": creado["seguimiento"], "clave_idempotencia": key()}).status_code == 409

    # Quien despacha lo ve por confirmar y no lo puede asignar todavía
    entrega = entrega_de(caja, creado["numero_texto"])
    assert entrega["web"] and entrega["por_confirmar"] and entrega["telefono"] == "3157778899"
    assert entrega["direccion"].startswith("Carrera 7") and entrega["notas"] == "Sin salsas"
    d01 = find(caja.data("/domicilio/domiciliario/list"), codigo="D01")
    assert caja.post("/entrega/asignar", {"entrega_id": entrega["id"], "domiciliario_id": d01["id"]}).status_code == 409

    # El cajero no aprueba órdenes de mesa, pero sí confirma domicilios
    aprobada = caja.data("/orden/aprobar", {"orden_id": entrega["orden_id"]})
    assert aprobada["estado"] == "nueva" and aprobada["canal"] == "domicilio"
    assert not entrega_de(caja, creado["numero_texto"])["por_confirmar"]
    caja.data("/entrega/asignar", {"entrega_id": entrega["id"], "domiciliario_id": d01["id"]})

    estado = publico.data("/publico/orden/estado", {"seguimiento": creado["seguimiento"]})
    assert estado["estado"] == "nueva" and estado["pago_en_linea"] is True
    info = publico.data("/publico/pago/cuenta", {"seguimiento": creado["seguimiento"]})
    assert info["disponible"] and info["envio"] == 3000 and info["saldo"] == estado["total"] + 3000

    # Con la autorización queda el cliente con su dirección para la próxima vez
    cliente = find(admin.data("/cliente/list", {"buscar": "3157778899"})["clientes"], nombre="Laura Web")
    ficha = admin.data("/cliente/get", {"cliente_id": cliente["id"]})
    assert any(d["direccion"].startswith("Carrera 7") for d in ficha["direcciones"])


def test_pedido_web_rechazado_no_cobra(client, esquina):
    admin, _ = esquina["admin.esquina"]
    caja, _ = esquina["caja.esquina"]
    mesero, _ = esquina["mesero.salon"]
    publico = Api(client)
    _, token = web(admin)
    sur = find(publico.data("/publico/qr", {"token": token})["domicilio"]["zonas"], nombre="Sur")

    creado = publico.data("/publico/orden/create", pedido(admin, token, sur["id"], telefono="3001234567"), expect=201)
    entrega = entrega_de(caja, creado["numero_texto"])
    caja.data("/orden/rechazar", {"orden_id": entrega["orden_id"], "motivo": "Dirección fuera de cobertura"})

    cerrada = entrega_de(caja, creado["numero_texto"])
    assert cerrada["estado"] == "fallida" and cerrada["decision"] == "cancelacion"
    assert "fuera de cobertura" in cerrada["motivo_fallo"]
    estado = publico.data("/publico/orden/estado", {"seguimiento": creado["seguimiento"]})
    assert estado["estado"] == "cancelada" and estado["entrega"]["estado"] == "fallida"
    assert not [c for c in caja.data("/cuenta/pendientes") if creado["numero_texto"] in c["ordenes"]]

    # El permiso de despachar no alcanza para rechazar una orden de mesa
    mesa_token = qr_token(admin, "Mesa 6")
    de_mesa = publico.data("/publico/orden/create", {
        "token": mesa_token, "clave_idempotencia": key(),
        "items": [{"producto_id": product_id(admin, "Gaseosa 400 ml"), "cantidad": 1}]}, expect=201)
    orden = find(mesero.data("/orden/list"), numero_texto=de_mesa["numero_texto"])
    assert caja.post("/orden/rechazar", {"orden_id": orden["id"], "motivo": "Prueba"}).status_code == 403
    mesero.data("/orden/rechazar", {"orden_id": orden["id"], "motivo": "Prueba de permisos"})


def test_pedido_web_valida_datos_y_limita(client, esquina):
    admin, _ = esquina["admin.esquina"]
    publico = Api(client)
    _, token = web(admin)
    zonas = publico.data("/publico/qr", {"token": token})["domicilio"]["zonas"]
    centro, norte = find(zonas, nombre="Centro"), find(zonas, nombre="Norte")

    def crear(**extra):
        return publico.post("/publico/orden/create", pedido(admin, token, centro["id"], telefono="3112223344", **extra))

    assert crear(cliente_telefono="12ab").status_code == 400                      # celular inválido
    assert crear(cliente_telefono="123").status_code == 400
    assert crear(acepta_datos=False).status_code == 400                           # sin autorización de datos
    assert crear(entrega={"direccion": ""}).status_code == 400                    # sin dirección
    assert crear(entrega={"forma_pago": "fiado"}).status_code == 400
    minimo = publico.post("/publico/orden/create", pedido(admin, token, norte["id"], telefono="3112223344"))
    assert minimo.status_code == 400 and "mínimo" in minimo.json()["message"]

    # Tres domicilios por celular cada media hora (doc 17A, sección 5); los intentos rechazados no cuentan
    for _ in range(2):
        assert crear().status_code == 201
    tercero = pedido(admin, token, centro["id"], telefono="3112223344")
    assert publico.post("/publico/orden/create", tercero).status_code == 201
    bloqueado = crear()
    assert bloqueado.status_code == 429 and "celular" in bloqueado.json()["message"]
    # Reenviar el mismo pedido (misma clave, p. ej. por mala señal) devuelve el que ya estaba
    reintento = publico.post("/publico/orden/create", tercero)
    assert reintento.status_code == 200 and "ya estaba" in reintento.json()["message"]
    # Otro celular desde el mismo enlace sí puede pedir: el enlace lo comparten todos los clientes
    assert publico.post("/publico/orden/create", pedido(admin, token, centro["id"], telefono="3119990000")).status_code == 201


def test_pausar_y_cambiar_el_enlace(client, esquina):
    admin, _ = esquina["admin.esquina"]
    publico = Api(client)
    config, token = web(admin)
    # El QR de domicilios no aparece entre los QR de las mesas
    assert not [q for q in admin.data("/qr/list") if token in q["url"]]

    pausado = admin.data("/domicilio/web/save", {"activo": False, "aprobacion": True, "mensaje": config["mensaje"]})
    assert pausado["activo"] is False
    carta = publico.data("/publico/qr", {"token": token})
    assert carta["disponible"] is False and "domicilios" in carta["mensaje"] and carta["categorias"] == []
    centro = find(admin.data("/domicilio/zona/list"), nombre="Centro")
    assert publico.post("/publico/orden/create", pedido(admin, token, centro["id"], telefono="3145556677")).status_code == 409

    admin.data("/domicilio/web/save", {"activo": True, "aprobacion": False, "mensaje": config["mensaje"]})
    # Sin aprobación, el pedido va directo a cocina
    directo = publico.data("/publico/orden/create", pedido(admin, token, centro["id"], telefono="3145556677"), expect=201)
    assert directo["estado"] == "nueva"

    nuevo = admin.data("/domicilio/web/regenerar")
    assert nuevo["url"] != config["url"]
    assert publico.post("/publico/qr", {"token": token}).status_code == 404
    assert publico.data("/publico/qr", {"token": nuevo["url"].rsplit("/", 1)[1]})["disponible"]
    admin.data("/domicilio/web/save", {"activo": True, "aprobacion": True, "mensaje": config["mensaje"]})
