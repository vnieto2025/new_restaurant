"""
Caja (doc 20): turnos con arqueo, cuenta por mesa, pagos mixtos, propina, descuento,
anulaciones, movimientos y cierre de jornada.
"""
from conftest import Api, login, key, find, product_id, table, option_id, ensure_shift, medio, pay_table


def ordenar(api, mesa_id, productos, admin):
    items = []
    for nombre, cantidad in productos:
        item = {"producto_id": product_id(admin, nombre), "cantidad": cantidad}
        if nombre.startswith("Hamburguesa"):
            item["modificadores"] = [option_id(admin, "Término de la carne", "Medio")]
        items.append(item)
    return api.data("/orden/create", {"mesa_id": mesa_id, "clave_idempotencia": key(), "items": items}, expect=201)


def test_cuenta_de_mesa_con_pago_mixto_y_cambio(esquina):
    mesero, _ = esquina["mesero.salon"]
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    ensure_shift(caja)
    mesa = table(mesero, "Mesa 7")

    # Dos órdenes en la misma mesa y un ítem cancelado: la cuenta suma solo lo vigente
    primera = ordenar(mesero, mesa["id"], [("Hamburguesa clásica", 1), ("Limonada natural", 2)], admin)
    ordenar(mesero, mesa["id"], [("Papas a la francesa", 1)], admin)
    limonadas = find(primera["items"], nombre="Limonada natural")
    mesero.data("/orden/cancelar_item", {"orden_item_id": limonadas["id"], "motivo": "Se equivocó"})

    # El mesero pide la cuenta: la mesa cambia de estado y caja la ve primero
    pedida = mesero.data("/cuenta/solicitar", {"mesa_id": mesa["id"]})
    assert pedida["subtotal"] == 18000 + 7000
    assert len(pedida["ordenes"]) == 2 and pedida["ordenes"][0] == primera["numero_texto"]
    assert table(mesero, "Mesa 7")["estado"] == "cuenta_solicitada"
    assert caja.data("/cuenta/pendientes")[0]["mesa"] == "Mesa 7"

    # Propina sugerida del 10 %
    cuenta = caja.data("/cuenta/abrir", {"mesa_id": mesa["id"]})
    assert cuenta["propina_sugerida"] == 2500
    cuenta = caja.data("/cuenta/ajustar", {"cuenta_id": cuenta["id"], "propina": 2500})
    assert cuenta["total"] == 27500

    # Pagar de más se rechaza (RN-CAJ-04)
    response = caja.post("/cuenta/pagar", {"cuenta_id": cuenta["id"], "clave_idempotencia": key(), "pagos": [
        {"medio_pago_id": medio(caja, "Efectivo"), "monto": 30000}]})
    assert response.status_code == 400

    # La transferencia exige referencia
    response = caja.post("/cuenta/pagar", {"cuenta_id": cuenta["id"], "clave_idempotencia": key(), "pagos": [
        {"medio_pago_id": medio(caja, "Nequi"), "monto": 10000}]})
    assert response.status_code == 400 and "referencia" in response.json()["message"]

    # Pago mixto: tarjeta + efectivo con cambio
    clave = key()
    body = {"cuenta_id": cuenta["id"], "clave_idempotencia": clave, "pagos": [
        {"medio_pago_id": medio(caja, "Tarjeta (datáfono)"), "monto": 17500},
        {"medio_pago_id": medio(caja, "Efectivo"), "monto": 10000, "recibido": 20000},
    ]}
    response = caja.post("/cuenta/pagar", body, expect=200)
    pagada = response.json()["data"]
    assert pagada["estado"] == "pagada" and pagada["saldo"] == 0
    assert pagada["numero_texto"].startswith("C-")
    assert "Cambio: 10.000" in response.json()["message"]
    assert find(pagada["pagos"], medio="Efectivo")["cambio"] == 10000

    # El reintento con la misma clave no duplica el pago
    repetido = caja.data("/cuenta/pagar", body)
    assert len(repetido["pagos"]) == 2

    # La mesa queda libre y ya no aparece por cobrar
    assert table(mesero, "Mesa 7")["estado"] == "libre"
    assert all(p["mesa"] != "Mesa 7" for p in caja.data("/cuenta/pendientes"))


def test_descuento_solo_con_permiso_y_motivo(esquina):
    mesero, _ = esquina["mesero.terraza"]
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    mesa = table(mesero, "Terraza 4")
    ordenar(mesero, mesa["id"], [("Salchipapa", 2)], admin)
    cuenta = caja.data("/cuenta/abrir", {"mesa_id": mesa["id"]})

    assert caja.post("/cuenta/ajustar", {"cuenta_id": cuenta["id"], "descuento": 3000}).status_code == 403
    assert admin.post("/cuenta/ajustar", {"cuenta_id": cuenta["id"], "descuento": 3000}).status_code == 400
    con_descuento = admin.data("/cuenta/ajustar", {"cuenta_id": cuenta["id"], "descuento": 3000,
                                                   "descuento_motivo": "Cliente frecuente"})
    assert con_descuento["total"] == 30000 - 3000
    assert any(r["entidad_id"] == cuenta["id"] for r in admin.data("/auditoria/list", {"accion": "descuento_aplicado"}))

    # El mesero no cobra (doc 29)
    assert mesero.post("/cuenta/pagar", {"cuenta_id": cuenta["id"], "clave_idempotencia": key(), "pagos": []}).status_code == 403
    pay_table(caja, mesa_id=mesa["id"])


