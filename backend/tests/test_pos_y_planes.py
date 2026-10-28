"""
POS de mostrador sin el módulo de pedidos (doc 20 sección 9, ADR-007) y planes comerciales con el cobro manual del
servicio (doc 42): paquetes deducidos de los módulos, dependencias validadas, vencimiento y mora.
"""
from datetime import date, timedelta
from types import SimpleNamespace
from conftest import key, find, product_id, ensure_shift, medio, login
from Utils.catalogo import plan_de
from Class.Suscripcion import estado_cuenta, sumar_meses


def test_planes_y_estado_de_cuenta():
    assert plan_de(["base", "pedidos"]) == "pedidos"
    assert plan_de(["base", "pedidos", "domicilios"]) == "pedidos"
    assert plan_de(["base", "caja", "inventario"]) == "gestion"
    assert plan_de(["base", "caja", "inventario", "facturacion", "fidelizacion"]) == "gestion"
    assert plan_de(["base", "pedidos", "caja", "inventario", "facturacion", "propinas", "pagos_linea"]) == "completo"
    assert plan_de(["base", "caja"]) == "personalizado"

    assert sumar_meses(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert sumar_meses(date(2026, 11, 15), 3) == date(2027, 2, 15)
    hoy = date(2026, 10, 27)
    contrato = lambda **c: SimpleNamespace(**{"estado": "activo", "fecha_fin": None, "proximo_vencimiento": None, **c})  # noqa: E731
    assert estado_cuenta(contrato(), hoy)["estado"] == "sin_cobro"
    assert estado_cuenta(contrato(proximo_vencimiento=hoy + timedelta(days=20)), hoy)["estado"] == "al_dia"
    assert estado_cuenta(contrato(proximo_vencimiento=hoy + timedelta(days=3)), hoy)["texto"] == "Vence en 3 días"
    mora = estado_cuenta(contrato(proximo_vencimiento=hoy - timedelta(days=4)), hoy)
    assert mora["estado"] == "en_mora" and not mora["suspender_sugerido"]
    # Pasado el periodo de gracia se sugiere suspender; nunca se suspende solo
    assert estado_cuenta(contrato(proximo_vencimiento=hoy - timedelta(days=15)), hoy)["suspender_sugerido"]
    assert estado_cuenta(contrato(estado="prueba", fecha_fin=hoy + timedelta(days=5)), hoy)["texto"] == "En prueba: quedan 5 días"


def test_venta_directa_sin_modulo_de_pedidos(client):
    caja, sesion = login(client, "caja.trigo")
    admin, _ = login(client, "trigo")
    # Caja sigue las cuentas en vivo aunque no haya pedidos; las zonas y la cocina no existen para ella
    from Router.Realtime import allowed_channels
    ctx = {"modulos": {"base", "caja", "inventario"}, "permisos": {"caja.cobrar"}, "zonas": None,
           "restaurante_id": sesion["restaurante"]["id"]}
    assert allowed_channels(ctx, ["ordenes", "zona:1", "punto:1"]) == [f"r{sesion['restaurante']['id']}:ordenes"]
    # Sin pedidos: no hay órdenes de mesa ni mostrador, pero caja vende directo
    assert caja.post("/orden/create", {"mesa_id": 1, "clave_idempotencia": key(), "items": []}).status_code == 403
    carta = caja.data("/pos/carta")
    productos = {p["nombre"]: p["id"] for c in carta["categorias"] for p in c["productos"]}
    venta = {"clave_idempotencia": key(), "items": [{"producto_id": productos["Pan de bono"], "cantidad": 4},
                                                     {"producto_id": productos["Café con leche"], "cantidad": 1}]}
    # Sin turno no se vende
    if not caja.data("/caja/estado")["turno"]:
        assert "turno" in caja.post("/pos/vender", venta).json()["message"]
    ensure_shift(caja)
    cuenta = caja.data("/pos/vender", venta, expect=201)
    assert cuenta["venta_directa"] and cuenta["subtotal"] == 4 * 2500 + 3500 and cuenta["items_pendientes"] == 0
    # Un doble toque no crea otra venta
    assert caja.data("/pos/vender", venta)["id"] == cuenta["id"]
    pendiente = find(caja.data("/cuenta/pendientes"), cuenta_id=cuenta["id"])
    assert pendiente["venta_directa"]

    pagada = caja.data("/cuenta/pagar", {"cuenta_id": cuenta["id"], "clave_idempotencia": key(), "pagos": [
        {"medio_pago_id": medio(caja, "Efectivo"), "monto": cuenta["saldo"], "recibido": 20000}]})
    assert pagada["estado"] == "pagada" and pagada["numero_texto"]
    assert caja.post("/pos/cancelar", {"cuenta_id": cuenta["id"]}).status_code == 409
    reporte = admin.data("/reporte/ventas", {})
    assert reporte["totales"]["ventas"] >= cuenta["subtotal"]

    # Una venta que no se cobra se cancela y no queda por cobrar
    otra = caja.data("/pos/vender", {"clave_idempotencia": key(), "cliente_nombre": "Señora del 302",
                                     "items": [{"producto_id": productos["Croissant"], "cantidad": 2}]}, expect=201)
    assert otra["cliente_nombre"] == "Señora del 302"
    caja.data("/pos/cancelar", {"cuenta_id": otra["id"], "motivo": "El cliente se arrepintió"})
    assert not any(p["cuenta_id"] == otra["id"] for p in caja.data("/cuenta/pendientes"))
    # Mi plan: Gestión, en mora en la demo, sin complementos que dependan de pedidos
    plan = admin.data("/restaurante/plan")
    assert plan["plan"] == "gestion" and plan["cuenta"]["estado"] == "en_mora"
    disponibles = [c["codigo"] for c in plan["complementos_disponibles"]]
    assert "facturacion" in disponibles and "domicilios" not in disponibles


def test_venta_directa_descuenta_inventario_y_lo_devuelve_al_cancelar(esquina):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    ensure_shift(caja)
    papa = lambda: find(admin.data("/insumo/list"), nombre="Papa")  # noqa: E731
    antes = float(papa()["stock"])
    venta = caja.data("/pos/vender", {"clave_idempotencia": key(), "items": [
        {"producto_id": product_id(admin, "Papas a la francesa"), "cantidad": 2}]}, expect=201)
    assert float(papa()["stock"]) == antes - 575  # receta: 250 g por porción más 15 % de merma
    caja.data("/pos/cancelar", {"cuenta_id": venta["id"]})
    assert float(papa()["stock"]) == antes
    # El producto nunca salió: no queda merma
    movimientos = admin.data("/inventario/movimientos", {"insumo_id": papa()["id"]})
    filas = movimientos["movimientos"] if isinstance(movimientos, dict) else movimientos
    assert not any(m["tipo"] == "merma" and "Venta directa" in (m.get("motivo") or "") for m in filas)


def test_planes_contrato_y_pagos_del_servicio(client):
    soporte, _ = login(client, "soporte", "Soporte12345")
    planes = soporte.data("/plataforma/plan/list")
    assert [p["codigo"] for p in planes["planes"]] == ["pedidos", "gestion", "completo"]
    assert {c["codigo"] for c in planes["complementos"]} == {"facturacion", "domicilios", "pagos_linea", "fidelizacion"}

    empresa = find(soporte.data("/plataforma/empresa/list"), nombre_comercial="Panadería Dulce Trigo")
    restaurante = empresa["restaurantes"][0]
    assert restaurante["suscripcion"]["plan"] == "gestion" and restaurante["suscripcion"]["cuenta"]["estado"] == "en_mora"
    # Las dependencias se validan: domicilios necesita pedidos
    respuesta = soporte.post("/plataforma/contrato/update", {"restaurante_id": restaurante["id"], "estado": "activo",
                                                             "modulos": ["caja", "inventario", "domicilios"]})
    assert respuesta.status_code == 400 and "requiere" in respuesta.json()["message"]
    # Con fidelización sigue siendo Gestión (complemento)
    actualizado = soporte.data("/plataforma/contrato/update", {
        "restaurante_id": restaurante["id"], "estado": "activo", "modulos": ["caja", "inventario", "fidelizacion"],
        "mensualidad": 140000, "notas_comerciales": "Precio de lanzamiento del piloto"})
    assert actualizado["contrato"]["modulos"] == ["base", "caja", "inventario", "fidelizacion"]

    vencia = date.fromisoformat(restaurante["contrato"]["proximo_vencimiento"])
    pago = soporte.data("/plataforma/suscripcion/pagar", {"restaurante_id": restaurante["id"], "valor": 280000, "meses": 2,
                                                          "medio": "transferencia", "referencia": "BANCO-881",
                                                          "factura": "FS-0012"}, expect=201)
    assert pago["suscripcion"]["proximo_vencimiento"] == str(sumar_meses(vencia, 2))
    assert pago["suscripcion"]["cuenta"]["estado"] == "al_dia" and pago["pagos"][0]["factura"] == "FS-0012"
    assert soporte.post("/plataforma/suscripcion/pagar", {"restaurante_id": restaurante["id"], "valor": 1000, "meses": 13,
                                                           "medio": "efectivo"}).status_code == 400
    # El restaurante ve su plan y sus pagos, pero no registra pagos
    admin, _ = login(client, "trigo")
    plan = admin.data("/restaurante/plan")
    assert plan["mensualidad"] == 140000 and plan["pagos"][0]["referencia"] == "BANCO-881"
    assert admin.post("/plataforma/suscripcion/pagar", {"restaurante_id": restaurante["id"], "valor": 1,
                                                        "medio": "efectivo"}).status_code == 403
    soporte.data("/plataforma/contrato/update", {"restaurante_id": restaurante["id"], "estado": "activo",
                                                 "modulos": ["caja", "inventario"]})
