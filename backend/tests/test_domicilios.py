"""
Domicilios (doc 15B): zonas de envío con tarifa, asignación por código, salida cuando cocina despacha,
entrega del domiciliario, cobro contra entrega con rendición en caja, entregas fallidas y validaciones.
"""
from conftest import key, find, product_id, table, ensure_shift, login


def zona(api, nombre):
    return find(api.data("/domicilio/zona/list"), nombre=nombre)


def domiciliario(api, codigo):
    return find(api.data("/domicilio/domiciliario/list"), codigo=codigo)


def pedir(caja, admin, zona_id, cantidad=1, telefono="3109998877", **extra):
    externa = table(caja, "Para llevar", incluir_externa=True)
    body = {"mesa_id": externa["id"], "clave_idempotencia": key(), "cliente_nombre": "Domicilio prueba",
            "cliente_telefono": telefono,
            "items": [{"producto_id": product_id(admin, "Papas a la francesa"), "cantidad": cantidad}],
            "entrega": {"zona_envio_id": zona_id, "direccion": "Calle 12 # 4-56 apto 201", "barrio": "Centro",
                        "indicaciones": "Portería azul"}}
    body.update(extra)
    return caja.post("/orden/create", body)


def despachar(cocina, sesion, orden):
    punto = find(sesion["puntos"], nombre="Cocina")["id"]
    tarjeta = find(cocina.data("/cocina/comandas", {"punto_produccion_id": punto})["en_proceso"], orden_id=orden["id"])
    cocina.data("/cocina/abrir", {"comanda_id": tarjeta["id"]})
    cocina.data("/cocina/despachar", {"comanda_id": tarjeta["id"]})


def entrega_de(api, orden):
    datos = api.data("/entrega/list")
    return next(e for e in datos["activas"] + datos["cerradas"] if e["orden_id"] == orden["id"])


def test_domicilio_contra_entrega_y_rendicion(esquina, client):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    cocina, sesion = esquina["cocina.esquina"]
    domi, _ = login(client, "domi.esquina")
    ensure_shift(caja)
    centro = zona(caja, "Centro")

    orden = pedir(caja, admin, centro["id"]).json()["data"]
    assert orden["canal"] == "domicilio"
    pendiente = next(c for c in caja.data("/cuenta/pendientes") if f"#{orden['numero']:03d}" in c["ordenes"])
    assert pendiente["domicilio"] and pendiente["envio"] == 3000 and pendiente["total"] == orden["total"] + 3000

    entrega = entrega_de(caja, orden)
    assert entrega["estado"] == "pendiente_asignacion" and not entrega["lista"] and entrega["tarifa"] == 3000
    assert caja.post("/entrega/salir", {"entrega_id": entrega["id"]}).status_code == 409  # sin domiciliario
    d01 = domiciliario(caja, "D01")
    caja.data("/entrega/asignar", {"entrega_id": entrega["id"], "domiciliario_id": d01["id"]})
    assert domi.post("/entrega/salir", {"entrega_id": entrega["id"]}).status_code == 409  # cocina no ha despachado

    despachar(cocina, sesion, orden)
    # El domiciliario ve solo lo suyo y sale con lo que debe cobrar
    propias = domi.data("/entrega/list")
    assert propias["propio"]["codigo"] == "D01" and propias["domiciliarios"] == []
    assert all(e["domiciliario"]["codigo"] == "D01" for e in propias["activas"])
    salida = domi.data("/entrega/salir", {"entrega_id": entrega["id"]})
    assert salida["estado"] == "en_camino" and salida["por_cobrar"] == orden["total"] + 3000

    # No se desactiva con una entrega en camino (RN-DOM-02)
    assert admin.post("/domicilio/domiciliario/change_status", {"domiciliario_id": d01["id"], "activo": False}).status_code == 409

    entregada = domi.data("/entrega/entregar", {"entrega_id": entrega["id"]})
    assert entregada["estado"] == "entregada" and entregada["hora_entrega"]
    assert caja.data("/orden/get", {"orden_id": orden["id"]})["estado"] == "entregada"

    # Rinde con 1000 de menos: la cuenta queda cobrada y el faltante no descuadra el arqueo (RN-DOM-03)
    antes = caja.data("/caja/estado")["turno"]["resumen"]
    grupo = find(caja.data("/entrega/por_rendir")["pendientes"], codigo="D01")
    esperado = grupo["esperado"]
    assert find(grupo["entregas"], id=entrega["id"])["monto"] == orden["total"] + 3000
    rendicion = caja.data("/entrega/rendir", {"domiciliario_id": d01["id"], "entregado": esperado - 1000,
                                              "notas": "Le faltó cambio"})
    assert rendicion["diferencia"] == -1000
    despues = caja.data("/caja/estado")["turno"]["resumen"]
    assert despues["efectivo_esperado"] == antes["efectivo_esperado"] + esperado - 1000
    assert despues["faltantes_domiciliarios"] == antes["faltantes_domiciliarios"] + 1000
    assert not any(g["codigo"] == "D01" for g in caja.data("/entrega/por_rendir")["pendientes"])

    cuenta = next(c for c in caja.data("/cuenta/list", {"estado": "pagada"}) if f"#{orden['numero']:03d}" in c["ordenes"])
    detalle = caja.data("/cuenta/get", {"cuenta_id": cuenta["id"]})
    assert detalle["envio"] == 3000 and detalle["total"] == orden["total"] + 3000
    assert detalle["entrega"]["direccion"].startswith("Calle 12")
    documento = admin.data("/documento/get", {"documento_id": detalle["documentos"][0]["id"]})
    linea = find(documento["lineas"], descripcion="Domicilio")
    assert linea["total"] == 3000 and documento["total"] == detalle["total"] - detalle["propina"]

    # La tirilla del domiciliario lleva la dirección
    tirilla = caja.data("/orden/tirilla", {"orden_id": orden["id"]})
    assert tirilla["entrega"]["indicaciones"] == "Portería azul"


