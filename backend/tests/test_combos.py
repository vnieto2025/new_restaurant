"""
Combos (doc 12, sección 4): el combo es la línea que se cobra; sus componentes van a cada cocina con valor 0,
descuentan su inventario y mueven el estado del combo. Cancelar una parte cancela el combo completo.
"""
from conftest import Api, find, key, product_id, option_id, table, pay_table, ensure_shift, qr_token

COMBO = "Combo clásico"


def combo_de(api):
    return find(api.data("/producto/list", {"todos": True}), nombre=COMBO)


def componente(combo, nombre):
    return find(combo["componentes"], nombre=nombre)


def eleccion(api, bebida="Limonada natural", termino="Medio"):
    combo = combo_de(api)
    return combo, [
        {"componente_id": componente(combo, "Hamburguesa")["id"], "producto_id": product_id(api, "Hamburguesa clásica"),
         "modificadores": [option_id(api, "Término de la carne", termino)]},
        {"componente_id": componente(combo, "Bebida")["id"], "producto_id": product_id(api, bebida)},
    ]


def pedir_en_mesa(mesero, admin, mesa, **extra):
    combo, componentes = eleccion(admin, **extra)
    return mesero.data("/orden/create", {"mesa_id": table(mesero, mesa)["id"], "clave_idempotencia": key(),
                                         "items": [{"producto_id": combo["id"], "cantidad": 1, "componentes": componentes, "nota": "Sin cebolla"}]},
                       expect=201)


def stock(api, nombre):
    return find(api.data("/insumo/list", {"todos": True}), nombre=nombre)["stock"]


def despachar_todo(api, punto, orden_id):
    sesion = api.data("/auth/sesion")
    punto_id = find(sesion["puntos"], nombre=punto)["id"]
    for tarjeta in [t for t in api.data("/cocina/comandas", {"punto_produccion_id": punto_id})["en_proceso"] if t["orden_id"] == orden_id]:
        api.data("/cocina/abrir", {"comanda_id": tarjeta["id"]})
        api.data("/cocina/despachar", {"comanda_id": tarjeta["id"]})
        return tarjeta


def test_crear_combo_y_validaciones(esquina):
    admin, _ = esquina["admin.esquina"]
    combo = combo_de(admin)
    assert combo["tipo"] == "combo" and [c["nombre"] for c in combo["componentes"]] == ["Hamburguesa", "Acompañamiento", "Bebida"]
    assert find(componente(combo, "Bebida")["opciones"], nombre="Limonada natural")["precio_extra"] == 1500

    base = {"categoria_id": combo["categoria_id"], "nombre": "Combo prueba", "precio": 20000, "tipo": "combo"}
    papas = product_id(admin, "Papas a la francesa")
    assert "componente" in admin.post("/producto/create", {**base, "componentes": []}).json()["message"]
    # Un combo no va dentro de otro
    assert "otro" in admin.post("/producto/create", {**base, "componentes": [
        {"nombre": "Todo", "opciones": [{"producto_id": combo["id"]}]}]}).json()["message"]
    assert "repetido" in admin.post("/producto/create", {**base, "componentes": [
        {"nombre": "Papas", "opciones": [{"producto_id": papas}, {"producto_id": papas}]}]}).json()["message"]
    # Un producto que está en un combo no se convierte en combo
    hamburguesa = find(admin.data("/producto/list", {"todos": True}), nombre="Hamburguesa clásica")
    convertir = admin.post("/producto/update", {**{k: hamburguesa[k] for k in ("categoria_id", "nombre", "precio")},
                                                "producto_id": hamburguesa["id"], "tipo": "combo",
                                                "componentes": [{"nombre": "X", "opciones": [{"producto_id": papas}]}]})
    assert convertir.status_code == 400 and COMBO in convertir.json()["message"]