def test_pago_parcial_anulacion_y_cierre_de_turno(esquina):
    mesero, _ = esquina["mesero.salon"]
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    estado = ensure_shift(caja)
    mesa = table(mesero, "Mesa 8")
    ordenar(mesero, mesa["id"], [("Perro sencillo", 2)], admin)
    cuenta = caja.data("/cuenta/abrir", {"mesa_id": mesa["id"]})

    abono = caja.data("/cuenta/pagar", {"cuenta_id": cuenta["id"], "clave_idempotencia": key(), "pagos": [
        {"medio_pago_id": medio(caja, "Efectivo"), "monto": 10000}]})
    assert abono["estado"] == "abierta" and abono["saldo"] == 14000

    # Anular un pago es de administrador
    pago_id = abono["pagos"][0]["id"]
    assert caja.post("/cuenta/anular_pago", {"pago_id": pago_id, "motivo": "Error de digitación"}).status_code == 403
    sin_abono = admin.data("/cuenta/anular_pago", {"pago_id": pago_id, "motivo": "Error de digitación"})
    assert sin_abono["pagado"] == 0 and sin_abono["pagos"][0]["estado"] == "anulado"

    # Vuelve a abonar: el turno no cierra con un pago parcial sin confirmar (RN-CAJ-03)
    caja.data("/cuenta/pagar", {"cuenta_id": cuenta["id"], "clave_idempotencia": key(), "pagos": [
        {"medio_pago_id": medio(caja, "Efectivo"), "monto": 4000}]})
    response = caja.post("/caja/turno/cerrar", {"efectivo_contado": 0})
    assert response.status_code == 409 and response.json()["data"]["cuentas_pendientes"] == 1

    # Movimientos: un gasto mayor que el efectivo se rechaza; un aporte y un gasto válidos
    esperado = caja.data("/caja/estado")["turno"]["resumen"]["efectivo_esperado"]
    assert caja.post("/caja/movimiento/create", {"tipo": "gasto", "monto": esperado + 1, "concepto": "Hielo"}).status_code == 400
    caja.data("/caja/movimiento/create", {"tipo": "aporte", "monto": 50000, "concepto": "Más monedas"}, expect=201)
    caja.data("/caja/movimiento/create", {"tipo": "gasto", "monto": 8000, "concepto": "Bolsa de hielo"}, expect=201)
    turno = caja.data("/caja/estado")["turno"]
    assert turno["resumen"]["efectivo_esperado"] == esperado + 50000 - 8000

    # Cierre con arqueo: la diferencia queda registrada (RN-CAJ-06)
    contado = turno["resumen"]["efectivo_esperado"] - 2000
    cerrado = caja.data("/caja/turno/cerrar", {"efectivo_contado": contado, "confirmar_pendientes": True,
                                               "observacion": "Faltaron monedas"})
    assert cerrado["estado"] == "cerrado" and cerrado["diferencia"] == -2000
    assert cerrado["id"] == estado["turno"]["id"]

    # Sin turno no se cobra (RN-CAJ-01)
    response = caja.post("/cuenta/pagar", {"cuenta_id": cuenta["id"], "clave_idempotencia": key(), "pagos": [
        {"medio_pago_id": medio(caja, "Efectivo"), "monto": 20000}]})
    assert response.status_code == 409 and "turno" in response.json()["message"]
    pay_table(caja, mesa_id=mesa["id"])


def test_pedido_para_llevar_se_cierra_al_cobrar(esquina):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    cocina, sesion_cocina = esquina["cocina.esquina"]
    externa = table(caja, "Para llevar", incluir_externa=True)
    orden = caja.data("/orden/create", {"mesa_id": externa["id"], "clave_idempotencia": key(), "cliente_nombre": "Rosa",
                                        "items": [{"producto_id": product_id(admin, "Perro sencillo"), "cantidad": 1}]},
                      expect=201)

    # Se entrega antes de cobrar: con caja, la sesión sigue abierta hasta que se pague
    punto = find(sesion_cocina["puntos"], nombre="Cocina")
    tarjeta = find(cocina.data("/cocina/comandas", {"punto_produccion_id": punto["id"]})["en_proceso"], orden_id=orden["id"])
    cocina.data("/cocina/abrir", {"comanda_id": tarjeta["id"]})
    cocina.data("/cocina/despachar", {"comanda_id": tarjeta["id"]})
    caja.data("/orden/entregar", {"orden_id": orden["id"]})
    pendiente = find(caja.data("/cuenta/pendientes"), sesion_mesa_id=orden["sesion_mesa_id"])
    assert pendiente["cliente_nombre"] == "Rosa" and pendiente["total"] == 12000

    pagada = pay_table(caja, sesion_mesa_id=orden["sesion_mesa_id"])
    assert pagada["estado"] == "pagada" and pagada["cliente_nombre"] == "Rosa"


