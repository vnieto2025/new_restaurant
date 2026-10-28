"""
Pagos en línea (doc 20A): el cliente paga desde su celular, el resultado solo lo decide el aviso firmado de la
pasarela, el intento tiene monto fijo, nada se aplica dos veces, la diferencia queda por reembolsar y caja concilia.
"""
import json
from conftest import Api, key, find, product_id, table, ensure_shift, qr_token, pay_table, medio


def ordenar(mesero, admin, mesa, cantidad=2):
    return mesero.data("/orden/create", {"mesa_id": table(mesero, mesa)["id"], "clave_idempotencia": key(), "items": [
        {"producto_id": product_id(admin, "Agua sin gas"), "cantidad": cantidad}]}, expect=201)


def pagar(publico, origen, propina=0, clave=None, decision="aprobar"):
    """ Cliente: inicia el pago y responde en la página de la pasarela simulada """
    iniciado = publico.data("/publico/pago/crear", {**origen, "propina": propina, "clave_idempotencia": clave or key()},
                            expect=201)
    referencia = iniciado["url"].rsplit("/", 1)[1]
    if decision:
        publico.data("/publico/pasarela/responder", {"referencia": referencia, "decision": decision})
    return iniciado, referencia


def test_pago_desde_el_qr_de_la_mesa(esquina, client):
    mesero, _ = esquina["mesero.terraza"]
    admin, _ = esquina["admin.esquina"]
    caja, _ = esquina["caja.esquina"]
    ensure_shift(caja)
    publico = Api(client)
    ordenar(mesero, admin, "Terraza 4")
    origen = {"token": qr_token(admin, "Terraza 4")}

    cuenta = publico.data("/publico/pago/cuenta", origen)
    assert cuenta["disponible"] and cuenta["saldo"] > 0 and cuenta["lineas"]
    saldo = cuenta["saldo"]

    clave = key()
    iniciado, referencia = pagar(publico, origen, propina=1000, clave=clave, decision=None)
    assert iniciado["monto"] == saldo + 1000 and iniciado["url"].startswith("/pasarela-simulada/")
    # Reintento con la misma clave: el mismo intento (idempotencia)
    assert pagar(publico, origen, propina=1000, clave=clave, decision=None)[0]["pago"] == iniciado["pago"]
    assert publico.data("/publico/pago/estado", {"pago": iniciado["pago"]})["estado"] == "pendiente"

    # Un aviso falso de "aprobado" sin firma válida no aprueba nada (RN-PAG-01)
    falso = json.dumps({"referencia": referencia, "estado": "aprobado", "monto": saldo + 1000}).encode()
    respuesta = client.post("/webhook/pagos/simulada", content=falso, headers={"x-firma": "inventada"})
    assert respuesta.status_code == 401
    assert publico.data("/publico/pago/estado", {"pago": iniciado["pago"]})["estado"] == "pendiente"

    publico.data("/publico/pasarela/responder", {"referencia": referencia, "decision": "aprobar"})
    estado = publico.data("/publico/pago/estado", {"pago": iniciado["pago"]})
    assert estado["estado"] == "aprobado" and estado["cuenta_pagada"]
    # Responder otra vez no aplica el pago dos veces
    publico.data("/publico/pasarela/responder", {"referencia": referencia, "decision": "aprobar"})

    pagada = next(c for c in caja.data("/cuenta/list", {"estado": "pagada"}) if c["mesa"] == "Terraza 4")
    detalle = caja.data("/cuenta/get", {"cuenta_id": pagada["id"]})
    assert detalle["propina"] == 1000 and detalle["pagado"] == saldo + 1000
    assert [p["medio"] for p in detalle["pagos"]] == ["Pago en línea"] and detalle["documentos"]
    assert publico.post("/publico/pago/cuenta", origen).status_code == 404  # la mesa quedó libre
    # El cajero no puede elegir el medio de la pasarela
    assert not any(m["nombre"] == "Pago en línea" for m in caja.data("/caja/estado")["medios"])


