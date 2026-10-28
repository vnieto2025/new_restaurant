"""
Impuestos y facturación (docs 21 y 21A): impuesto incluido en el precio, documento al pagar con
numeración atómica, cola de emisión con proveedor simulado, rechazos, notas crédito y factura a nombre del cliente.
"""
from datetime import timedelta, date
from conftest import key, find, product_id, option_id, table, ensure_shift, medio


def pedido(caja, admin, productos):
    externa = table(caja, "Para llevar", incluir_externa=True)
    items = []
    for nombre, cantidad in productos:
        item = {"producto_id": product_id(admin, nombre), "cantidad": cantidad}
        if nombre.startswith("Hamburguesa"):
            item["modificadores"] = [option_id(admin, "Término de la carne", "Medio")]
        items.append(item)
    return caja.data("/orden/create", {"mesa_id": externa["id"], "clave_idempotencia": key(), "cliente_nombre": "Cliente",
                                        "items": items}, expect=201)


def cobrar(caja, orden, propina=0, factura=None, expect=200):
    ensure_shift(caja)
    cuenta = caja.data("/cuenta/abrir", {"sesion_mesa_id": orden["sesion_mesa_id"]})
    if propina:
        cuenta = caja.data("/cuenta/ajustar", {"cuenta_id": cuenta["id"], "propina": propina})
    body = {"cuenta_id": cuenta["id"], "clave_idempotencia": key(),
            "pagos": [{"medio_pago_id": medio(caja, "Efectivo"), "monto": cuenta["saldo"]}]}
    if factura:
        body["factura"] = factura
    return caja.post("/cuenta/pagar", body, expect=expect).json()


def enviar(api, ids=None):
    return api.data("/documento/enviar", {"documento_ids": ids or [], "forzar": bool(ids)})


def modo_proveedor(admin, modo):
    admin.data("/facturacion/config/save", {"proveedor": "simulado", "ambiente": "pruebas", "documento_defecto": "pos",
                                            "credenciales": {"modo": modo}, "activo": True})


def test_documento_pos_desglosa_el_impuesto_incluido(esquina):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    orden = pedido(caja, admin, [("Hamburguesa doble", 1), ("Limonada natural", 1)])
    pagada = cobrar(caja, orden, propina=3000)["data"]

    documento = pagada["documentos"][0]
    assert documento["tipo"] == "pos" and documento["numero"].startswith("POSE")
    assert documento["estado"] == "pendiente"
    # Impuesto al consumo del 8 % incluido: la propina queda fuera de la base (RN-FAC-03)
    assert documento["total"] == 32000 and documento["propina"] == 3000
    assert documento["base"] == 24074 + 5556 and documento["impuestos"] == 1926 + 444

    enviar(caja)
    detalle = caja.data("/documento/get", {"documento_id": documento["id"]})
    assert detalle["estado"] == "aceptada" and len(detalle["cufe"]) == 96
    assert sum(l["base"] + l["impuesto_valor"] for l in detalle["lineas"]) == detalle["total"]
    assert detalle["impuestos_detalle"] == [{"impuesto": "Impuesto al consumo", "porcentaje": 8.0, "porcentaje_texto": "8 %",
                                             "base": 29630, "valor": 2370}]
    assert "Término de la carne" not in detalle["lineas"][0]["descripcion"] and "Medio" in detalle["lineas"][0]["descripcion"]


def test_descuento_baja_la_base_y_el_impuesto(esquina):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    orden = pedido(caja, admin, [("Hamburguesa clásica", 1), ("Papas a la francesa", 1)])
    cuenta = caja.data("/cuenta/abrir", {"sesion_mesa_id": orden["sesion_mesa_id"]})
    admin.data("/cuenta/ajustar", {"cuenta_id": cuenta["id"], "descuento": 5000, "descuento_motivo": "Cliente frecuente"})
    documento = cobrar(caja, orden)["data"]["documentos"][0]

    detalle = caja.data("/documento/get", {"documento_id": documento["id"]})
    assert detalle["total"] == 20000 and detalle["descuento"] == 5000
    assert [l["descuento"] for l in detalle["lineas"]] == [3600, 1400]
    assert detalle["base"] == 13333 + 5185 and detalle["impuestos"] == 20000 - 18518


def test_numeracion_consecutiva_sin_saltos(esquina):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    numeros = []
    for _ in range(3):
        orden = pedido(caja, admin, [("Agua sin gas", 1)])
        # Un cobro rechazado no consume número
        cuenta = caja.data("/cuenta/abrir", {"sesion_mesa_id": orden["sesion_mesa_id"]})
        caja.post("/cuenta/pagar", {"cuenta_id": cuenta["id"], "clave_idempotencia": key(), "pagos": [
            {"medio_pago_id": medio(caja, "Efectivo"), "monto": 999999}]}, expect=400)
        numeros.append(int(cobrar(caja, orden)["data"]["documentos"][0]["numero"].replace("POSE", "")))
    assert numeros == list(range(numeros[0], numeros[0] + 3))


