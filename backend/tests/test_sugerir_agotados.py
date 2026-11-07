"""
Sugerir agotados con el inventario (doc 12, sección 5; ADR-051): cuántas porciones alcanzan, qué plato
sugerir agotar cuando un insumo se acaba, cuál se está acabando y cuál ya se puede volver a ofrecer.
"""
from conftest import find, product_id
from test_inventario import stock, pedir, abrir_en_cocina


def sugerencias(api, sesion=None, punto=None):
    data = {"punto_produccion_id": find(sesion["puntos"], nombre=punto)["id"]} if punto else {}
    return api.data("/producto/sugerir_agotados", data)


def nombres(filas):
    return [f["nombre"] for f in filas]


def ajustar(admin, insumo, existencia):
    admin.data("/inventario/ajuste", {"insumo_id": insumo["id"], "existencia_real": existencia, "motivo": "Prueba de agotados"})


def test_sugiere_agotar_cuando_cocina_gasta_el_ultimo_insumo(esquina):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    cocina, sesion = esquina["cocina.esquina"]
    pan = stock(admin, "Pan de perro")
    assert "Perro sencillo" not in nombres(sugerencias(cocina, sesion, "Cocina")["sugeridos"])

    try:
        # Queda un pan: alcanza para un perro y se avisa que se está acabando
        ajustar(admin, pan, 1)
        por_acabarse = find(sugerencias(cocina, sesion, "Cocina")["por_acabarse"], nombre="Perro sencillo")
        assert por_acabarse["porciones"] == 1 and nombres(por_acabarse["limitan"]) == ["Pan de perro"]

        # Cocina prepara ese perro: el pan llega a cero y se sugiere agotarlo, sin marcarlo solo
        abrir_en_cocina(cocina, sesion, pedir(caja, admin, "Perro sencillo"))
        sugerido = find(sugerencias(cocina, sesion, "Cocina")["sugeridos"], nombre="Perro sencillo")
        assert sugerido["porciones"] == 0
        assert sugerido["motivo"] == "Pan de perro: quedan 0 und y cada uno lleva 1 und"
        assert find(admin.data("/producto/list"), nombre="Perro sencillo")["agotado"] is False
        # El bar no ve lo que se prepara en la cocina
        bar, sesion_bar = esquina["bar.esquina"]
        assert "Perro sencillo" not in nombres(sugerencias(bar, sesion_bar, "Bar")["sugeridos"])
        # Ni pide la lista de un punto que no tiene asignado
        assert bar.post("/producto/sugerir_agotados", {"punto_produccion_id": find(sesion["puntos"], nombre="Cocina")["id"]}).status_code == 403

        # Ya agotado deja de sugerirse; al reponer el pan se sugiere volver a ofrecerlo
        perro = product_id(admin, "Perro sencillo")
        cocina.data("/producto/agotado", {"producto_id": perro, "agotado": True})
        assert "Perro sencillo" not in nombres(sugerencias(admin)["sugeridos"])
        admin.data("/inventario/entrada", {"insumo_id": pan["id"], "cantidad": 10, "costo_unitario": 700})
        assert find(sugerencias(admin)["con_insumos"], nombre="Perro sencillo")["porciones"] == 10
    finally:
        ajustar(admin, pan, pan["stock"])
        admin.data("/producto/agotado", {"producto_id": product_id(admin, "Perro sencillo"), "agotado": False})


def test_insumo_sin_inventario_cargado_no_sugiere_nada(esquina):
    admin, _ = esquina["admin.esquina"]
    categoria = find(admin.data("/categoria/list"), nombre="Bebidas")
    insumo = admin.data("/insumo/create", {"nombre": "Hierbabuena de prueba", "unidad": "g"}, expect=201)
    producto = admin.data("/producto/create", {"categoria_id": categoria["id"], "nombre": "Aromática de prueba", "precio": 3000}, expect=201)
    try:
        admin.data("/receta/save", {"producto_id": producto["id"], "rendimiento": 1, "lineas": [{"insumo_id": insumo["id"], "cantidad": 10}]})
        # Nunca entró hierbabuena al inventario: su stock en cero no dice que se acabó
        assert "Aromática de prueba" not in nombres(sugerencias(admin)["sugeridos"])

        admin.data("/inventario/entrada", {"insumo_id": insumo["id"], "cantidad": 25, "costo_unitario": 40})
        assert find(sugerencias(admin)["por_acabarse"], nombre="Aromática de prueba")["porciones"] == 2
    finally:
        admin.data("/producto/change_status", {"producto_id": producto["id"], "activo": False})


def test_combo_afectado_y_permisos(esquina, napoli):
    admin, _ = esquina["admin.esquina"]
    mesero, _ = esquina["mesero.salon"]
    papa = stock(admin, "Papa")
    try:
        ajustar(admin, papa, 0)
        papas = find(sugerencias(admin)["sugeridos"], nombre="Papas a la francesa")
        # El combo que trae las papas como parte fija también se queda sin ellas
        assert papas["combos"] == ["Combo clásico"]
        assert {"Salchipapa", "Perro sencillo"} <= set(nombres(sugerencias(admin)["sugeridos"]))
    finally:
        ajustar(admin, papa, papa["stock"])

    assert mesero.post("/producto/sugerir_agotados").status_code == 403
    assert napoli["napoli"][0].post("/producto/sugerir_agotados").json()["detail"]["codigo"] == "modulo_no_contratado"