def test_cuenta_que_cambia_reembolso_y_conciliacion(esquina, client):
    mesero, _ = esquina["mesero.terraza"]
    admin, _ = esquina["admin.esquina"]
    caja, _ = esquina["caja.esquina"]
    ensure_shift(caja)
    publico = Api(client)

    # Mientras el cliente pagaba se pidió algo más: se abona lo pagado y caja cobra la diferencia
    orden = ordenar(mesero, admin, "Terraza 3")
    origen = {"token": qr_token(admin, "Terraza 3")}
    iniciado, _ = pagar(publico, origen, decision=None)
    mesero.data("/orden/agregar_items", {"orden_id": orden["id"], "clave_idempotencia": key(), "items": [
        {"producto_id": product_id(admin, "Agua sin gas"), "cantidad": 1}]})
    referencia = iniciado["url"].rsplit("/", 1)[1]
    publico.data("/publico/pasarela/responder", {"referencia": referencia, "decision": "aprobar"})
    cuenta = publico.data("/publico/pago/cuenta", origen)
    assert cuenta["estado"] == "abierta" and cuenta["pagado"] == iniciado["monto"] and cuenta["saldo"] > 0
    pay_table(caja, mesa_id=table(caja, "Terraza 3")["id"])

    # La cuenta se pagó en caja antes de que llegara la aprobación: todo queda por reembolsar
    ordenar(mesero, admin, "Terraza 3")
    iniciado, referencia = pagar(publico, origen, decision=None)
    pay_table(caja, mesa_id=table(caja, "Terraza 3")["id"])
    publico.data("/publico/pasarela/responder", {"referencia": referencia, "decision": "aprobar"})
    por_reembolsar = admin.data("/pago_linea/list", {"estado": "por_reembolsar"})
    pago = find(por_reembolsar["pagos"], referencia=referencia)
    assert pago["aplicado"] == 0 and pago["excedente"] == iniciado["monto"] and pago["reembolsable"] == iniciado["monto"]

    # Reembolso solo con permiso y motivo (RN-PAG-03)
    assert caja.post("/pago_linea/reembolsar", {"intento_pago_id": pago["id"], "motivo": "Pagó dos veces"}).status_code == 403
    assert admin.post("/pago_linea/reembolsar", {"intento_pago_id": pago["id"]}).status_code == 422
    assert admin.post("/pago_linea/reembolsar", {"intento_pago_id": pago["id"], "monto": pago["monto"] + 1,
                                                 "motivo": "Pagó dos veces"}).status_code == 400
    parcial = admin.data("/pago_linea/reembolsar", {"intento_pago_id": pago["id"], "monto": 1000, "motivo": "Pagó dos veces"})
    assert parcial["estado"] == "parcial" and parcial["reembolsable"] == pago["monto"] - 1000
    total = admin.data("/pago_linea/reembolsar", {"intento_pago_id": pago["id"], "motivo": "Pagó dos veces"})
    assert total["estado"] == "reembolsado" and total["reembolsable"] == 0

    # Conciliación con la fecha de abono y la comisión real de la pasarela
    aprobado = find(admin.data("/pago_linea/list")["pagos"], referencia=iniciado["url"].rsplit("/", 1)[1])
    conciliado = admin.data("/pago_linea/conciliar", {"intento_pago_id": aprobado["id"], "fecha_abono": "2026-10-27",
                                                      "comision": 500, "nota": "Extracto del día"})
    assert conciliado["fecha_abono"] == "2026-10-27" and conciliado["neto"] == conciliado["monto"] - 500 - conciliado["reembolsado"]


def test_enlace_de_pago_para_llevar_rechazo_y_reintento(esquina, napoli, client):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    publico = Api(client)
    externa = table(caja, "Para llevar", incluir_externa=True)
    orden = caja.data("/orden/create", {"mesa_id": externa["id"], "clave_idempotencia": key(), "cliente_nombre": "Pago Enlace",
                                        "cliente_telefono": "3005551234", "items": [
                                            {"producto_id": product_id(admin, "Agua sin gas"), "cantidad": 1}]}, expect=201)
    enlace = caja.data("/pago_linea/enlace", {"sesion_mesa_id": orden["sesion_mesa_id"]})
    assert enlace["seguimiento"] == orden["token_seguimiento"] and enlace["telefono"] == "573005551234"
    origen = {"seguimiento": enlace["seguimiento"]}
    assert publico.data("/publico/pago/cuenta", origen)["saldo"] == enlace["saldo"]

    rechazado, _ = pagar(publico, origen, decision="rechazar")
    assert publico.data("/publico/pago/estado", {"pago": rechazado["pago"]})["estado"] == "rechazado"
    assert publico.data("/publico/pago/cuenta", origen)["estado"] == "abierta"  # puede pagar en caja (RN-PAG-04)
    aprobado, _ = pagar(publico, origen)
    assert publico.data("/publico/pago/estado", {"pago": aprobado["pago"]})["cuenta_pagada"]
    assert publico.post("/publico/pago/crear", {**origen, "clave_idempotencia": key()}).status_code == 409  # ya pagada

    # El QR de para llevar no sirve para pagar: se paga con el enlace del pedido
    assert publico.post("/publico/pago/cuenta", {"token": qr_token(admin, "Para llevar")}).status_code == 409
    # Un restaurante sin el módulo no ofrece el pago
    otro, _ = napoli["napoli"]
    assert otro.post("/pago_linea/enlace", {"sesion_mesa_id": orden["sesion_mesa_id"]}).status_code == 403
