"""
Propinas y liquidaciones (doc 26A): reparto individual, colectivo o mixto; pozo por horas, puntos o zona; borrador
editable con ajustes con motivo; aprobada no se modifica; nada se liquida dos veces; cada persona ve lo suyo; y el
pago a domiciliarios con sus entregas, propinas y faltantes.
"""
from datetime import date, timedelta
from types import SimpleNamespace
from conftest import key, find, product_id, table, ensure_shift, medio, login
from Class.Liquidacion import repartir_propinas, periodo_de, pago_entrega

A, B = ("u", 1), ("u", 2)


def reglas(**campos):
    return {"modelo": "colectiva", "porcentaje_individual": 50, "metodo": "puntos", "por_zona": False, "retencion": 0,
            **campos}


def gente(zonas_a=None):
    return [{"clave": A, "horas": 8, "peso": 1, "zonas": zonas_a, "participa": True},
            {"clave": B, "horas": 4, "peso": 1, "zonas": None, "participa": True}]


PROPINAS = [{"monto": 1000, "mesero_id": 1, "zona_id": 10}, {"monto": 2000, "mesero_id": None, "zona_id": 20}]


def test_reparto_de_propinas():
    colectiva = repartir_propinas(PROPINAS, gente(), reglas())
    assert colectiva["pozo"][A]["total"] == 1500 and colectiva["pozo"][B]["total"] == 1500

    # Individual: la propina con mesero es suya; la de mostrador va al pozo
    individual = repartir_propinas(PROPINAS, gente(), reglas(modelo="individual"))
    assert individual["individual"] == {1: 1000} and individual["pozo"][A]["total"] == 1000

    mixta = repartir_propinas(PROPINAS, gente(), reglas(modelo="mixta"))
    assert mixta["individual"] == {1: 500} and mixta["pozo"][A]["total"] == 1250 and mixta["pozo"][B]["total"] == 1250

    # Horas x puntos: A trabajó el doble
    horas = repartir_propinas(PROPINAS, gente(), reglas(metodo="horas_puntos"))
    assert horas["pozo"][A]["total"] == 2000 and horas["pozo"][B]["total"] == 1000

    retencion = repartir_propinas(PROPINAS, gente(), reglas(retencion=10))
    assert retencion["retenido"] == 300 and retencion["pozo_total"] == 2700

    # Por zona: A solo atiende la zona 10, así que el pozo de la zona 20 es de B
    zona = repartir_propinas(PROPINAS, gente(zonas_a=[10]), reglas(por_zona=True))
    assert zona["pozo"][A]["total"] == 500 and zona["pozo"][B]["total"] == 2500

    # Sin horas no hay con qué repartir: queda a la vista, no se pierde
    sin_horas = repartir_propinas(PROPINAS, [{**g, "horas": 0} for g in gente()], reglas(metodo="horas"))
    assert sin_horas["sin_repartir"] == 3000 and not sin_horas["pozo"]

    # Siempre cuadra al peso
    raro = repartir_propinas([{"monto": 1001, "mesero_id": None, "zona_id": 1}],
                             [{"clave": ("u", i), "horas": 1, "peso": 1, "zonas": None, "participa": True} for i in range(3)],
                             reglas())
    assert sum(p["total"] for p in raro["pozo"].values()) == 1001


def test_periodos_y_pago_por_entrega():
    assert periodo_de(date(2026, 10, 27), "quincenal") == (date(2026, 10, 16), date(2026, 10, 31))
    assert periodo_de(date(2026, 2, 3), "quincenal") == (date(2026, 2, 1), date(2026, 2, 15))
    assert periodo_de(date(2026, 10, 28), "semanal") == (date(2026, 10, 26), date(2026, 11, 1))
    assert periodo_de(date(2026, 2, 10), "mensual") == (date(2026, 2, 1), date(2026, 2, 28))
    entrega = SimpleNamespace(tarifa=4000, pago_domiciliario=3500)
    assert pago_entrega(entrega, {"pago_domicilio": "zona"}) == 3500
    assert pago_entrega(entrega, {"pago_domicilio": "porcentaje", "pago_porcentaje": 80}) == 3200
    assert pago_entrega(entrega, {"pago_domicilio": "mixto", "pago_base": 1000, "pago_porcentaje": 50}) == 3000


