"""
Restaurante de práctica (doc 33, sección 7; ADR-053): copia de la configuración, operación aparte que no toca
ventas, caja, inventario ni clientes del real, sin facturación electrónica ni pagos en línea, y reinicio.
"""
from conftest import login, key, find, table, pay_table


def entrar(client, usuario, restaurante_id, password="demo1234"):
    api, _ = login(client, usuario, password)
    sesion = api.data("/auth/cambiar_restaurante", {"restaurante_id": restaurante_id})
    api.token = sesion["token"]
    return api, sesion


def test_practica_aparte_del_real(client, esquina):
    admin, sesion_real = esquina["admin.esquina"]
    real_id = sesion_real["restaurante"]["id"]
    assert admin.data("/practica/estado")["practica"] is None
    mesero, _ = esquina["mesero.salon"]
    assert mesero.post("/practica/crear").status_code == 403

    estado = admin.data("/practica/crear", expect=201)
    practica_id = estado["practica"]["id"]
    assert estado["practica"]["nombre"] == "La Esquina Centro · Práctica"
    assert admin.post("/practica/crear").status_code == 409

    ventas_antes = admin.data("/reporte/ventas")["totales"]["ventas"]
    papa_real = find(admin.data("/insumo/list"), nombre="Papa")["stock"]

    # El mesero entra a la práctica: mismas zonas, misma carta, sin facturación ni pagos en línea
    practica, sesion = entrar(client, "mesero.salon", practica_id)
    assert sesion["restaurante"]["practica"] is True and sesion["practica"]["real"]["id"] == real_id
    assert [z["nombre"] for z in sesion["zonas"]] == ["Salón"]
    assert "facturacion" not in sesion["modulos"] and "pagos_linea" not in sesion["modulos"]
    caja, sesion_caja = entrar(client, "caja.esquina", practica_id)
    externa = table(caja, "Para llevar", incluir_externa=True)
    papas = find(caja.data("/producto/list"), nombre="Papas a la francesa")
    caja.data("/orden/create", {"mesa_id": externa["id"], "clave_idempotencia": key(), "cliente_nombre": "Práctica",
                                "items": [{"producto_id": papas["id"], "cantidad": 2}]}, expect=201)
    pay_table(caja, sesion_mesa_id=caja.data("/cuenta/pendientes")[0]["sesion_mesa_id"])
    admin_practica, _ = entrar(client, "admin.esquina", practica_id)
    assert admin_practica.data("/reporte/ventas")["totales"]["ventas"] == 14000
    # El inventario de práctica arrancó con las existencias del real
    assert find(admin_practica.data("/insumo/list"), nombre="Papa")["stock"] == papa_real

    # Un cliente con el mismo celular que uno real no choca, y cada uno se ve solo en su restaurante
    caja_real, _ = esquina["caja.esquina"]
    caja_real.data("/cliente/create", {"nombre": "Cliente real", "telefono": "3001112233", "acepta_datos": True}, expect=201)
    caja.data("/cliente/create", {"nombre": "Cliente de práctica", "telefono": "3001112233", "acepta_datos": True}, expect=201)
    assert [c["nombre"] for c in caja_real.data("/cliente/buscar", {"texto": "3001112233"})] == ["Cliente real"]
    assert [c["nombre"] for c in caja.data("/cliente/buscar", {"texto": "3001112233"})] == ["Cliente de práctica"]

    # Nada de eso llegó al real
    assert admin.data("/reporte/ventas")["totales"]["ventas"] == ventas_antes
    assert all(r["id"] != practica_id for r in admin.data("/auth/sesion")["restaurantes"])
    assert admin_practica.post("/producto/imagen/quitar", {"producto_id": papas["id"]}).status_code == 409

    # Reiniciar deja la práctica como el real, sin órdenes ni clientes de práctica
    estado = admin_practica.data("/practica/reiniciar")
    assert estado["practica"]["ordenes"] == 0 and estado["practica"]["id"] == practica_id
    assert admin_practica.data("/reporte/ventas")["totales"]["ventas"] == 0
    assert caja.data("/cliente/buscar", {"texto": "3001112233"}) == []
    assert [c["nombre"] for c in caja_real.data("/cliente/buscar", {"texto": "3001112233"})] == ["Cliente real"]
    assert find(admin_practica.data("/producto/list"), nombre="Papas a la francesa")
