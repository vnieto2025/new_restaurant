"""
Código de barras de los productos (ADR-058): único en el restaurante, viaja en la carta de mesa, mostrador y caja,
no se copia al duplicar y se carga desde Excel aunque la celda sea un número.
"""
from conftest import find, table
from test_importar_productos import xlsx
from Class.Producto import normalizar_codigo


def test_normalizar_codigo():
    assert normalizar_codigo(7702004003409) == "7702004003409"
    assert normalizar_codigo(7702004003409.0) == "7702004003409"
    assert normalizar_codigo(" 7702 0040 ") == "77020040"
    assert normalizar_codigo("") is None and normalizar_codigo(None) is None


def test_codigo_unico_y_en_la_carta(esquina):
    admin, _ = esquina["admin.esquina"]
    mesero, _ = esquina["mesero.salon"]
    caja, _ = esquina["caja.esquina"]
    agua = find(admin.data("/producto/list"), nombre="Agua sin gas")
    datos = {k: agua[k] for k in ("categoria_id", "nombre", "precio", "punto_produccion_id", "orden", "cartas")}
    admin.data("/producto/update", {**datos, "producto_id": agua["id"], "codigo_barras": " 7702090012345 "})
    assert find(admin.data("/producto/list"), nombre="Agua sin gas")["codigo_barras"] == "7702090012345"

    # Lo ven las pantallas que venden: la mesa del mesero y la venta directa de la caja
    carta = mesero.data("/orden/carta", {"mesa_id": table(mesero, "Mesa 6")["id"]})
    en_mesa = next(p for c in carta["categorias"] for p in c["productos"] if p["nombre"] == "Agua sin gas")
    assert en_mesa["codigo_barras"] == "7702090012345"
    en_caja = next(p for c in caja.data("/pos/carta")["categorias"] for p in c["productos"] if p["nombre"] == "Agua sin gas")
    assert en_caja["codigo_barras"] == "7702090012345"

    # Otro producto no puede tener el mismo código; uno con caracteres raros se rechaza
    cerveza = find(admin.data("/producto/list"), nombre="Cerveza nacional")
    otros = {k: cerveza[k] for k in ("categoria_id", "nombre", "precio", "punto_produccion_id", "orden", "cartas")}
    respuesta = admin.post("/producto/update", {**otros, "producto_id": cerveza["id"], "codigo_barras": "7702090012345"})
    assert "ya lo tiene Agua sin gas" in respuesta.json()["message"]
    assert "solo lleva letras" in admin.post("/producto/update", {**otros, "producto_id": cerveza["id"], "codigo_barras": "77/02"}).json()["message"]

    # Al duplicar, la copia queda sin código (no puede repetirse)
    copia = admin.data("/producto/duplicar", {"producto_id": agua["id"]}, expect=201)
    assert copia["codigo_barras"] is None
    admin.data("/producto/change_status", {"producto_id": copia["id"], "activo": False})

    # Quitarlo: vacío lo deja sin código
    admin.data("/producto/update", {**datos, "producto_id": agua["id"], "codigo_barras": None})
    assert find(admin.data("/producto/list"), nombre="Agua sin gas")["codigo_barras"] is None


def test_importar_con_codigo_de_barras(napoli):
    admin, _ = napoli["napoli"]
    titulos = ["Producto", "Categoría", "Precio", "Código de barras"]
    archivo = xlsx([["Gaseosa lata", "Bebidas", 3500, 7702004003409], ["Agua lata", "Bebidas", 3000, 7702004003409]], titulos)
    revision = admin.data("/producto/importar/revisar", archivo)
    assert any("ya aparece en una fila anterior" in e for e in revision["filas"][1]["errores"])

    archivo = xlsx([["Gaseosa lata", "Bebidas", 3500, 7702004003409.0]], titulos)
    admin.data("/producto/importar/aplicar", archivo)
    assert find(admin.data("/producto/list"), nombre="Gaseosa lata")["codigo_barras"] == "7702004003409"
    # Otro producto con el mismo código en un archivo nuevo: error
    revision = admin.data("/producto/importar/revisar", xlsx([["Gaseosa botella", "Bebidas", 4000, "7702004003409"]], titulos))
    assert any("otro producto" in e for e in revision["filas"][0]["errores"])
