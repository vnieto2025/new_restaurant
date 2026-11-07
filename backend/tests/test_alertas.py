"""
Alertas del dueño y resumen del día (docs 27, 26 y 31B; ADR-052): umbrales configurables, silenciar por la
jornada, resumen con ventas, pagos, cancelaciones y caja, y aviso por WhatsApp al cerrar la jornada.
"""
from datetime import timedelta
from sqlalchemy import text
from conftest import Api, login, key, find, table, pay_table
from Config.db import admin_engine


def alerta(api, codigo):
    return next((a for a in api.data("/alerta/list") if a["codigo"] == codigo), None)


def configurar(api, **umbrales):
    filas = api.data("/alerta/config/get")
    api.data("/alerta/config/save", {"alertas": [{**f, "umbral": umbrales.get(f["codigo"], f["umbral_sugerido"])} for f in filas]})


def test_alertas_con_umbral_y_silencio(esquina):
    admin, _ = esquina["admin.esquina"]
    caja, _ = esquina["caja.esquina"]
    mesero, _ = esquina["mesero.salon"]

    # La tocineta de la semilla está bajo su mínimo
    inventario = alerta(admin, "inventario")
    assert any(d.startswith("Tocineta") for d in inventario["detalle"]) and not inventario["silenciada"]

    # Silenciar vale para la jornada; se puede deshacer
    admin.data("/alerta/silenciar", {"codigo": "inventario"})
    assert alerta(admin, "inventario")["silenciada"] is True
    admin.data("/alerta/silenciar", {"codigo": "inventario", "silenciar": False})
    assert alerta(admin, "inventario")["silenciada"] is False

    # Cancelaciones: con umbral 1, cancelar un ítem ya alerta con el nombre de quien canceló
    try:
        configurar(admin, cancelaciones=1)
        externa = table(caja, "Para llevar", incluir_externa=True)
        producto = find(admin.data("/producto/list"), nombre="Gaseosa 400 ml")
        orden = caja.data("/orden/create", {"mesa_id": externa["id"], "clave_idempotencia": key(), "cliente_nombre": "Alertas",
                                            "items": [{"producto_id": producto["id"], "cantidad": 1}]}, expect=201)
        caja.data("/orden/cancelar_item", {"orden_item_id": orden["items"][0]["id"], "motivo": "Prueba de alertas"})
        cancelaciones = alerta(admin, "cancelaciones")
        assert any("ítems" in d for d in cancelaciones["detalle"])
        assert find(admin.data("/alerta/config/get"), codigo="cancelaciones")["umbral"] == 1

        # Una alerta apagada no aparece
        filas = admin.data("/alerta/config/get")
        admin.data("/alerta/config/save", {"alertas": [{**f, "activa": f["codigo"] != "cancelaciones", "umbral": 1 if f["codigo"] == "cancelaciones" else f["umbral"]} for f in filas]})
        assert alerta(admin, "cancelaciones") is None
    finally:
        configurar(admin)

    assert "no es válido" in admin.post("/alerta/config/save", {"alertas": [{"codigo": "mesas_abiertas", "umbral": 0}]}).json()["message"]
    assert mesero.post("/alerta/list").status_code == 403
    assert caja.post("/alerta/silenciar", {"codigo": "inventario"}).status_code == 403


def test_comanda_demorada(esquina):
    admin, _ = esquina["admin.esquina"]
    caja, _ = esquina["caja.esquina"]
    externa = table(caja, "Para llevar", incluir_externa=True)
    producto = find(admin.data("/producto/list"), nombre="Papas a la francesa")
    orden = caja.data("/orden/create", {"mesa_id": externa["id"], "clave_idempotencia": key(), "cliente_nombre": "Demora",
                                        "items": [{"producto_id": producto["id"], "cantidad": 1}]}, expect=201)
    # La comanda llegó hace una hora: más que cualquier tiempo objetivo
    with admin_engine.begin() as conn:
        conn.execute(text("UPDATE comanda SET creado_en = creado_en - interval '1 hour' WHERE orden_id = :id"), {"id": orden["id"]})
    demoradas = alerta(admin, "comandas_demoradas")
    assert demoradas["nivel"] == "urgente" and any(d.startswith("Cocina") for d in demoradas["detalle"])
    caja.data("/orden/cancelar_item", {"orden_item_id": orden["items"][0]["id"], "motivo": "Prueba de demora"})