def test_combo_en_mesa_cocina_cobro_y_factura(esquina):
    admin, _ = esquina["admin.esquina"]
    mesero, _ = esquina["mesero.terraza"]
    cocina, _ = esquina["cocina.esquina"]
    bar, _ = esquina["bar.esquina"]
    caja, _ = esquina["caja.esquina"]
    carne = stock(admin, "Carne de res molida")
    papa = stock(admin, "Papa")

    orden = pedir_en_mesa(mesero, admin, "Terraza 2")
    # Se cobra el combo con lo extra de la limonada; los componentes van a su cocina con valor 0
    padre = find(orden["items"], nombre=COMBO)
    partes = [i for i in orden["items"] if i["combo_item_id"] == padre["id"]]
    assert padre["es_combo"] and padre["total"] == 26000 + 1500 and orden["total"] == 27500
    assert {p["nombre"] for p in partes} == {"Hamburguesa clásica", "Papas a la francesa", "Limonada natural"}
    assert all(p["total"] == 0 for p in partes) and padre["punto_produccion"] == "Despacho directo"
    assert find(partes, nombre="Hamburguesa clásica")["modificadores"][0]["nombre"] == "Medio"

    # El combo no está listo mientras falte una parte
    tarjeta = despachar_todo(cocina, "Cocina", orden["id"])
    assert any(i["combo"] == COMBO and i["nota"] == "Sin cebolla" for i in tarjeta["items"])
    assert find(mesero.data("/orden/get", {"orden_id": orden["id"]})["items"], nombre=COMBO)["estado"] == "en_proceso"
    despachar_todo(bar, "Bar", orden["id"])
    assert find(mesero.data("/orden/get", {"orden_id": orden["id"]})["items"], nombre=COMBO)["estado"] == "despachado"
    entregada = mesero.data("/orden/entregar", {"orden_id": orden["id"]})
    assert {i["estado"] for i in entregada["items"]} == {"entregado"} and entregada["estado"] == "entregada"

    # Inventario: descuentan las partes, no el combo
    assert stock(admin, "Carne de res molida") < carne and stock(admin, "Papa") < papa

    # En la cuenta y en la factura es una sola línea con su detalle
    cuenta = caja.data("/cuenta/abrir", {"mesa_id": table(mesero, "Terraza 2")["id"]})
    assert cuenta["items_pendientes"] == 0
    linea = find(cuenta["lineas"], nombre=COMBO)
    assert len([l for l in cuenta["lineas"] if l["orden"] == f"#{orden['numero']:03d}"]) == 1
    assert {"Papas a la francesa", "Limonada natural"} <= {m["nombre"] for m in linea["modificadores"]}
    assert any(m["nombre"].startswith("Hamburguesa clásica (Medio") for m in linea["modificadores"])
    pagada = pay_table(caja, mesa_id=table(mesero, "Terraza 2")["id"])
    documento = caja.data("/documento/get", {"documento_id": pagada["documentos"][0]["id"]})
    combo_linea = [l for l in documento["lineas"] if COMBO in l["descripcion"]]
    assert len(combo_linea) == 1 and "Papas a la francesa" in combo_linea[0]["descripcion"] and combo_linea[0]["total"] == 27500
    assert not [l for l in documento["lineas"] if l["total"] == 0]


def test_cancelar_una_parte_cancela_el_combo(esquina):
    admin, _ = esquina["admin.esquina"]
    mesero, _ = esquina["mesero.terraza"]
    bar, _ = esquina["bar.esquina"]
    orden = pedir_en_mesa(mesero, admin, "Terraza 3", bebida="Gaseosa 400 ml")
    padre = find(orden["items"], nombre=COMBO)
    assert padre["total"] == 26000  # la gaseosa no suma

    papas = find(orden["items"], nombre="Papas a la francesa")
    cancelada = mesero.data("/orden/cancelar_item", {"orden_item_id": papas["id"], "motivo": "El cliente cambió de idea"})
    assert {i["estado"] for i in cancelada["items"]} == {"cancelado"} and cancelada["total"] == 0

    # Si cocina agota una parte, cae el combo completo
    otra = pedir_en_mesa(mesero, admin, "Terraza 3", bebida="Limonada natural")
    sesion = bar.data("/auth/sesion")
    punto = find(sesion["puntos"], nombre="Bar")["id"]
    tarjeta = next(t for t in bar.data("/cocina/comandas", {"punto_produccion_id": punto})["en_proceso"] if t["orden_id"] == otra["id"])
    limonada = find(tarjeta["items"], nombre="Limonada natural")
    bar.data("/cocina/agotado", {"orden_item_id": limonada["id"], "motivo": "Sin limones"})
    despues = mesero.data("/orden/get", {"orden_id": otra["id"]})
    assert {i["estado"] for i in despues["items"]} == {"cancelado"} and despues["total"] == 0
    # Y la carta ya no ofrece la limonada en el combo
    carta = mesero.data("/orden/carta", {"mesa_id": table(mesero, "Terraza 3")["id"]})
    en_carta = next(p for c in carta["categorias"] for p in c["productos"] if p["nombre"] == COMBO)
    assert "Limonada natural" not in [o["nombre"] for o in componente(en_carta, "Bebida")["opciones"]] and not en_carta["agotado"]
    admin.data("/producto/agotado", {"producto_id": product_id(admin, "Limonada natural"), "agotado": False})


