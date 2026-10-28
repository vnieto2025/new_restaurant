"""
Inventario y recetas (docs 14 y 22, ADR-013): descuento al entrar a producción, merma al cancelar después,
costo promedio ponderado, costo y margen por plato, preparaciones, conteos y alertas.
"""
from conftest import key, find, product_id, option_id, table


def stock(api, nombre):
    return find(api.data("/insumo/list", {"todos": True}), nombre=nombre)


def pedir(caja, admin, nombre, opciones=()):
    externa = table(caja, "Para llevar", incluir_externa=True)
    item = {"producto_id": product_id(admin, nombre), "cantidad": 1,
            "modificadores": [option_id(admin, grupo, opcion) for grupo, opcion in opciones]}
    return caja.data("/orden/create", {"mesa_id": externa["id"], "clave_idempotencia": key(), "cliente_nombre": "Inventario",
                                       "items": [item]}, expect=201)


def abrir_en_cocina(cocina, sesion, orden, punto="Cocina"):
    punto_id = find(sesion["puntos"], nombre=punto)["id"]
    tarjeta = find(cocina.data("/cocina/comandas", {"punto_produccion_id": punto_id})["en_proceso"], orden_id=orden["id"])
    cocina.data("/cocina/abrir", {"comanda_id": tarjeta["id"]})


def test_descuenta_receta_y_modificadores_al_entrar_a_produccion(esquina):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    cocina, sesion = esquina["cocina.esquina"]
    antes = {n: stock(admin, n)["stock"] for n in ("Carne de res molida", "Queso mozzarella", "Tomate", "Pan de hamburguesa")}

    orden = pedir(caja, admin, "Hamburguesa clásica", [("Término de la carne", "Medio"), ("Adicionales", "Queso extra"),
                                                        ("Quitar ingredientes", "Sin tomate")])
    # Pedir no descuenta: el ítem aún puede cancelarse sin costo (ADR-013)
    assert stock(admin, "Carne de res molida")["stock"] == antes["Carne de res molida"]

    abrir_en_cocina(cocina, sesion, orden)
    assert stock(admin, "Carne de res molida")["stock"] == antes["Carne de res molida"] - 157.5  # 150 g + 5 % de merma
    assert stock(admin, "Queso mozzarella")["stock"] == antes["Queso mozzarella"] - 60  # receta + queso extra
    assert stock(admin, "Tomate")["stock"] == antes["Tomate"] - 3  # 33 g de receta − 30 g "sin tomate"
    assert stock(admin, "Pan de hamburguesa")["stock"] == antes["Pan de hamburguesa"] - 1

    carne = stock(admin, "Carne de res molida")
    ultimo = admin.data("/inventario/movimientos", {"insumo_id": carne["id"]})[0]
    assert ultimo["tipo"] == "consumo" and ultimo["motivo"].endswith("1 × Hamburguesa clásica")


def test_cancelar_en_produccion_queda_como_merma(esquina):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    cocina, sesion = esquina["cocina.esquina"]
    papa = stock(admin, "Papa")

    # Cancelado antes de empezar: no mueve inventario
    orden = pedir(caja, admin, "Papas a la francesa")
    caja.data("/orden/cancelar_item", {"orden_item_id": orden["items"][0]["id"], "motivo": "El cliente cambió de idea"})
    assert stock(admin, "Papa")["stock"] == papa["stock"]

    orden = pedir(caja, admin, "Papas a la francesa")
    abrir_en_cocina(cocina, sesion, orden)
    admin.data("/orden/cancelar_item", {"orden_item_id": orden["items"][0]["id"], "motivo": "Se quemaron"})
    assert stock(admin, "Papa")["stock"] == papa["stock"] - 287.5
    tipos = [m["tipo"] for m in admin.data("/inventario/movimientos", {"insumo_id": papa["id"]})[:3]]
    assert tipos == ["merma", "reverso_consumo", "consumo"]
    merma = admin.data("/inventario/movimientos", {"insumo_id": papa["id"], "tipo": "merma"})[0]
    assert "Se quemaron" in merma["motivo"] and merma["cantidad"] == -287.5


def test_costo_promedio_ponderado_y_stock_por_movimientos(esquina):
    admin, _ = esquina["admin.esquina"]
    insumo = admin.data("/insumo/create", {"nombre": "Harina de prueba", "unidad": "g", "categoria": "Abarrotes",
                                           "presentaciones": [{"nombre": "Bulto 10 kg", "factor": 10000}]}, expect=201)
    bulto = insumo["presentaciones"][0]["id"]
    admin.data("/inventario/entrada", {"insumo_id": insumo["id"], "cantidad": 1, "presentacion_id": bulto, "costo_total": 30000})
    despues = admin.data("/inventario/entrada", {"insumo_id": insumo["id"], "cantidad": 10000, "costo_unitario": 5})
    assert despues["stock"] == 20000 and despues["costo_promedio"] == 4.0  # (10000×3 + 10000×5) / 20000

    assert admin.post("/inventario/merma", {"insumo_id": insumo["id"], "cantidad": 500}).status_code == 422  # sin motivo
    admin.data("/inventario/merma", {"insumo_id": insumo["id"], "cantidad": 500, "motivo": "Se mojó"})
    ajustado = admin.data("/inventario/ajuste", {"insumo_id": insumo["id"], "existencia_real": 19000, "motivo": "Conteo rápido"})
    assert ajustado["stock"] == 19000 and ajustado["costo_promedio"] == 4.0

    movimientos = admin.data("/inventario/movimientos", {"insumo_id": insumo["id"]})
    assert sum(m["cantidad"] for m in movimientos) == ajustado["stock"]  # RN-INV-01
    assert [m["tipo"] for m in movimientos] == ["ajuste", "merma", "entrada", "entrada"]
    # Con movimientos no se cambia la unidad (RN-INV-03)
    assert admin.post("/insumo/update", {**insumo, "insumo_id": insumo["id"], "unidad": "ml"}).status_code == 400


