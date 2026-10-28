"""
Corte vertical de la fase 0: QR / tablet -> orden -> cocina -> en proceso -> listo -> entregado.
Incluye los casos que el doc 17, sección 7, pide probar antes de producción.
"""
from conftest import Api, key, find, product_id, table, qr_token, option_id, pay_table


def comandas(api, punto_nombre):
    sesion = api.data("/auth/sesion")
    punto = find(sesion["puntos"], nombre=punto_nombre)
    return api.data("/cocina/comandas", {"punto_produccion_id": punto["id"]})


def tarjeta_de(kds, orden_id, pestana="en_proceso"):
    return [t for t in kds[pestana] if t["orden_id"] == orden_id]


def test_flujo_completo_tablet_a_entregado(esquina):
    mesero, _ = esquina["mesero.salon"]
    cocina, _ = esquina["cocina.esquina"]
    mesa = table(mesero, "Mesa 1")
    hamburguesa = product_id(esquina["admin.esquina"][0], "Hamburguesa clásica")

    orden = mesero.data("/orden/create", {
        "mesa_id": mesa["id"], "clave_idempotencia": key(),
        "items": [{"producto_id": hamburguesa, "cantidad": 2, "nota": "sin cebolla",
                   "modificadores": [option_id(esquina["admin.esquina"][0], "Término de la carne", "Medio")]}],
    }, expect=201)
    assert orden["estado"] == "nueva"
    assert orden["total"] == 36000
    assert orden["items"][0]["punto_produccion"] == "Cocina"
    assert orden["mesero"] == "Carlos Mesero"

    assert table(mesero, "Mesa 1")["estado"] == "con_orden"

    # Cocina ve la tarjeta azul (nueva), la abre (amarillo) y la despacha (Listos)
    kds = comandas(cocina, "Cocina")
    [tarjeta] = tarjeta_de(kds, orden["id"])
    assert tarjeta["estado"] == "nueva"
    assert tarjeta["items"][0]["nota"] == "sin cebolla"

    abierta = cocina.data("/cocina/abrir", {"comanda_id": tarjeta["id"]})
    assert abierta["estado"] == "en_proceso"
    cocina.data("/cocina/despachar", {"comanda_id": tarjeta["id"]})
    assert tarjeta_de(comandas(cocina, "Cocina"), orden["id"], "listos")

    # El mesero ve "lista" y entrega; la tarjeta sale de Listos
    assert mesero.data("/orden/get", {"orden_id": orden["id"]})["estado"] == "lista"
    entregada = mesero.data("/orden/entregar", {"orden_id": orden["id"]})
    assert entregada["estado"] == "entregada"
    assert not tarjeta_de(comandas(cocina, "Cocina"), orden["id"], "listos")

    # Con caja contratada la mesa no se libera sin cobrar; al pagar queda libre
    response = mesero.post("/mesa/cerrar", {"mesa_id": mesa["id"]})
    assert response.status_code == 409 and "caja" in response.json()["message"]
    pagada = pay_table(esquina["caja.esquina"][0], mesa_id=mesa["id"])
    assert pagada["estado"] == "pagada"
    assert table(mesero, "Mesa 1")["estado"] == "libre"


def test_envio_duplicado_devuelve_la_misma_orden(esquina):
    mesero, _ = esquina["mesero.salon"]
    mesa = table(mesero, "Mesa 2")
    papas = product_id(esquina["admin.esquina"][0], "Papas a la francesa")
    body = {"mesa_id": mesa["id"], "clave_idempotencia": key(),
            "items": [{"producto_id": papas, "cantidad": 1}]}

    primera = mesero.post("/orden/create", body, expect=201).json()["data"]
    segunda = mesero.post("/orden/create", body, expect=200).json()["data"]
    assert primera["id"] == segunda["id"]
    assert primera["numero"] == segunda["numero"]

    ordenes = mesero.data("/orden/list", {"mesa_id": mesa["id"]})
    assert [o["id"] for o in ordenes] == [primera["id"]]