def test_elecciones_obligatorias_y_precio_del_servidor(esquina):
    admin, _ = esquina["admin.esquina"]
    mesero, _ = esquina["mesero.terraza"]
    combo, componentes = eleccion(admin)
    mesa = table(mesero, "Terraza 4")["id"]
    pedir = lambda comps: mesero.post("/orden/create", {"mesa_id": mesa, "clave_idempotencia": key(),  # noqa: E731
                                                        "items": [{"producto_id": combo["id"], "cantidad": 2, "componentes": comps}]})
    assert "bebida" in pedir(componentes[:1]).json()["message"].lower()
    sin_termino = [{**componentes[0], "modificadores": []}, componentes[1]]
    assert "término" in pedir(sin_termino).json()["message"].lower()
    ajena = [componentes[0], {**componentes[1], "producto_id": product_id(admin, "Cerveza nacional")}]
    assert pedir(ajena).status_code == 409
    # Dos combos: el valor se multiplica y las partes también
    orden = pedir(componentes).json()["data"]
    assert orden["total"] == 2 * 27500 and find(orden["items"], nombre="Papas a la francesa")["cantidad"] == 2


def test_reportes_cuentan_el_combo_y_aparte_sus_partes(esquina):
    admin, _ = esquina["admin.esquina"]
    caja, _ = esquina["caja.esquina"]
    ensure_shift(caja)
    combo, componentes = eleccion(admin)
    venta = caja.data("/pos/vender", {"clave_idempotencia": key(), "items": [{"producto_id": combo["id"], "cantidad": 1, "componentes": componentes}]}, expect=201)
    assert venta["total"] == 27500
    ventas = admin.data("/reporte/ventas")
    nombres = {f["nombre"] for f in ventas["productos"]}
    assert COMBO in nombres and "Limonada natural" not in {f["nombre"] for f in ventas["productos"] if f["valor"] == 0}
    assert find(ventas["componentes_combo"], nombre="Papas a la francesa")["unidades"] >= 1
    assert find(ventas["categorias"], nombre="Combos")["valor"] >= 27500


def test_qr_con_aprobacion_y_rechazo(client, esquina):
    admin, _ = esquina["admin.esquina"]
    mesero, _ = esquina["mesero.salon"]
    combo, componentes = eleccion(admin)
    publico = Api(client)
    token = qr_token(admin, "Mesa 8")
    carta = publico.data("/publico/qr", {"token": token})
    en_carta = next(p for c in carta["categorias"] for p in c["productos"] if p["nombre"] == COMBO)
    assert en_carta["tipo"] == "combo" and componente(en_carta, "Hamburguesa")["opciones"][0]["grupos"]

    pedido = publico.data("/publico/orden/create", {"token": token, "clave_idempotencia": key(),
                                                    "items": [{"producto_id": combo["id"], "cantidad": 1, "componentes": componentes}]}, expect=201)
    assert pedido["estado"] == "pendiente_aprobacion"
    orden = find(mesero.data("/orden/list"), numero_texto=pedido["numero_texto"])
    rechazada = mesero.data("/orden/rechazar", {"orden_id": orden["id"], "motivo": "Mesa vacía"})
    assert {i["estado"] for i in rechazada["items"]} == {"cancelado"}

    pedido = publico.data("/publico/orden/create", {"token": token, "clave_idempotencia": key(),
                                                    "items": [{"producto_id": combo["id"], "cantidad": 1, "componentes": componentes}]}, expect=201)
    orden = find(mesero.data("/orden/list"), numero_texto=pedido["numero_texto"])
    aprobada = mesero.data("/orden/aprobar", {"orden_id": orden["id"]})
    assert find(aprobada["items"], nombre=COMBO)["estado"] == "nuevo"
    assert find(aprobada["items"], nombre="Hamburguesa clásica")["estado"] == "nuevo"
    # La mesa queda libre para las demás pruebas
    mesero.data("/orden/cancelar_item", {"orden_item_id": find(aprobada["items"], nombre=COMBO)["id"], "motivo": "Fin de la prueba"})
    mesero.data("/mesa/cerrar", {"mesa_id": table(mesero, "Mesa 8")["id"]})