def test_costo_y_margen_por_plato(esquina):
    admin, _ = esquina["admin.esquina"]
    receta = admin.data("/receta/get", {"producto_id": product_id(admin, "Hamburguesa clásica")})
    # Pan 900 + carne 157,5 g × 28 + queso 900 + lechuga 22 g × 6 + tomate 33 g × 5 + salsa 20 g × 13,7
    assert receta["costo"] == 900 + 4410 + 900 + 132 + 165 + 274
    assert receta["precio_sin_impuesto"] == 16667 and receta["margen"] == 16667 - receta["costo"]

    costos = admin.data("/receta/costos", {"margen_minimo": 60})
    jugo = find(costos["productos"], nombre="Jugo de mango")
    assert jugo["tiene_receta"] is False and jugo["costo"] is None
    clasica = find(costos["productos"], nombre="Hamburguesa clásica")
    assert clasica["bajo_meta"] is True  # 59,3 % < 60 %
    assert costos["sin_receta"] >= 1


def test_preparacion_sin_ciclos_y_produccion(esquina):
    admin, _ = esquina["admin.esquina"]
    cocina, _ = esquina["cocina.esquina"]
    salsa = stock(admin, "Salsa de la casa")
    mayonesa = stock(admin, "Mayonesa")
    respuesta = admin.post("/receta/save", {"insumo_id": salsa["id"], "rendimiento": 1000, "lineas": [
        {"insumo_id": mayonesa["id"], "cantidad": 950}, {"insumo_id": salsa["id"], "cantidad": 10}]})
    assert respuesta.status_code == 400 and "a sí misma" in respuesta.json()["message"]

    # La cocina registra lo que prepara: baja la mayonesa y sube la salsa
    cocina.data("/inventario/producir", {"insumo_id": salsa["id"], "cantidad": 500})
    assert stock(admin, "Salsa de la casa")["stock"] == salsa["stock"] + 500
    assert stock(admin, "Mayonesa")["stock"] == mayonesa["stock"] - 475
    # Un producto que no es preparación no tiene receta de preparación
    assert admin.post("/receta/get", {"insumo_id": mayonesa["id"]}).status_code == 400


def test_conteo_genera_ajustes_solo_de_lo_contado(esquina):
    admin, _ = esquina["admin.esquina"]
    cocina, _ = esquina["cocina.esquina"]
    mesero, _ = esquina["mesero.salon"]
    assert mesero.post("/conteo/create", {"categoria": "Verduras"}).status_code == 403

    conteo = cocina.data("/conteo/create", {"categoria": "Verduras"}, expect=201)
    limon = find(conteo["lineas"], insumo="Limón")
    cocina.data("/conteo/save", {"conteo_id": conteo["id"], "lineas": [
        {"linea_id": limon["linea_id"], "contado": limon["teorico"] - 3, "nota": "Dos estaban dañados"}]})
    # Aplicar ajusta el inventario: lo decide el administrador
    assert cocina.post("/conteo/aplicar", {"conteo_id": conteo["id"]}).status_code == 403
    aplicado = admin.data("/conteo/aplicar", {"conteo_id": conteo["id"]})
    assert aplicado["estado"] == "aplicado" and aplicado["total"] == 1 and aplicado["con_diferencia"] == 1
    ajuste = admin.data("/inventario/movimientos", {"insumo_id": limon["insumo_id"], "tipo": "ajuste"})[0]
    assert ajuste["cantidad"] == -3 and "Dos estaban dañados" in ajuste["motivo"]
    assert admin.post("/conteo/save", {"conteo_id": conteo["id"], "lineas": [
        {"linea_id": limon["linea_id"], "contado": 1}]}).status_code == 409


def test_alerta_de_stock_negativo_sin_frenar_la_venta(esquina):
    admin, _ = esquina["admin.esquina"]
    insumo = admin.data("/insumo/create", {"nombre": "Servilletas de prueba", "unidad": "und", "stock_minimo": 10}, expect=201)
    admin.data("/inventario/entrada", {"insumo_id": insumo["id"], "cantidad": 5, "costo_unitario": 20})
    estado = admin.data("/inventario/estado")
    assert any(i["id"] == insumo["id"] for i in estado["bajos"])
    admin.data("/inventario/merma", {"insumo_id": insumo["id"], "cantidad": 8, "motivo": "Se mojaron"})  # RN-INV-05
    estado = admin.data("/inventario/estado")
    assert any(i["id"] == insumo["id"] and i["stock"] == -3 for i in estado["negativos"])


def test_modulo_inventario_no_contratado(napoli):
    admin, _ = napoli["napoli"]
    assert admin.post("/insumo/list").json()["detail"]["codigo"] == "modulo_no_contratado"
