"""
Proveedores y compras (docs 23 y 24): orden formal con recepción parcial, compra rápida pagada de caja,
anulación con movimientos contrarios, historial de precios, alertas de costo y lista sugerida.
"""
from conftest import find, ensure_shift


def insumo(api, nombre):
    return find(api.data("/insumo/list", {"todos": True}), nombre=nombre)


def proveedor(api, nombre):
    return find(api.data("/proveedor/list", {"todos": True}), nombre=nombre)


def nuevo_insumo(api, nombre, costo=None, stock=None, **extra):
    creado = api.data("/insumo/create", {"nombre": nombre, "unidad": "g", "categoria": "Pruebas", **extra}, expect=201)
    if stock:
        api.data("/inventario/entrada", {"insumo_id": creado["id"], "cantidad": stock, "costo_unitario": costo})
    return creado


def test_orden_de_compra_con_recepcion_parcial(esquina):
    admin, _ = esquina["admin.esquina"]
    andina = proveedor(admin, "Distribuidora Andina")
    # Insumo propio: las recetas demo que miden otras pruebas no cambian de costo
    nuevo_insumo(admin, "Carne de prueba compras", costo=28, stock=8000,
                 presentaciones=[{"nombre": "Paquete 1 kg", "factor": 1000}])
    carne = insumo(admin, "Carne de prueba compras")
    paquete = find(carne["presentaciones"], nombre="Paquete 1 kg")

    compra = admin.data("/compra/create", {"proveedor_id": andina["id"], "lineas": [
        {"insumo_id": carne["id"], "presentacion_id": paquete["id"], "cantidad": 4, "precio_unitario": 30000},
    ]}, expect=201)
    assert compra["estado"] == "borrador" and compra["total"] == 120000 and compra["forma_pago"] == "credito"
    compra = admin.data("/compra/solicitar", {"compra_id": compra["id"]})
    assert compra["estado"] == "solicitada" and "4 Paquete 1 kg de Carne de prueba compras" in compra["mensaje_proveedor"]

    # Llegan 3 de 4 paquetes: entran 3000 g a 30 $/g y el resto queda pendiente (RN-COM-02)
    linea = compra["lineas"][0]
    recibida = admin.data("/compra/recibir", {"compra_id": compra["id"], "notas": "Faltó un paquete", "lineas": [
        {"compra_linea_id": linea["id"], "cantidad": 3, "novedad": "Llegó un paquete menos"}]})
    assert recibida["estado"] == "parcial" and recibida["valor_recibido"] == 90000
    assert recibida["lineas"][0]["pendiente"] == 1 and recibida["recepciones"][0]["usuario"]
    despues = insumo(admin, "Carne de prueba compras")
    assert despues["stock"] == carne["stock"] + 3000
    esperado = (carne["stock"] * carne["costo_promedio"] + 3000 * 30) / (carne["stock"] + 3000)
    assert abs(despues["costo_promedio"] - esperado) < 0.001

    movimiento = admin.data("/inventario/movimientos", {"insumo_id": carne["id"], "tipo": "compra"})[0]
    assert movimiento["referencia"] == f"Compra {compra['numero']}" and movimiento["cantidad"] == 3000

    # Recibida no se edita (RN-COM-01) y el precio ya usado no cambia en otra recepción
    assert admin.post("/compra/update", {"compra_id": compra["id"], "lineas": [
        {"insumo_id": carne["id"], "cantidad": 1000, "precio_unitario": 28}]}).status_code == 409
    assert admin.post("/compra/recibir", {"compra_id": compra["id"], "lineas": [
        {"compra_linea_id": linea["id"], "cantidad": 1, "precio_unitario": 31000}]}).status_code == 400

    # Cerrar con faltante pide confirmación
    assert admin.post("/compra/cerrar", {"compra_id": compra["id"]}).status_code == 409
    cerrada = admin.data("/compra/cerrar", {"compra_id": compra["id"], "cerrar_con_pendiente": True,
                                            "factura_proveedor": "FV-2231"})
    assert cerrada["estado"] == "cerrada" and cerrada["factura_proveedor"] == "FV-2231"
    assert admin.post("/compra/recibir", {"compra_id": compra["id"], "lineas": [
        {"compra_linea_id": linea["id"], "cantidad": 1}]}).status_code == 409

    # El proveedor guarda el último precio y el histórico sale de las compras (RN-PRV-02)
    detalle = admin.data("/proveedor/get", {"proveedor_id": andina["id"]})
    relacion = find(detalle["insumos"], insumo_id=carne["id"])
    assert relacion["ultimo_precio"] == 30000 and relacion["ultimo_costo_unitario"] == 30 and relacion["preferido"]
    assert find(detalle["precios"], compra_id=compra["id"])["precio_unitario"] == 30000