def cobrar_con_propina(caja, mesero, admin, mesa, propina):
    mesa_id = table(caja, mesa)["id"]
    mesero.data("/orden/create", {"mesa_id": mesa_id, "clave_idempotencia": key(), "items": [
        {"producto_id": product_id(admin, "Limonada natural"), "cantidad": 1}]}, expect=201)
    cuenta = caja.data("/cuenta/abrir", {"mesa_id": mesa_id})
    cuenta = caja.data("/cuenta/ajustar", {"cuenta_id": cuenta["id"], "propina": propina})
    return caja.data("/cuenta/pagar", {"cuenta_id": cuenta["id"], "clave_idempotencia": key(), "pagos": [
        {"medio_pago_id": medio(caja, "Efectivo"), "monto": cuenta["saldo"]}]})


def cuadra(liquidacion):
    resumen = liquidacion["resumen"]
    repartido = sum(l["individual"] + l["pozo"] for l in liquidacion["lineas"])
    return repartido + resumen["retenido"] + resumen["sin_repartir"] == resumen["propinas"]


def test_liquidacion_de_propinas(esquina):
    admin, _ = esquina["admin.esquina"]
    caja, _ = esquina["caja.esquina"]
    mesero, sesion_mesero = esquina["mesero.terraza"]
    ensure_shift(caja)
    admin.data("/liquidacion/config/save", {"periodo": "quincenal", "modelo": "mixta", "porcentaje_individual": 50,
                                            "metodo": "puntos", "por_zona": False, "retencion": 0,
                                            "propina_domicilio": "pozo"})
    # La retención tiene tope
    assert admin.post("/liquidacion/config/save", {"retencion": 80}).status_code == 400
    cobrar_con_propina(caja, mesero, admin, "Terraza 1", 2000)

    abierta = admin.data("/liquidacion/periodo", {"tipo": "propinas"})
    assert abierta["estado"] == "abierta" and abierta["resumen"]["propinas"] >= 2000 and cuadra(abierta)
    # El mesero no liquida; solo ve lo suyo (RN-PRP-05)
    assert mesero.post("/liquidacion/calcular", {"tipo": "propinas"}).status_code == 403
    assert mesero.data("/liquidacion/mias")["periodo_actual"]["propinas_mesas"] >= 2000

    borrador = admin.data("/liquidacion/calcular", {"tipo": "propinas"})
    assert borrador["estado"] == "calculada" and cuadra(borrador)
    propio = find(borrador["lineas"], usuario_id=sesion_mesero["usuario"]["id"])
    assert propio["individual"] >= 1000 and propio["rol"] == "mesero"

    # Cocina no participa este periodo: su parte se reparte entre los demás y todo sigue cuadrando
    cocina = find(borrador["lineas"], rol="cocina")
    editado = admin.data("/liquidacion/linea", {"linea_id": cocina["id"], "participa": False, "motivo": "Acuerdo del equipo"})
    assert find(editado["lineas"], nombre=cocina["nombre"])["pozo"] == 0 and cuadra(editado)

    propio = find(editado["lineas"], usuario_id=sesion_mesero["usuario"]["id"])
    assert admin.post("/liquidacion/ajustar", {"liquidacion_id": borrador["id"], "linea_id": propio["id"], "valor": 5000,
                                               "motivo": ""}).status_code == 400  # el motivo es obligatorio
    ajustado = admin.data("/liquidacion/ajustar", {"liquidacion_id": borrador["id"], "linea_id": propio["id"], "valor": 5000,
                                                   "motivo": "Turno doble del sábado"})
    assert find(ajustado["lineas"], id=propio["id"])["total"] == propio["total"] + 5000

    # Recalcular conserva lo editado y los ajustes
    recalculada = admin.data("/liquidacion/calcular", {"tipo": "propinas", "liquidacion_id": borrador["id"]})
    assert not find(recalculada["lineas"], nombre=cocina["nombre"])["participa"]
    assert find(recalculada["lineas"], usuario_id=sesion_mesero["usuario"]["id"])["ajustes"] == 5000

    aprobada = admin.data("/liquidacion/aprobar", {"liquidacion_id": borrador["id"]})
    assert aprobada["estado"] == "aprobada"
    # Aprobada no se modifica (RN-PRP-03): el ajuste queda para la siguiente
    linea = find(aprobada["lineas"], usuario_id=sesion_mesero["usuario"]["id"])
    assert admin.post("/liquidacion/linea", {"linea_id": linea["id"], "horas": 3}).status_code == 409
    corregida = admin.data("/liquidacion/ajustar", {"liquidacion_id": borrador["id"], "linea_id": linea["id"], "valor": -1000,
                                                    "motivo": "Se le pagó de más"})
    assert corregida["pendientes"] == [{"valor": -1000, "motivo": "Se le pagó de más"}]
    assert admin.post("/liquidacion/calcular", {"tipo": "propinas"}).status_code == 409  # el periodo ya está liquidado

    # Lo liquidado no vuelve a entrar (RN-PRP-06): el siguiente periodo solo trae lo nuevo y el ajuste pendiente
    cobrar_con_propina(caja, mesero, admin, "Terraza 1", 700)
    siguiente = admin.data("/liquidacion/periodo", {"tipo": "propinas", "fecha": str(date.fromisoformat(borrador["hasta"]) + timedelta(days=1))})
    assert siguiente["resumen"]["propinas"] == 700
    assert find(siguiente["lineas"], usuario_id=sesion_mesero["usuario"]["id"])["ajustes"] == -1000

    # Pago con comprobante; al pagar a todos queda pagada
    assert admin.post("/liquidacion/pagar", {"linea_id": linea["id"], "medio_pago": "cheque"}).status_code == 400
    admin.data("/liquidacion/pagar", {"linea_id": linea["id"], "medio_pago": "transferencia", "referencia": "TR-1"})
    assert admin.post("/liquidacion/pagar", {"linea_id": linea["id"], "medio_pago": "efectivo"}).status_code == 409
    mias = mesero.data("/liquidacion/mias")["liquidaciones"]
    assert mias[0]["total"] == linea["total"] and mias[0]["referencia_pago"] == "TR-1"
    for otra in aprobada["lineas"]:
        if otra["total"] > 0 and otra["id"] != linea["id"]:
            admin.data("/liquidacion/pagar", {"linea_id": otra["id"], "medio_pago": "efectivo"})
    assert admin.data("/liquidacion/get", {"liquidacion_id": borrador["id"]})["estado"] == "pagada"


