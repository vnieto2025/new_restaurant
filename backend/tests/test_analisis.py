"""
Reportes de la fase 2 (doc 26, sección 5): horas pico que cuadran con el total, tiempos de cocina, domiciliarios,
clientes, inventario y comparativo entre sedes, con permisos y módulos.
"""
from datetime import date, timedelta
from conftest import find, key, login, product_id, table, pay_table
from Class.Analisis import resumen_tiempos

MANANA = date.today() + timedelta(days=1)
PERIODO = {"desde": str(date.today() - timedelta(days=2)), "hasta": str(MANANA)}


def test_resumen_de_tiempos():
    assert resumen_tiempos([10]) == {"cantidad": 1, "promedio": 10.0, "p90": 10}
    resumen = resumen_tiempos([1] * 9 + [100])
    assert resumen["cantidad"] == 10 and resumen["promedio"] == 10.9 and resumen["p90"] == 100


def test_horas_pico_cuadran_con_el_reporte_de_ventas(esquina):
    admin, _ = esquina["admin.esquina"]
    caja, _ = esquina["caja.esquina"]
    mesero, _ = esquina["mesero.salon"]
    mesa = table(mesero, "Mesa 3")
    mesero.data("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(),
                                  "items": [{"producto_id": product_id(admin, "Gaseosa 400 ml"), "cantidad": 3}]}, expect=201)
    pay_table(caja, mesa_id=mesa["id"])

    analisis = admin.data("/reporte/analisis", PERIODO)
    ventas = admin.data("/reporte/ventas", PERIODO)
    celdas = analisis["horas"]["celdas"]
    assert celdas and all(0 <= c["dia"] <= 6 and 0 <= c["hora"] <= 23 for c in celdas)
    assert sum(c["ventas"] for c in celdas) == ventas["totales"]["ventas"]
    assert sum(c["cuentas"] for c in celdas) == ventas["totales"]["cuentas"]
    assert analisis["horas"]["maximo"] == max(c["ventas"] for c in celdas)


def test_tiempos_de_cocina_por_punto(esquina):
    admin, _ = esquina["admin.esquina"]
    cocina, sesion = esquina["cocina.esquina"]
    caja, _ = esquina["caja.esquina"]
    mesero, _ = esquina["mesero.salon"]
    mesa = table(mesero, "Mesa 3")
    orden = mesero.data("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(),
                                          "items": [{"producto_id": product_id(admin, "Papas a la francesa"), "cantidad": 1}]}, expect=201)
    punto = find(sesion["puntos"], nombre="Cocina")["id"]
    tarjeta = find(cocina.data("/cocina/comandas", {"punto_produccion_id": punto})["en_proceso"], orden_id=orden["id"])
    cocina.data("/cocina/abrir", {"comanda_id": tarjeta["id"]})
    cocina.data("/cocina/despachar", {"comanda_id": tarjeta["id"]})
    fila = find(admin.data("/reporte/analisis", PERIODO)["tiempos"], nombre="Cocina")
    assert fila["cantidad"] >= 1 and fila["promedio"] >= 0 and fila["p90"] >= 0
    # La mesa queda libre para las demás pruebas
    mesero.data("/orden/entregar", {"orden_id": orden["id"]})
    pay_table(caja, mesa_id=mesa["id"])


def test_clientes_y_nombres_segun_permiso(client, esquina):
    admin, _ = esquina["admin.esquina"]
    caja, _ = esquina["caja.esquina"]
    externa = table(caja, "Para llevar", incluir_externa=True)
    for _ in range(2):
        caja.data("/orden/create", {"mesa_id": externa["id"], "clave_idempotencia": key(), "cliente_nombre": "Frecuente Análisis",
                                    "cliente_telefono": "3187770011", "acepta_datos": True,
                                    "items": [{"producto_id": product_id(admin, "Limonada natural"), "cantidad": 1}]}, expect=201)
    clientes = admin.data("/reporte/analisis", PERIODO)["clientes"]
    assert clientes["nuevos"] >= 1 and clientes["con_nombres"]
    assert find(clientes["frecuentes"], nombre="Frecuente Análisis")["ordenes"] >= 2

    # El contador ve las cantidades, no los nombres (doc 29)
    contador, _ = login(client, "contador.esquina")
    sin_nombres = contador.data("/reporte/analisis", PERIODO)["clientes"]
    assert sin_nombres["frecuentes_cantidad"] >= 1 and sin_nombres["frecuentes"] == [] and not sin_nombres["con_nombres"]


def test_secciones_segun_modulos_y_validaciones(client, esquina, napoli):
    admin, _ = esquina["admin.esquina"]
    completo = admin.data("/reporte/analisis", PERIODO)
    assert {"tiempos", "domiciliarios", "inventario", "horas", "clientes"} <= set(completo)
    assert isinstance(completo["inventario"]["criticos"], list) and isinstance(completo["domiciliarios"], list)

    pizzeria, _ = napoli["napoli"]
    solo_pedidos = pizzeria.data("/reporte/analisis", PERIODO)
    assert "tiempos" in solo_pedidos and "inventario" not in solo_pedidos and "domiciliarios" not in solo_pedidos

    assert admin.post("/reporte/analisis", {"desde": "2020-02-01", "hasta": "2020-01-01"}).status_code == 400
    caja, _ = esquina["caja.esquina"]
    assert caja.post("/reporte/analisis", PERIODO).status_code == 403


def test_comparativo_solo_para_el_dueno_y_sus_sedes(client, esquina, napoli):
    admin, _ = esquina["admin.esquina"]
    assert admin.post("/reporte/sedes", PERIODO).status_code == 403

    soporte, _ = login(client, "soporte", "Soporte12345")
    empresa = soporte.data("/plataforma/empresa/create", {
        "nombre_comercial": "Cadena Dos Sedes", "modulos": ["pedidos"], "estado_contrato": "activo",
        "admin": {"usuario": "dueno.cadena", "nombre": "Dueño", "password": "clave12345"},
        "restaurante": {"nombre": "Sede Norte"}}, expect=201)
    soporte.data("/plataforma/restaurante/create", {"empresa_id": empresa["id"], "nombre": "Sede Sur", "modulos": ["pedidos"],
                                                    "estado_contrato": "activo", "restaurante": {"nombre": "Sede Sur"}}, expect=201)
    dueno, _ = login(client, "dueno.cadena", "clave12345")
    comparativo = dueno.data("/reporte/sedes", PERIODO)
    assert {r["nombre"] for r in comparativo["restaurantes"]} == {"Sede Norte", "Sede Sur"}
    # Otra empresa no aparece
    assert "Napoli Norte" not in {r["nombre"] for r in comparativo["restaurantes"]}