def test_alerta_si_el_proveedor_sube_el_precio_y_encarece_platos(esquina):
    admin, _ = esquina["admin.esquina"]
    andina = proveedor(admin, "Distribuidora Andina")
    cacao = nuevo_insumo(admin, "Cacao de prueba", costo=10, stock=1000)
    categoria = admin.data("/categoria/list")[0]
    plato = admin.data("/producto/create", {"categoria_id": categoria["id"], "nombre": "Postre de prueba compras",
                                            "precio": 20000}, expect=201)
    admin.data("/receta/save", {"producto_id": plato["id"], "lineas": [{"insumo_id": cacao["id"], "cantidad": 100}]})

    def comprar(precio):
        return admin.data("/compra/rapida", {"proveedor_id": andina["id"], "forma_pago": "credito", "lineas": [
            {"insumo_id": cacao["id"], "cantidad": 1000, "precio_unitario": precio}]}, expect=201)

    primera = comprar(10)
    assert primera["estado"] == "cerrada" and primera["es_rapida"] and primera["alertas_precio"] == []
    # El proveedor triplica el precio: el promedio pasa de 10 a (2000×10 + 1000×30) / 3000 ≈ 16,7 $/g
    segunda = comprar(30)
    alerta = find(segunda["alertas_precio"], insumo="Cacao de prueba")
    assert alerta["antes"] == 10 and alerta["despues"] == 30 and alerta["variacion"] == 200.0
    plato_alerta = find(segunda["alertas_costo"], producto="Postre de prueba compras")
    assert plato_alerta["antes"] == 1000 and plato_alerta["despues"] > plato_alerta["antes"]


def test_compra_rapida_pagada_de_caja(esquina):
    admin, _ = esquina["admin.esquina"]
    caja = ensure_shift(admin)
    gastos = caja["turno"]["resumen"]["gastos"]
    efectivo = caja["turno"]["resumen"]["efectivo_esperado"]
    nuevo_insumo(admin, "Tomate de prueba compras", costo=5, stock=2000)
    tomate = insumo(admin, "Tomate de prueba compras")

    # Sin efectivo suficiente no se registra nada
    assert admin.post("/compra/rapida", {"proveedor_nombre": "Plaza de mercado", "forma_pago": "caja", "lineas": [
        {"insumo_id": tomate["id"], "cantidad": 1000, "total": efectivo + 1}]}).status_code == 400
    assert insumo(admin, "Tomate de prueba compras")["stock"] == tomate["stock"]

    compra = admin.data("/compra/rapida", {"proveedor_nombre": "Plaza de mercado", "forma_pago": "caja", "lineas": [
        {"insumo_id": tomate["id"], "cantidad": 3000, "total": 12000}]}, expect=201)
    assert compra["proveedor"] == "Plaza de mercado" and compra["recepciones"][0]["pagado_de_caja"]
    assert compra["lineas"][0]["precio_unitario"] == 4
    resumen = admin.data("/caja/estado")["turno"]["resumen"]
    assert resumen["gastos"] == gastos + 12000 and resumen["efectivo_esperado"] == efectivo - 12000
    assert insumo(admin, "Tomate de prueba compras")["stock"] == tomate["stock"] + 3000

    # Al anularla se puede devolver el dinero a la caja
    anulada = admin.data("/compra/anular", {"compra_id": compra["id"], "motivo": "Se registró dos veces",
                                            "reintegrar_caja": True})
    assert anulada["estado"] == "anulada"
    assert admin.data("/caja/estado")["turno"]["resumen"]["efectivo_esperado"] == efectivo
    assert insumo(admin, "Tomate de prueba compras")["stock"] == tomate["stock"]


def test_anular_revierte_entradas_y_costo_promedio(esquina):
    admin, _ = esquina["admin.esquina"]
    harina = nuevo_insumo(admin, "Harina para anular", costo=10, stock=1000)
    compra = admin.data("/compra/rapida", {"forma_pago": "contado", "lineas": [
        {"insumo_id": harina["id"], "cantidad": 1000, "precio_unitario": 20}]}, expect=201)
    assert compra["proveedor"] == "Compra de plaza"
    assert insumo(admin, "Harina para anular")["costo_promedio"] == 15

    assert admin.post("/compra/anular", {"compra_id": compra["id"]}).status_code == 422  # sin motivo
    anulada = admin.data("/compra/anular", {"compra_id": compra["id"], "motivo": "Mercancía devuelta"})
    assert anulada["estado"] == "anulada" and anulada["motivo_anulacion"] == "Mercancía devuelta"
    despues = insumo(admin, "Harina para anular")
    assert despues["stock"] == 1000 and despues["costo_promedio"] == 10  # RN-COM-05
    tipos = [m["tipo"] for m in admin.data("/inventario/movimientos", {"insumo_id": harina["id"]})[:2]]
    assert tipos == ["anulacion_compra", "compra"]
    assert admin.post("/compra/anular", {"compra_id": compra["id"], "motivo": "Otra vez"}).status_code == 409

    # Si ya se consumió, la anulación deja la existencia negativa y lo advierte
    otra = admin.data("/compra/rapida", {"forma_pago": "contado", "lineas": [
        {"insumo_id": harina["id"], "cantidad": 500, "precio_unitario": 10}]}, expect=201)
    admin.data("/inventario/merma", {"insumo_id": harina["id"], "cantidad": 1400, "motivo": "Se mojó"})
    respuesta = admin.post("/compra/anular", {"compra_id": otra["id"], "motivo": "Error de registro"}, expect=200).json()
    assert "Harina para anular" in respuesta["message"] and insumo(admin, "Harina para anular")["stock"] == -400