def test_orden_con_varios_puntos_se_divide_en_comandas(esquina):
    mesero, _ = esquina["mesero.salon"]
    cocina, _ = esquina["cocina.esquina"]
    bar, _ = esquina["bar.esquina"]
    admin, _ = esquina["admin.esquina"]
    mesa = table(mesero, "Mesa 3")

    orden = mesero.data("/orden/create", {
        "mesa_id": mesa["id"], "clave_idempotencia": key(),
        "items": [
            {"producto_id": product_id(admin, "Hamburguesa doble"), "cantidad": 1,
             "modificadores": [option_id(admin, "Término de la carne", "Bien asada")]},
            {"producto_id": product_id(admin, "Cerveza nacional"), "cantidad": 2},
        ],
    }, expect=201)
    assert sorted(c["punto_produccion"] for c in orden["comandas"]) == ["Bar", "Cocina"]

    # Cada punto solo ve lo suyo y trabaja por separado (doc 19)
    [en_cocina] = tarjeta_de(comandas(cocina, "Cocina"), orden["id"])
    [en_bar] = tarjeta_de(comandas(bar, "Bar"), orden["id"])
    assert [i["nombre"] for i in en_cocina["items"]] == ["Hamburguesa doble"]
    assert [i["nombre"] for i in en_bar["items"]] == ["Cerveza nacional"]

    bar.data("/cocina/abrir", {"comanda_id": en_bar["id"]})
    bar.data("/cocina/despachar", {"comanda_id": en_bar["id"]})
    # Cerveza lista + hamburguesa nueva = la orden sigue en proceso (doc 16, sección 4)
    assert mesero.data("/orden/get", {"orden_id": orden["id"]})["estado"] == "en_proceso"

    # El bar no puede tocar la comanda de cocina
    assert bar.post("/cocina/abrir", {"comanda_id": en_cocina["id"]}).status_code == 403


def test_edicion_despues_de_enviar(esquina):
    mesero, _ = esquina["mesero.salon"]
    cocina, _ = esquina["cocina.esquina"]
    admin, _ = esquina["admin.esquina"]
    mesa = table(mesero, "Mesa 4")

    orden = mesero.data("/orden/create", {
        "mesa_id": mesa["id"], "clave_idempotencia": key(),
        "items": [{"producto_id": product_id(admin, "Salchipapa"), "cantidad": 1},
                  {"producto_id": product_id(admin, "Perro sencillo"), "cantidad": 1}],
    }, expect=201)

    # Agregar ítems crea una comanda de adición; el reintento no duplica
    adicion = {"orden_id": orden["id"], "clave_idempotencia": key(),
               "items": [{"producto_id": product_id(admin, "Papas a la francesa"), "cantidad": 1}]}
    con_adicion = mesero.data("/orden/agregar_items", adicion)
    mesero.data("/orden/agregar_items", adicion)
    assert len(mesero.data("/orden/get", {"orden_id": orden["id"]})["items"]) == 3
    assert [c["es_adicion"] for c in con_adicion["comandas"]] == [False, True]
    assert con_adicion["total"] == 15000 + 12000 + 7000

    # Quitar un ítem en "nuevo": el mesero puede, y la cocina lo ve como modificación
    perro = find(con_adicion["items"], nombre="Perro sencillo")
    sin_perro = mesero.data("/orden/cancelar_item", {"orden_item_id": perro["id"], "motivo": "El cliente cambió de idea"})
    assert sin_perro["total"] == 15000 + 7000
    [original, _] = tarjeta_de(comandas(cocina, "Cocina"), orden["id"])
    assert original["modificada"] is True

    # En proceso ya no lo puede quitar el mesero; el administrador sí, y queda auditado
    cocina.data("/cocina/abrir", {"comanda_id": original["id"]})
    salchipapa = find(sin_perro["items"], nombre="Salchipapa")
    response = mesero.post("/orden/cancelar_item", {"orden_item_id": salchipapa["id"], "motivo": "Se fue"})
    assert response.status_code == 403
    perdida = admin.data("/orden/cancelar_item", {"orden_item_id": salchipapa["id"], "motivo": "Cliente se fue"})
    assert find(perdida["items"], nombre="Salchipapa")["tipo_cancelacion"] == "perdida"
    assert any(r["entidad_id"] == salchipapa["id"] for r in admin.data("/auditoria/list", {"accion": "item_cancelado"}))


