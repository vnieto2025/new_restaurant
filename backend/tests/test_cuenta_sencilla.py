"""
Cuenta sencilla de la mesa (ADR-057): en un restaurante sin caja, el mesero o la cocina imprimen para el cliente
todo lo consumido, el IVA incluido y la propina sugerida. Es informativa: no es factura electrónica.
"""
from conftest import key, find, product_id, table


def test_cuenta_de_la_mesa_con_iva_y_propina(napoli):
    duena, _ = napoli["napoli"]
    mesero, _ = napoli["mesero.napoli"]
    cocina, _ = napoli["cocina.napoli"]
    if not duena.data("/impuesto/list"):
        duena.data("/impuesto/create", {"nombre": "IVA", "tipo": "iva", "porcentaje": 19}, expect=201)

    mesa = table(mesero, "Mesa 2")
    pizza = product_id(duena, "Pizza margarita")
    primera = mesero.data("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(),
                                            "items": [{"producto_id": pizza, "cantidad": 1}]}, expect=201)
    mesero.data("/orden/agregar_items", {"orden_id": primera["id"], "clave_idempotencia": key(),
                                         "items": [{"producto_id": pizza, "cantidad": 1},
                                                   {"producto_id": product_id(duena, "Pizza napolitana"), "cantidad": 1}]})

    cuenta = mesero.data("/orden/cuenta", {"mesa_id": mesa["id"]})
    # Las dos margaritas, pedidas en momentos distintos, salen en una línea
    assert find(cuenta["lineas"], nombre="Pizza margarita")["cantidad"] == 2
    assert cuenta["subtotal"] == 32000 * 2 + 36000 and cuenta["sencilla"] is True
    # El precio ya trae el IVA: base + IVA = total
    [iva] = cuenta["desglose"]["impuestos"]
    assert iva["impuesto"] == "IVA" and iva["porcentaje_texto"] == "19"
    assert cuenta["desglose"]["base"] + iva["valor"] == cuenta["subtotal"]
    assert cuenta["propina_porcentaje"] == 10 and cuenta["propina_sugerida"] == 10000
    assert cuenta["total_con_propina"] == 110000

    # La cocina la imprime desde la comanda: la misma cuenta de toda la mesa
    desde_cocina = cocina.data("/orden/cuenta", {"orden_id": primera["id"]})
    assert desde_cocina["subtotal"] == cuenta["subtotal"]

    for item in mesero.data("/orden/get", {"orden_id": primera["id"]})["items"]:
        mesero.data("/orden/cancelar_item", {"orden_item_id": item["id"], "motivo": "Prueba de cuenta"})
    mesero.data("/mesa/cerrar", {"mesa_id": mesa["id"]})
    assert mesero.post("/orden/cuenta", {"mesa_id": mesa["id"]}).status_code == 409


def test_cuenta_solo_de_lo_propio(esquina, napoli):
    mesero_salon, _ = esquina["mesero.salon"]
    admin, _ = esquina["admin.esquina"]
    # Un mesero del Salón no imprime la cuenta de la Terraza
    assert mesero_salon.post("/orden/cuenta", {"mesa_id": table(admin, "Terraza 1")["id"]}).status_code == 403
    assert mesero_salon.post("/orden/cuenta", {}).status_code == 400
