"""
Reportes (doc 26): las cifras cuadran con las cuentas pagadas (RN-REP-01) y respetan permisos.
Se arman en un restaurante propio para tener cifras exactas sin depender de otras pruebas.
"""
from datetime import date, timedelta
import pytest
from conftest import login, key, find, table, ensure_shift, medio


@pytest.fixture(scope="module")
def local(client):
    soporte, _ = login(client, "soporte", "Soporte12345")
    soporte.data("/plataforma/empresa/create", {
        "nombre_comercial": "Asadero Reportes", "modulos": ["pedidos", "caja"], "estado_contrato": "activo",
        "admin": {"usuario": "duena.reportes", "nombre": "Dueña Reportes", "password": "clave12345"},
        "restaurante": {"nombre": "Asadero Centro", "hora_inicio_jornada": "00:00"},
    }, expect=201)
    duena, _ = login(client, "duena.reportes", "clave12345")
    salon = find(duena.data("/zona/list"), nombre="Salón")["id"]
    duena.data("/mesa/create_lote", {"zona_id": salon, "desde": 1, "hasta": 3}, expect=201)
    for usuario, nombre, roles, zonas in [("admin.reportes", "Admin Reportes", ["admin_restaurante"], []),
                                          ("mesero.uno", "Mesero Uno", ["mesero"], [salon]),
                                          ("mesero.dos", "Mesero Dos", ["mesero"], [salon])]:
        duena.data("/usuario/create", {"usuario": usuario, "nombre": nombre, "password": "clave12345",
                                       "roles": roles, "zonas": zonas}, expect=201)
    admin, _ = login(client, "admin.reportes", "clave12345")
    categoria = admin.data("/categoria/create", {"nombre": "Asados"}, expect=201)
    pollo = admin.data("/producto/create", {"categoria_id": categoria["id"], "nombre": "Pollo asado", "precio": 30000}, expect=201)
    gaseosa = admin.data("/producto/create", {"categoria_id": categoria["id"], "nombre": "Gaseosa", "precio": 5000}, expect=201)
    uno, _ = login(client, "mesero.uno", "clave12345")
    dos, _ = login(client, "mesero.dos", "clave12345")
    ensure_shift(admin)

    def vender(mesero, mesa, items, propina=0, descuento=0):
        mesa_id = table(mesero, mesa)["id"]
        orden = mesero.data("/orden/create", {"mesa_id": mesa_id, "clave_idempotencia": key(), "items": items}, expect=201)
        cuenta = admin.data("/cuenta/abrir", {"mesa_id": mesa_id})
        cuenta = admin.data("/cuenta/ajustar", {"cuenta_id": cuenta["id"], "propina": propina, "descuento": descuento,
                                                "descuento_motivo": "Prueba" if descuento else None})
        admin.data("/cuenta/pagar", {"cuenta_id": cuenta["id"], "clave_idempotencia": key(), "pagos": [
            {"medio_pago_id": medio(admin, "Efectivo"), "monto": cuenta["saldo"]}]})
        return orden

    # Mesa 1: 2 pollos + 1 gaseosa, propina 6.500 → venta 65.000
    vender(uno, "Mesa 1", [{"producto_id": pollo["id"], "cantidad": 2}, {"producto_id": gaseosa["id"], "cantidad": 1}], propina=6500)
    # Mesa 2: 1 pollo con descuento 5.000 → venta 25.000
    vender(dos, "Mesa 2", [{"producto_id": pollo["id"], "cantidad": 1}], descuento=5000)
    # Mesa 3: una gaseosa cancelada y nada cobrado todavía
    orden = uno.data("/orden/create", {"mesa_id": table(uno, "Mesa 3")["id"], "clave_idempotencia": key(),
                                       "items": [{"producto_id": gaseosa["id"], "cantidad": 2}]}, expect=201)
    uno.data("/orden/cancelar_item", {"orden_item_id": orden["items"][0]["id"], "motivo": "Se fueron"})
    return {"admin": admin, "uno": uno, "dos": dos}


def test_ventas_del_dia_cuadran_con_caja(local):
    admin = local["admin"]
    reporte = admin.data("/reporte/ventas")
    t = reporte["totales"]
    assert t["ventas"] == 65000 + 25000
    assert t["cuentas"] == 2 and t["ticket_promedio"] == 45000
    assert t["propinas"] == 6500 and t["descuentos"] == 5000
    assert reporte["base"] == "cuentas pagadas"

    # Cuadra con la caja (RN-REP-01): lo cobrado en efectivo = ventas + propinas
    efectivo = find(reporte["medios"], nombre="Efectivo")["valor"]
    assert efectivo == t["ventas"] + t["propinas"]

    productos = {p["nombre"]: p for p in reporte["productos"]}
    assert productos["Pollo asado"]["unidades"] == 3 and productos["Pollo asado"]["valor"] == 90000
    assert productos["Gaseosa"]["unidades"] == 1
    assert reporte["cancelaciones"]["items"] == 1 and reporte["cancelaciones"]["valor"] == 10000
    assert [z["nombre"] for z in reporte["zonas"]] == ["Salón"]
    assert reporte["comparativos"][0]["nombre"] == "Mismo día de la semana pasada"
    assert reporte["comparativos"][0]["variacion_ventas"] is None  # no hay base para comparar


def test_periodo_y_validaciones(local):
    admin = local["admin"]
    hoy = date.fromisoformat(admin.data("/reporte/dashboard")["jornada"])
    semana = admin.data("/reporte/ventas", {"desde": str(hoy - timedelta(days=6)), "hasta": str(hoy)})
    assert len(semana["serie"]) == 7 and semana["serie"][-1]["ventas"] == 90000
    assert semana["comparativos"][0]["nombre"] == "Periodo anterior"
    assert admin.post("/reporte/ventas", {"desde": str(hoy), "hasta": str(hoy - timedelta(days=1))}).status_code == 400
    assert admin.post("/reporte/ventas", {"desde": "2020-01-01", "hasta": "2026-01-01"}).status_code == 400


def test_informe_por_mesero(local):
    admin, uno = local["admin"], local["uno"]
    resumen = {m["nombre"]: m for m in admin.data("/reporte/meseros")}
    assert resumen["Mesero Uno"]["ventas"] == 65000 and resumen["Mesero Uno"]["cancelaciones"] == 1
    assert resumen["Mesero Dos"]["ventas"] == 30000  # ventas por ítems, antes del descuento de la cuenta

    # El mesero ve su propio informe, no el de otro (doc 29)
    propio = uno.data("/reporte/mesero")
    assert propio["mesero"] == "Mesero Uno"
    assert propio["atencion"]["mesas"] == 2 and propio["ventas"]["propinas"] == 6500
    assert propio["excepciones"]["mesas_sin_cobrar"] == 1
    assert propio["excepciones"]["cancelaciones"][0]["motivo"] == "Se fueron"
    assert propio["turnos"][0]["inicio"]
    otro = uno.data("/reporte/mesero", {"usuario_id": resumen["Mesero Dos"]["mesero_id"]})
    assert otro["mesero"] == "Mesero Uno"
    assert uno.post("/reporte/ventas").status_code == 403


def test_dashboard(local):
    admin = local["admin"]
    tablero = admin.data("/reporte/dashboard")
    assert tablero["hoy"]["ventas"] == 90000
    assert tablero["caja"]["turno_abierto"] is True and tablero["caja"]["por_cobrar"] == 1
    assert tablero["productos_del_dia"][0]["nombre"] == "Pollo asado"
