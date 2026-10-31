"""
Rol de contador o auditor (doc 08): consulta informes y exporta, sin operar. No ve ni baja la base de clientes.
"""
from conftest import login
from test_solo_lectura import rutas_con_sesion
from Utils.acceso import RUTAS_LECTURA


def test_contador_no_puede_escribir_en_ninguna_ruta(client, esquina):
    contador, sesion = login(client, "contador.esquina")
    assert sesion["roles"] == ["contador"]
    for ruta in set(rutas_con_sesion()) - RUTAS_LECTURA:
        respuesta = contador.post(ruta)
        assert respuesta.status_code == 403, ruta
        assert respuesta.json()["detail"]["codigo"] == "permiso_insuficiente", ruta


def test_contador_consulta_y_exporta_pero_no_ve_clientes(client, esquina):
    contador, _ = login(client, "contador.esquina")
    for ruta in ["/reporte/ventas", "/reporte/meseros", "/reporte/dashboard", "/caja/turno/list", "/cuenta/list", "/documento/list",
                 "/compra/list", "/inventario/estado", "/auditoria/list", "/cupon/resultados", "/orden/list", "/exportacion/catalogo"]:
        assert contador.post(ruta).status_code == 200, ruta

    claves = {c["clave"] for g in contador.data("/exportacion/catalogo")["grupos"] for c in g["conjuntos"]}
    assert {"cuentas", "pagos", "documentos", "compras", "existencias", "horas", "liquidaciones"} <= claves
    assert "clientes" not in claves
    assert contador.post("/exportacion/generar", {"conjunto": "clientes", "formato": "csv"}).status_code == 403
    assert contador.post("/cliente/list").status_code == 403
    assert contador.post("/exportacion/generar", {"conjunto": "productos", "formato": "csv"}).status_code == 200


def test_el_administrador_puede_asignar_el_rol(esquina):
    admin, _ = esquina["admin.esquina"]
    assert any(r["codigo"] == "contador" for r in admin.data("/usuario/roles"))