def test_factura_a_nombre_del_cliente_al_pagar_y_despues(esquina):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]

    # Pedirla al pagar exige documento del cliente
    orden = pedido(caja, admin, [("Salchipapa", 1)])
    respuesta = cobrar(caja, orden, factura={"nombre": "Juan Pérez", "tipo_documento": "CC"}, expect=400)
    assert "documento del cliente" in respuesta["message"]
    factura = cobrar(caja, orden, factura={"nombre": "Juan Pérez", "tipo_documento": "CC", "documento": "1020 304 050",
                                           "correo": "juan@correo.co"})["data"]["documentos"][0]
    assert factura["tipo"] == "factura" and factura["numero"].startswith("FE")
    assert factura["receptor_documento"] == "1020304050"

    # Después de pagar: el POS se anula con nota crédito y sale la factura
    orden = pedido(caja, admin, [("Perro sencillo", 1)])
    pos = cobrar(caja, orden)["data"]["documentos"][0]
    nueva = caja.data("/documento/facturar", {"cuenta_id": pos["cuenta_id"], "receptor": {
        "nombre": "Comercial Andes SAS", "tipo_documento": "NIT", "documento": "900123456-7"}}, expect=201)
    assert nueva["tipo"] == "factura"
    assert caja.post("/documento/facturar", {"cuenta_id": pos["cuenta_id"], "receptor": {
        "nombre": "Otra", "tipo_documento": "CC", "documento": "123456"}}).status_code == 409

    enviar(caja)
    original = caja.data("/documento/get", {"documento_id": pos["id"]})
    assert original["estado"] == "anulada" and len(original["notas"]) == 1
    nota = find(caja.data("/documento/list", {"tipo": "nota_credito"}), origen=pos["numero"])
    assert nota["estado"] == "aceptada" and nota["total"] == pos["total"]


def test_proveedor_caido_no_bloquea_el_cobro(esquina):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    modo_proveedor(admin, "caido")
    try:
        orden = pedido(caja, admin, [("Gaseosa 400 ml", 1)])
        pagada = cobrar(caja, orden)
        assert pagada["data"]["estado"] == "pagada"
        documento = pagada["data"]["documentos"][0]
        enviar(caja)
        en_cola = caja.data("/documento/get", {"documento_id": documento["id"]})
        assert en_cola["estado"] == "pendiente" and en_cola["intentos"] == 1 and en_cola["proximo_intento_en"]
        assert "no responde" in en_cola["mensaje"]
        # Mientras espera su turno no se reenvía
        enviar(caja)
        assert caja.data("/documento/get", {"documento_id": documento["id"]})["intentos"] == 1
    finally:
        modo_proveedor(admin, "aceptar")
    enviar(caja, [documento["id"]])
    assert caja.data("/documento/get", {"documento_id": documento["id"]})["estado"] == "aceptada"


def test_documento_rechazado_se_corrige_con_el_mismo_numero(esquina):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    modo_proveedor(admin, "rechazar")
    try:
        documento = cobrar(caja, pedido(caja, admin, [("Jugo de mango", 1)]))["data"]["documentos"][0]
        enviar(caja)
        assert caja.data("/documento/get", {"documento_id": documento["id"]})["estado"] == "rechazada"
        estado = admin.data("/facturacion/estado")
        assert any("rechazado" in a["texto"] for a in estado["alertas"])
        # El cajero no corrige documentos
        assert caja.post("/documento/corregir", {"documento_id": documento["id"]}).status_code == 403
    finally:
        modo_proveedor(admin, "aceptar")
    corregido = admin.data("/documento/corregir", {"documento_id": documento["id"]})
    assert corregido["estado"] == "aceptada" and corregido["numero"] == documento["numero"]


def test_anular_cuenta_emite_nota_credito(esquina):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    documento = cobrar(caja, pedido(caja, admin, [("Cerveza nacional", 2)]))["data"]["documentos"][0]
    enviar(caja)
    hoy = date.fromisoformat(str(documento["jornada"]))
    antes = admin.data("/documento/impuestos", {"desde": hoy.isoformat(), "hasta": hoy.isoformat()})["totales"]

    anulada = admin.data("/cuenta/anular", {"cuenta_id": documento["cuenta_id"], "motivo": "Cobro duplicado"})
    nota = find(anulada["documentos"], tipo="nota_credito")
    assert nota["origen"] == documento["numero"] and nota["motivo"] == "Cobro duplicado"
    enviar(caja)
    assert caja.data("/documento/get", {"documento_id": documento["id"]})["estado"] == "anulada"
    # Las notas crédito restan en el informe por impuesto
    despues = admin.data("/documento/impuestos", {"desde": hoy.isoformat(), "hasta": hoy.isoformat()})["totales"]
    assert antes["total"] - despues["total"] == 14000