def test_resumen_del_dia_y_aviso_al_cerrar(client):
    soporte, _ = login(client, "soporte", "Soporte12345")
    soporte.data("/plataforma/empresa/create", {
        "nombre_comercial": "Café Resumen", "modulos": ["pedidos", "caja"], "estado_contrato": "activo",
        "admin": {"usuario": "duena.resumen", "nombre": "Dueña", "password": "clave12345"},
        "restaurante": {"nombre": "Resumen Centro", "hora_inicio_jornada": "05:00"},
    }, expect=201)
    duena, _ = login(client, "duena.resumen", "clave12345")
    duena.data("/usuario/create", {"usuario": "admin.resumen", "nombre": "Admin", "password": "clave12345",
                                   "roles": ["admin_restaurante"]}, expect=201)
    admin, _ = login(client, "admin.resumen", "clave12345")
    categoria = admin.data("/categoria/create", {"nombre": "Café"}, expect=201)
    tinto = admin.data("/producto/create", {"categoria_id": categoria["id"], "nombre": "Tinto", "precio": 2000}, expect=201)

    assert admin.post("/reporte/resumen_diario/config/save", {"activo": True}).json()["message"].startswith("Escribe el celular")
    config = admin.data("/reporte/resumen_diario/config/save", {"activo": True, "telefono": "300 555 1234", "nombre": "Marta"})
    assert config["telefono"] == "300 555 1234" and config["activo"] is True

    externa = table(admin, "Para llevar", incluir_externa=True)
    admin.data("/orden/create", {"mesa_id": externa["id"], "clave_idempotencia": key(), "cliente_nombre": "Leo",
                                 "items": [{"producto_id": tinto["id"], "cantidad": 3}]}, expect=201)
    pay_table(admin, sesion_mesa_id=admin.data("/cuenta/pendientes")[0]["sesion_mesa_id"])

    resumen = admin.data("/reporte/resumen_diario")
    assert resumen["en_curso"] is True and resumen["totales"]["ventas"] == 6000
    assert "Ventas: $ 6.000" in resumen["texto"] and "3 Tinto" in resumen["texto"]
    assert resumen["telefono"] == "573005551234"

    # Faltaron 1.000 al cerrar el turno: alerta de caja y línea en el resumen
    turno = admin.data("/caja/estado")["turno"]
    admin.data("/caja/turno/cerrar", {"efectivo_contado": turno["resumen"]["efectivo_esperado"] - 1000})
    configurar(admin, diferencia_caja=1000)
    caja_alerta = alerta(admin, "diferencia_caja")
    assert caja_alerta["detalle"] == ["Admin: faltaron $ 1.000"]
    assert "Caja: a Admin le faltaron $ 1.000" in admin.data("/reporte/resumen_diario")["texto"]

    # Al cerrar la jornada el resumen queda por enviar en los avisos de WhatsApp
    admin.data("/caja/jornada/cerrar")
    aviso = find(admin.data("/notificacion/list"), evento="resumen_diario")
    assert aviso["estado"] == "manual" and aviso["telefono"] == "573005551234" and aviso["evento_texto"] == "Resumen del día"
    assert "Jornada cerrada a las" in aviso["mensaje"] and "*Resumen de Resumen Centro*" in aviso["mensaje"]

    dia = admin.data("/reporte/resumen_diario")["jornada"]
    from datetime import date
    assert admin.post("/reporte/resumen_diario", {"jornada": str(date.fromisoformat(dia) + timedelta(days=1))}).status_code == 400
    assert Api(client).post("/reporte/resumen_diario").status_code == 401