def test_validaciones_y_permisos(esquina, napoli):
    admin, _ = esquina["admin.esquina"]
    cocina, _ = esquina["cocina.esquina"]
    mesero, _ = esquina["mesero.salon"]
    papa = insumo(admin, "Papa")
    salsa = insumo(admin, "Salsa de la casa")

    assert admin.post("/compra/create", {"lineas": [{"insumo_id": salsa["id"], "cantidad": 1}]}).status_code == 400
    assert admin.post("/compra/create", {"fecha": "2999-01-01", "lineas": [
        {"insumo_id": papa["id"], "cantidad": 1}]}).status_code == 400
    assert admin.post("/compra/create", {"proveedor_id": 1}).status_code == 422
    assert admin.post("/compra/create", {"lineas": [{"insumo_id": papa["id"], "cantidad": 1},
                                                    {"insumo_id": papa["id"], "cantidad": 2}]}).status_code == 400

    # La compra demo de La Cosecha está pendiente: cocina la ve y la recibe, pero no crea ni anula
    pendiente = find(cocina.data("/compra/list", {"estado": "pendientes"}), proveedor="Fruver La Cosecha")
    detalle = cocina.data("/compra/get", {"compra_id": pendiente["id"]})
    assert cocina.post("/compra/rapida", {"lineas": [{"insumo_id": papa["id"], "cantidad": 1}]}).status_code == 403
    assert cocina.post("/compra/anular", {"compra_id": pendiente["id"], "motivo": "No"}).status_code == 403
    assert mesero.post("/compra/list").status_code == 403
    papa_linea = find(detalle["lineas"], insumo="Papa")
    recibida = cocina.data("/compra/recibir", {"compra_id": pendiente["id"], "lineas": [
        {"compra_linea_id": papa_linea["id"], "cantidad": 1}]})
    assert recibida["estado"] == "parcial" and insumo(admin, "Papa")["stock"] == papa["stock"] + 25000

    # Otra empresa no ve las compras de La Esquina
    otro, _ = napoli["napoli"]
    assert otro.post("/compra/get", {"compra_id": pendiente["id"]}).status_code in (403, 404)


def test_proveedores_y_lista_sugerida(esquina):
    admin, _ = esquina["admin.esquina"]
    creado = admin.data("/proveedor/create", {"nombre": "Lácteos El Prado", "tipo_documento": "NIT", "documento": "800111222-3",
                                              "forma_pago": "credito", "plazo_dias": 8, "whatsapp": "3001112233"}, expect=201)
    assert admin.post("/proveedor/create", {"nombre": "lácteos el prado"}).status_code == 400
    assert admin.post("/proveedor/create", {"nombre": "Sin tipo", "documento": "123456"}).status_code == 400

    leche = nuevo_insumo(admin, "Leche de prueba", costo=4, stock=500, stock_minimo=2000,
                         presentaciones=[{"nombre": "Bolsa 1 l", "factor": 1000}])
    bolsa = leche["presentaciones"][0]["id"]
    admin.data("/proveedor/insumos", {"proveedor_id": creado["id"], "insumos": [
        {"insumo_id": leche["id"], "presentacion_id": bolsa, "preferido": True}]})

    # Faltan 3500 ml para llegar al doble del mínimo: 4 bolsas de 1 l con Lácteos El Prado
    grupo = find(admin.data("/compra/sugerida"), proveedor="Lácteos El Prado")
    item = find(grupo["items"], insumo="Leche de prueba")
    assert item["cantidad"] == 4 and item["presentacion"] == "Bolsa 1 l" and item["precio_estimado"] == 4000

    # Lo que ya viene en camino no se vuelve a sugerir
    admin.data("/compra/create", {"proveedor_id": creado["id"], "solicitar": True, "lineas": [
        {"insumo_id": leche["id"], "presentacion_id": bolsa, "cantidad": 4, "precio_unitario": 4200}]}, expect=201)
    sugeridas = admin.data("/compra/sugerida")
    assert not any(i["insumo"] == "Leche de prueba" for g in sugeridas for i in g["items"])

    # Inactivar no borra: sigue en la lista con todos
    admin.data("/proveedor/change_status", {"proveedor_id": creado["id"], "activo": False})
    assert proveedor(admin, "Lácteos El Prado")["activo"] is False
    assert admin.post("/compra/create", {"proveedor_id": creado["id"], "lineas": [
        {"insumo_id": leche["id"], "cantidad": 1}]}).status_code == 400