def test_liquidacion_de_domiciliarios(esquina, client):
    admin, _ = esquina["admin.esquina"]
    caja, _ = esquina["caja.esquina"]
    cocina, sesion_cocina = esquina["cocina.esquina"]
    domi, _ = login(client, "domi.esquina")
    ensure_shift(caja)
    admin.data("/liquidacion/config/save", {"pago_domicilio": "mixto", "pago_base": 1000, "pago_porcentaje": 10,
                                            "propina_domicilio": "domiciliario"})

    # Domicilio pagado en caja con propina, entregado por D01
    zona = find(caja.data("/domicilio/zona/list"), nombre="Centro")
    externa = table(caja, "Para llevar", incluir_externa=True)
    orden = caja.data("/orden/create", {
        "mesa_id": externa["id"], "clave_idempotencia": key(), "cliente_nombre": "Liquidación domicilio",
        "cliente_telefono": "3109990022", "items": [{"producto_id": product_id(admin, "Papas a la francesa"), "cantidad": 1}],
        "entrega": {"zona_envio_id": zona["id"], "direccion": "Calle 30 # 4-10", "barrio": "Centro"}}, expect=201)
    cuenta = caja.data("/cuenta/abrir", {"sesion_mesa_id": orden["sesion_mesa_id"]})
    cuenta = caja.data("/cuenta/ajustar", {"cuenta_id": cuenta["id"], "propina": 1500})
    caja.data("/cuenta/pagar", {"cuenta_id": cuenta["id"], "clave_idempotencia": key(), "pagos": [
        {"medio_pago_id": medio(caja, "Efectivo"), "monto": cuenta["saldo"]}]})
    datos = caja.data("/entrega/list")
    entrega = next(e for e in datos["activas"] + datos["cerradas"] if e["orden_id"] == orden["id"])
    d01 = find(caja.data("/domicilio/domiciliario/list"), codigo="D01")
    caja.data("/entrega/asignar", {"entrega_id": entrega["id"], "domiciliario_id": d01["id"]})
    punto = find(sesion_cocina["puntos"], nombre="Cocina")["id"]
    tarjeta = find(cocina.data("/cocina/comandas", {"punto_produccion_id": punto})["en_proceso"], orden_id=orden["id"])
    cocina.data("/cocina/abrir", {"comanda_id": tarjeta["id"]})
    cocina.data("/cocina/despachar", {"comanda_id": tarjeta["id"]})
    domi.data("/entrega/salir", {"entrega_id": entrega["id"]})
    domi.data("/entrega/entregar", {"entrega_id": entrega["id"]})

    # Con efectivo por rendir no se aprueba
    previa = admin.data("/liquidacion/periodo", {"tipo": "domiciliarios"})
    linea = find(previa["lineas"], domiciliario_id=d01["id"])
    detalle = find(linea["detalle"]["entregas"], entrega_id=entrega["id"])
    assert detalle["pago"] == 1000 + round(zona["tarifa"] * 0.10)
    # Los faltantes de sus rendiciones se descuentan
    assert linea["propinas"] >= 1500 and linea["descuentos"] == sum(f["valor"] for f in linea["detalle"]["faltantes"])
    assert linea["total"] == linea["pago_entregas"] + linea["propinas"] - linea["descuentos"] + linea["ajustes"]
    borrador = admin.data("/liquidacion/calcular", {"tipo": "domiciliarios"})
    if any(l["detalle"].get("por_rendir") for l in borrador["lineas"]):
        assert "por rendir" in admin.post("/liquidacion/aprobar", {"liquidacion_id": borrador["id"]}).json()["message"]
        for grupo in caja.data("/entrega/por_rendir")["pendientes"]:
            caja.data("/entrega/rendir", {"domiciliario_id": grupo["domiciliario_id"], "entregado": grupo["esperado"]})
        borrador = admin.data("/liquidacion/calcular", {"tipo": "domiciliarios", "liquidacion_id": borrador["id"]})
    # El mesero no ve liquidaciones de domiciliarios
    mesero, _ = esquina["mesero.terraza"]
    assert mesero.post("/liquidacion/get", {"liquidacion_id": borrador["id"]}).status_code == 403

    aprobada = admin.data("/liquidacion/aprobar", {"liquidacion_id": borrador["id"]})
    assert aprobada["estado"] in ("aprobada", "pagada")
    # Las entregas liquidadas no se vuelven a liquidar (RN-PRP-06)
    siguiente = admin.data("/liquidacion/periodo", {"tipo": "domiciliarios",
                                                    "fecha": str(date.fromisoformat(borrador["hasta"]) + timedelta(days=1))})
    assert not any(e["entrega_id"] == entrega["id"] for l in siguiente["lineas"] for e in l["detalle"].get("entregas", []))
    propia = domi.data("/liquidacion/mias")["liquidaciones"]
    assert propia[0]["domiciliario_id"] == d01["id"] and propia[0]["liquidacion"]["tipo"] == "domiciliarios"
    # La propina del domicilio fue al domiciliario, no al pozo del equipo
    admin.data("/liquidacion/config/save", {"propina_domicilio": "pozo", "pago_domicilio": "zona"})