def test_qr_con_aprobacion_espera_al_mesero(client, esquina):
    mesero, _ = esquina["mesero.salon"]
    cocina, _ = esquina["cocina.esquina"]
    admin, _ = esquina["admin.esquina"]
    publico = Api(client)
    token = qr_token(admin, "Mesa 5")

    carta = publico.data("/publico/qr", {"token": token})
    assert carta["mesa"] == "Mesa 5" and carta["zona"] == "Salón"
    assert carta["con_aprobacion"] is True
    clasica = find(find(carta["categorias"], nombre="Hamburguesas")["productos"], nombre="Hamburguesa clásica")

    pedido = publico.data("/publico/orden/create", {
        "token": token, "clave_idempotencia": key(),
        "items": [{"producto_id": clasica["id"], "cantidad": 1,
                   "modificadores": [clasica["grupos"][0]["opciones"][0]["id"]]}],
    }, expect=201)
    assert pedido["estado"] == "pendiente_aprobacion"
    assert "id" not in pedido  # lo público no expone ids internos

    # No llega a cocina hasta que el mesero la aprueba
    pendiente = find(mesero.data("/orden/list"), numero_texto=pedido["numero_texto"])
    assert not tarjeta_de(comandas(cocina, "Cocina"), pendiente["id"])
    assert table(mesero, "Mesa 5")["estado_urgente"] == "pendiente_aprobacion"

    aprobada = mesero.data("/orden/aprobar", {"orden_id": pendiente["id"]})
    assert aprobada["estado"] == "nueva"
    assert aprobada["mesero"] == "Carlos Mesero"
    assert tarjeta_de(comandas(cocina, "Cocina"), pendiente["id"])

    estado = publico.data("/publico/orden/estado", {"seguimiento": pedido["seguimiento"]})
    assert estado["estado"] == "nueva"


def test_qr_rechazado(client, esquina):
    mesero, _ = esquina["mesero.salon"]
    admin, _ = esquina["admin.esquina"]
    publico = Api(client)
    token = qr_token(admin, "Mesa 6")
    gaseosa = product_id(admin, "Gaseosa 400 ml")

    pedido = publico.data("/publico/orden/create", {
        "token": token, "clave_idempotencia": key(), "items": [{"producto_id": gaseosa, "cantidad": 1}],
    }, expect=201)
    orden = find(mesero.data("/orden/list"), numero_texto=pedido["numero_texto"])
    mesero.data("/orden/rechazar", {"orden_id": orden["id"], "motivo": "Mesa vacía"})

    estado = publico.data("/publico/orden/estado", {"seguimiento": pedido["seguimiento"]})
    assert estado["estado"] == "cancelada"
    assert estado["items"][0]["motivo"] == "Mesa vacía"


def test_qr_libre_va_directo_a_produccion(client, esquina):
    cocina, _ = esquina["cocina.esquina"]
    admin, _ = esquina["admin.esquina"]
    mesero_terraza, _ = esquina["mesero.terraza"]
    publico = Api(client)
    token = qr_token(admin, "Terraza 1")

    pedido = publico.data("/publico/orden/create", {
        "token": token, "clave_idempotencia": key(),
        "items": [{"producto_id": product_id(admin, "Hamburguesa de pollo"), "cantidad": 1,
                   "modificadores": [option_id(admin, "Término de la carne", "Medio")]}],
    }, expect=201)
    assert pedido["estado"] == "nueva"
    orden = find(mesero_terraza.data("/orden/list"), numero_texto=pedido["numero_texto"])
    assert tarjeta_de(comandas(cocina, "Cocina"), orden["id"])