def test_impuesto_del_producto_y_cambio_de_tasa_con_vigencia(esquina):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    impuestos = admin.data("/impuesto/list")
    iva = find(impuestos, nombre="IVA")
    assert find(impuestos, nombre="Impuesto al consumo")["por_defecto"] is True

    # Un producto con impuesto propio usa ese y no el por defecto
    jugo = find(admin.data("/producto/list", {"todos": True}), nombre="Jugo de mango")
    campos = {k: jugo[k] for k in ("categoria_id", "nombre", "descripcion", "precio", "punto_produccion_id", "orden")}
    admin.data("/producto/update", {**campos, "producto_id": jugo["id"], "impuesto_id": iva["id"]})
    try:
        documento = cobrar(caja, pedido(caja, admin, [("Jugo de mango", 1)]))["data"]["documentos"][0]
        linea = caja.data("/documento/get", {"documento_id": documento["id"]})["lineas"][0]
        assert linea["porcentaje"] == 19.0 and linea["base"] == 5882 and linea["impuesto_valor"] == 1118
    finally:
        admin.data("/producto/update", {**campos, "producto_id": jugo["id"], "impuesto_id": None})

    # Un cambio de tasa se programa: no aplica hacia atrás ni cambia ventas hechas (RN-FIS-01)
    nuevo = admin.data("/impuesto/create", {"nombre": "Tasa de prueba", "tipo": "otro", "porcentaje": 5}, expect=201)
    hoy = date.fromisoformat(str(nuevo["tarifas"][0]["vigente_desde"]))
    assert admin.post("/impuesto/tarifa", {"impuesto_id": nuevo["id"], "porcentaje": 6,
                                           "vigente_desde": (hoy - timedelta(days=1)).isoformat()}).status_code == 400
    programado = admin.data("/impuesto/tarifa", {"impuesto_id": nuevo["id"], "porcentaje": 6,
                                                 "vigente_desde": (hoy + timedelta(days=1)).isoformat()})
    assert programado["porcentaje"] == 5.0
    assert [t["porcentaje"] for t in programado["tarifas"]] == [6.0, 5.0]
    assert str(programado["tarifas"][1]["vigente_hasta"]) == hoy.isoformat()
    # El mesero no configura impuestos
    mesero, _ = esquina["mesero.salon"]
    assert mesero.post("/impuesto/create", {"nombre": "X", "tipo": "otro", "porcentaje": 1}).status_code == 403


def test_resoluciones_y_venta_sin_resolucion(esquina):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    pos = find(admin.data("/resolucion/list"), tipo_documento="pos")
    campos = {k: pos[k] for k in ("tipo_documento", "numero_resolucion", "prefijo", "desde", "hasta", "vigente_desde",
                                  "vigente_hasta", "alerta_restantes")}
    # No se cruzan rangos con el mismo prefijo ni se recorta por debajo de lo usado
    assert admin.post("/resolucion/create", {**campos, "desde": 10, "hasta": 20}).status_code == 400
    respuesta = admin.post("/resolucion/update", {**campos, "resolucion_id": pos["id"], "hasta": pos["ultimo"] - 1})
    assert respuesta.status_code == 400 and "Ya se usó" in respuesta.json()["message"]

    # Sin resolución vigente se vende igual; la cuenta queda sin documento y con aviso
    admin.data("/resolucion/change_status", {"resolucion_id": pos["id"], "activo": False})
    try:
        pagada = cobrar(caja, pedido(caja, admin, [("Agua sin gas", 1)]))
        assert pagada["data"]["estado"] == "pagada" and pagada["data"]["documentos"] == []
        assert "No se generó documento" in pagada["message"]
        estado = admin.data("/facturacion/estado")
        assert any(c["id"] == pagada["data"]["id"] for c in estado["cuentas_sin_documento"])
    finally:
        admin.data("/resolucion/change_status", {"resolucion_id": pos["id"], "activo": True})
    generado = caja.data("/documento/facturar", {"cuenta_id": pagada["data"]["id"]}, expect=201)
    assert generado["tipo"] == "pos"


def test_credenciales_y_permisos(esquina, napoli):
    admin, _ = esquina["admin.esquina"]
    mesero, _ = esquina["mesero.salon"]
    config = admin.data("/facturacion/config/get")
    assert config["credenciales_guardadas"] is True and "credenciales" not in config
    assert mesero.post("/documento/list").status_code == 403
    admin_napoli, _ = napoli["napoli"]
    assert admin_napoli.post("/documento/list").json()["detail"]["codigo"] == "modulo_no_contratado"