def test_domicilio_fallido_reintento_y_cancelacion(esquina, client):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    cocina, sesion = esquina["cocina.esquina"]
    domi, _ = login(client, "domi.esquina")
    ensure_shift(caja)
    d01 = domiciliario(caja, "D01")
    d02 = domiciliario(caja, "D02")
    orden = pedir(caja, admin, zona(caja, "Sur")["id"]).json()["data"]
    entrega = entrega_de(caja, orden)
    despachar(cocina, sesion, orden)

    # Una entrega de otro domiciliario no se toca
    caja.data("/entrega/asignar", {"entrega_id": entrega["id"], "domiciliario_id": d02["id"]})
    assert domi.post("/entrega/salir", {"entrega_id": entrega["id"]}).status_code == 403
    caja.data("/entrega/salir", {"entrega_id": entrega["id"]})
    assert caja.post("/entrega/fallida", {"entrega_id": entrega["id"], "decision": "reintento"}).status_code == 422
    reintento = caja.data("/entrega/fallida", {"entrega_id": entrega["id"], "motivo": "Cliente ausente", "decision": "reintento"})
    assert reintento["estado"] == "pendiente_asignacion" and reintento["domiciliario"] is None and reintento["intentos"] == 1

    # El domiciliario solo puede pedir reintento; cancelar lo decide quien despacha (RN-DOM-04)
    caja.data("/entrega/asignar", {"entrega_id": entrega["id"], "domiciliario_id": d01["id"]})
    domi.data("/entrega/salir", {"entrega_id": entrega["id"]})
    assert domi.post("/entrega/fallida", {"entrega_id": entrega["id"], "motivo": "Dirección errada",
                                          "decision": "cancelacion"}).status_code == 403
    cancelada = caja.data("/entrega/fallida", {"entrega_id": entrega["id"], "motivo": "Dirección errada", "decision": "cancelacion"})
    assert cancelada["estado"] == "fallida" and cancelada["decision"] == "cancelacion"
    assert all(i["estado"] == "cancelado" for i in caja.data("/orden/get", {"orden_id": orden["id"]})["items"])
    # Ni el pedido ni el domicilio quedan por cobrar
    assert not any(f"#{orden['numero']:03d}" in c["ordenes"] for c in caja.data("/cuenta/pendientes"))


def test_validaciones_de_domicilio(esquina, napoli):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    mesero, _ = esquina["mesero.salon"]
    centro, norte = zona(caja, "Centro"), zona(caja, "Norte")

    assert pedir(caja, admin, norte["id"]).status_code == 400  # pedido mínimo de 20.000
    assert pedir(caja, admin, centro["id"], telefono=None).status_code == 400  # sin teléfono (RN-DOM-01)
    sin_direccion = pedir(caja, admin, centro["id"], entrega={"zona_envio_id": centro["id"]})
    assert sin_direccion.status_code == 422
    mesa = table(caja, "Mesa 1")
    assert caja.post("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(), "items": [
        {"producto_id": product_id(admin, "Papas a la francesa"), "cantidad": 1}],
        "entrega": {"zona_envio_id": centro["id"], "direccion": "Calle 1 # 2-3"}}).status_code == 400

    # Configuración: códigos únicos, zonas inactivas no reciben pedidos
    assert admin.post("/domicilio/domiciliario/save", {"nombre": "Otro", "codigo": "d01"}).status_code == 400
    nueva = admin.data("/domicilio/zona/save", {"nombre": "Rural", "tarifa": 9000, "pago_domiciliario": 7000}, expect=201)
    admin.data("/domicilio/zona/save", {"zona_envio_id": nueva["id"], "nombre": "Rural", "tarifa": 9000, "activo": False})
    assert pedir(caja, admin, nueva["id"]).status_code == 400

    assert mesero.post("/entrega/list").status_code == 403
    otro, _ = napoli["napoli"]
    assert otro.post("/entrega/list").status_code == 403  # sin el módulo contratado