def test_para_llevar_por_qr_rapido_y_mostrador(client, esquina):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    publico = Api(client)
    token = qr_token(admin, "Para llevar")
    limonada = product_id(admin, "Limonada natural")

    # Para llevar exige nombre del cliente
    sin_nombre = publico.post("/publico/orden/create", {
        "token": token, "clave_idempotencia": key(), "items": [{"producto_id": limonada, "cantidad": 1}]})
    assert sin_nombre.status_code == 400

    pedido = publico.data("/publico/orden/create", {
        "token": token, "clave_idempotencia": key(), "cliente_nombre": "Ana",
        "items": [{"producto_id": limonada, "cantidad": 1}],
    }, expect=201)
    assert pedido["mesa_tipo"] == "externa" and pedido["cliente_nombre"] == "Ana"

    # Desde el mostrador: la mesa externa admite muchas órdenes a la vez
    externa = table(caja, "Para llevar", incluir_externa=True)
    for nombre in ["Luis", "Marta"]:
        caja.data("/orden/create", {"mesa_id": externa["id"], "clave_idempotencia": key(), "cliente_nombre": nombre,
                                    "items": [{"producto_id": limonada, "cantidad": 1}]}, expect=201)
    nombres = {o["cliente_nombre"] for o in caja.data("/orden/list") if o["mesa_tipo"] == "externa"}
    assert {"Ana", "Luis", "Marta"} <= nombres


def test_producto_agotado_y_fuera_de_carta(esquina):
    mesero, _ = esquina["mesero.salon"]
    cocina, _ = esquina["cocina.esquina"]
    admin, _ = esquina["admin.esquina"]
    mesa = table(mesero, "Mesa 7")
    jugo = product_id(admin, "Jugo de mango")
    perro = product_id(admin, "Perro sencillo")

    orden = mesero.data("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(),
                                          "items": [{"producto_id": perro, "cantidad": 1}]}, expect=201)
    [tarjeta] = tarjeta_de(comandas(cocina, "Cocina"), orden["id"])
    cocina.data("/cocina/agotado", {"orden_item_id": tarjeta["items"][0]["id"]})

    # El producto queda agotado: no se puede volver a pedir
    response = mesero.post("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(),
                                             "items": [{"producto_id": perro, "cantidad": 1}]})
    assert response.status_code == 409
    assert "Agotado" in response.json()["message"]
    admin.data("/producto/agotado", {"producto_id": perro, "agotado": False})

    # Un producto que no está en la carta de la zona se rechaza
    carta = find(admin.data("/carta/list"), nombre="Carta principal")
    otra = admin.data("/carta/create", {"nombre": "Solo bebidas", "productos": [jugo]}, expect=201)
    assert otra["productos"] == [jugo] and carta["id"] != otra["id"]
    zona = find(admin.data("/zona/list"), nombre="Terraza")
    admin.data("/zona/update", {**zona, "zona_id": zona["id"], "carta_id": otra["id"]})
    terraza = table(admin, "Terraza 2")
    response = admin.post("/orden/create", {"mesa_id": terraza["id"], "clave_idempotencia": key(),
                                            "items": [{"producto_id": perro, "cantidad": 1}]})
    assert response.status_code == 409
    assert "Perro sencillo" in response.json()["message"]
    admin.data("/zona/update", {**zona, "zona_id": zona["id"], "carta_id": carta["id"]})


def test_despacho_directo_sin_punto_de_produccion(esquina):
    admin, _ = esquina["admin.esquina"]
    categoria = admin.data("/categoria/create", {"nombre": "Nevera"}, expect=201)
    agua = admin.data("/producto/create", {"categoria_id": categoria["id"], "nombre": "Agua con gas", "precio": 4000},
                      expect=201)

    # Ni producto, ni categoría, ni zona tienen punto: se despacha de inmediato (doc 19, sección 3)
    zona = find(admin.data("/zona/list"), nombre="Terraza")
    admin.data("/zona/update", {**zona, "zona_id": zona["id"], "punto_produccion_id": None})
    mesa = table(admin, "Terraza 3")
    orden = admin.data("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(),
                                         "items": [{"producto_id": agua["id"], "cantidad": 1}]}, expect=201)
    assert orden["comandas"] == []
    assert orden["items"][0]["estado"] == "despachado"
    assert orden["estado"] == "lista"
    admin.data("/zona/update", {**zona, "zona_id": zona["id"]})