def test_anular_cuenta_pagada(esquina):
    mesero, _ = esquina["mesero.salon"]
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    mesa = table(mesero, "Mesa 4")
    ordenar(mesero, mesa["id"], [("Agua sin gas", 1)], admin)
    pagada = pay_table(caja, mesa_id=mesa["id"])

    assert caja.post("/cuenta/anular", {"cuenta_id": pagada["id"], "motivo": "Prueba"}).status_code == 403
    anulada = admin.data("/cuenta/anular", {"cuenta_id": pagada["id"], "motivo": "Cobro duplicado"})
    assert anulada["estado"] == "anulada"
    assert all(p["estado"] == "anulado" for p in anulada["pagos"])
    assert any(c["id"] == pagada["id"] for c in caja.data("/cuenta/list", {"estado": "anulada"}))


def test_mesa_sin_consumo_se_libera_sin_cobrar(esquina):
    mesero, _ = esquina["mesero.salon"]
    mesa = table(mesero, "Mesa 3")
    if mesa["estado"] != "libre":
        return  # otra prueba dejó la mesa con consumo
    mesero.data("/mesa/abrir", {"mesa_id": mesa["id"]}, expect=201)
    mesero.data("/mesa/cerrar", {"mesa_id": mesa["id"]})
    assert table(mesero, "Mesa 3")["estado"] == "libre"


def test_modulo_caja_no_contratado(napoli):
    mesero, _ = napoli["mesero.napoli"]
    admin, _ = napoli["napoli"]
    assert admin.post("/caja/estado").json()["detail"]["codigo"] == "modulo_no_contratado"
    assert mesero.post("/cuenta/solicitar", {"mesa_id": 1}).status_code == 403


def test_cierre_de_jornada(client):
    """ En un restaurante propio: cerrar la jornada bloquea órdenes y cobros, y reinicia agotados """
    soporte, _ = login(client, "soporte", "Soporte12345")
    soporte.data("/plataforma/empresa/create", {
        "nombre_comercial": "Cafetería Cierre", "modulos": ["pedidos", "caja"], "estado_contrato": "activo",
        "admin": {"usuario": "duena.cierre", "nombre": "Dueña", "password": "clave12345"},
        "restaurante": {"nombre": "Cierre Centro", "hora_inicio_jornada": "05:00"},
    }, expect=201)
    duena, _ = login(client, "duena.cierre", "clave12345")
    duena.data("/usuario/create", {"usuario": "admin.cierre", "nombre": "Admin", "password": "clave12345",
                                   "roles": ["admin_restaurante"]}, expect=201)
    admin, _ = login(client, "admin.cierre", "clave12345")
    categoria = admin.data("/categoria/create", {"nombre": "Café"}, expect=201)
    tinto = admin.data("/producto/create", {"categoria_id": categoria["id"], "nombre": "Tinto", "precio": 2000}, expect=201)
    pan = admin.data("/producto/create", {"categoria_id": categoria["id"], "nombre": "Pan", "precio": 1000}, expect=201)
    admin.data("/producto/agotado", {"producto_id": pan["id"], "agotado": True})

    externa = table(admin, "Para llevar", incluir_externa=True)
    admin.data("/orden/create", {"mesa_id": externa["id"], "clave_idempotencia": key(), "cliente_nombre": "Leo",
                                 "items": [{"producto_id": tinto["id"], "cantidad": 3}]}, expect=201)

    # Bloqueos: hay un pedido sin cobrar y luego un turno abierto
    estado = admin.data("/caja/jornada/estado")
    assert estado["bloqueos"]["pedidos_externos_abiertos"] == 1
    assert admin.post("/caja/jornada/cerrar").status_code == 409
    pendiente = admin.data("/cuenta/pendientes")[0]
    pay_table(admin, sesion_mesa_id=pendiente["sesion_mesa_id"])
    response = admin.post("/caja/jornada/cerrar")
    assert response.status_code == 409 and "turno" in response.json()["message"]

    turno = admin.data("/caja/estado")["turno"]
    assert turno["resumen"]["ventas"] == 6000
    admin.data("/caja/turno/cerrar", {"efectivo_contado": turno["resumen"]["efectivo_esperado"]})
    cierre = admin.data("/caja/jornada/cerrar")
    assert cierre["resumen"]["ventas"] == 6000 and cierre["resumen"]["cuentas"] == 1

    # Jornada cerrada: no hay órdenes, ni turnos, y los agotados se reiniciaron
    response = admin.post("/orden/create", {"mesa_id": externa["id"], "clave_idempotencia": key(), "cliente_nombre": "Ana",
                                            "items": [{"producto_id": tinto["id"], "cantidad": 1}]})
    assert response.status_code == 409 and "jornada" in response.json()["message"]
    assert admin.post("/caja/turno/abrir", {"fondo_inicial": 0}).status_code == 409
    assert find(admin.data("/producto/list"), nombre="Pan")["agotado"] is False
    assert admin.data("/caja/jornada/estado")["cerrada"] is True
    assert Api(client).post("/caja/jornada/cerrar").status_code == 401