def test_restaurante_en_pausa_bloquea_qr_pero_no_tablet(client, esquina):
    admin, _ = esquina["admin.esquina"]
    mesero, _ = esquina["mesero.terraza"]
    token = qr_token(admin, "Terraza 4")
    limonada = product_id(admin, "Limonada natural")

    admin.data("/restaurante/change_status", {"estado": "pausado", "mensaje_carta": "Cocina saturada, volvemos en 15 min"})
    try:
        carta = Api(client).data("/publico/qr", {"token": token})
        assert carta["disponible"] is False and "saturada" in carta["mensaje"]
        response = Api(client).post("/publico/orden/create", {
            "token": token, "clave_idempotencia": key(), "items": [{"producto_id": limonada, "cantidad": 1}]})
        assert response.status_code == 409

        mesa = table(mesero, "Terraza 4")
        mesero.data("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(),
                                      "items": [{"producto_id": limonada, "cantidad": 1}]}, expect=201)
    finally:
        admin.data("/restaurante/change_status", {"estado": "activo"})


def test_qr_revocado_deja_de_funcionar(client, esquina):
    admin, _ = esquina["admin.esquina"]
    mesa = table(admin, "Mesa 8")
    viejo = qr_token(admin, "Mesa 8")

    nuevo = admin.data("/qr/regenerar", {"mesa_id": mesa["id"]})
    assert Api(client).post("/publico/qr", {"token": viejo}).status_code == 404
    assert Api(client).data("/publico/qr", {"token": nuevo["url"].rsplit("/", 1)[1]})["mesa"] == "Mesa 8"
    assert nuevo["svg"].startswith("<svg")


def test_limite_de_ordenes_por_qr(client, esquina):
    admin, _ = esquina["admin.esquina"]
    token = qr_token(admin, "Mesa 8")
    gaseosa = product_id(admin, "Gaseosa 400 ml")
    publico = Api(client)

    codigos = [publico.post("/publico/orden/create", {
        "token": token, "clave_idempotencia": key(), "items": [{"producto_id": gaseosa, "cantidad": 1}],
    }).status_code for _ in range(7)]
    assert codigos[:6] == [201] * 6
    assert codigos[6] == 429


def test_cerrar_mesa_con_items_pendientes_se_rechaza(esquina):
    mesero, _ = esquina["mesero.salon"]
    admin, _ = esquina["admin.esquina"]
    mesa = table(mesero, "Mesa 3")
    response = mesero.post("/mesa/cerrar", {"mesa_id": mesa["id"]})
    assert response.status_code == 409
    assert "sin entregar" in response.json()["message"]


def test_reabrir_comanda_queda_auditado(esquina):
    mesero, _ = esquina["mesero.terraza"]
    cocina, _ = esquina["cocina.esquina"]
    admin, _ = esquina["admin.esquina"]
    mesa = table(mesero, "Terraza 2")
    orden = mesero.data("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(),
                                          "items": [{"producto_id": product_id(admin, "Salchipapa"), "cantidad": 1}]},
                        expect=201)
    [tarjeta] = tarjeta_de(comandas(cocina, "Cocina"), orden["id"])
    cocina.data("/cocina/abrir", {"comanda_id": tarjeta["id"]})
    cocina.data("/cocina/despachar", {"comanda_id": tarjeta["id"]})
    reabierta = cocina.data("/cocina/reabrir", {"comanda_id": tarjeta["id"], "motivo": "Faltó la salsa"})
    assert reabierta["estado"] == "en_proceso"

    # Transición que no existe: de en proceso no se entrega sin despachar (RG-22)
    response = mesero.post("/orden/entregar", {"orden_item_ids": [tarjeta["items"][0]["id"]]})
    assert response.status_code == 409

    tirilla = cocina.data("/cocina/tirilla", {"comanda_id": tarjeta["id"]})
    assert tirilla["restaurante"] == "La Esquina Centro" and "precio_unitario" not in tirilla["items"][0]
    cocina.data("/cocina/tirilla", {"comanda_id": tarjeta["id"]})
    acciones = [r["accion"] for r in admin.data("/auditoria/list")]
    assert "comanda_reabierta" in acciones and "tirilla_reimpresa" in acciones
