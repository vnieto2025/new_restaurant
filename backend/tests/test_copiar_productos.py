"""
Duplicar un producto y copiar la carta a otro restaurante de la empresa (docs 07 y 12): lo que existe no se pisa,
puntos e impuestos se enlazan por nombre, los modificadores viajan y nada cruza entre empresas.
"""
from conftest import find, login, product_id


def test_duplicar_conserva_cartas_modificadores_y_receta(esquina):
    admin, _ = esquina["admin.esquina"]
    original = find(admin.data("/producto/list", {"todos": True}), nombre="Hamburguesa clásica")
    copia = admin.data("/producto/duplicar", {"producto_id": original["id"]}, expect=201)
    assert copia["nombre"] == "Hamburguesa clásica (copia)" and copia["precio"] == original["precio"]
    assert sorted(copia["cartas"]) == sorted(original["cartas"])
    assert copia["grupos"] == original["grupos"] and copia["grupos"]
    assert not copia["agotado"] and copia["id"] != original["id"]
    assert admin.data("/producto/duplicar", {"producto_id": original["id"]}, expect=201)["nombre"] == "Hamburguesa clásica (copia 2)"

    receta_original = admin.post("/receta/get", {"producto_id": original["id"]}).json()["data"]
    receta_copia = admin.post("/receta/get", {"producto_id": copia["id"]}).json()["data"]
    if receta_original and receta_original.get("lineas"):
        assert len(receta_copia["lineas"]) == len(receta_original["lineas"])

    # Sin permiso de catálogo no se duplica
    caja, _ = esquina["caja.esquina"]
    assert caja.post("/producto/duplicar", {"producto_id": original["id"]}).status_code == 403


def test_copiar_a_otra_sede_sin_pisar_lo_existente(client, esquina):
    soporte, _ = login(client, "soporte", "Soporte12345")
    empresa = soporte.data("/plataforma/empresa/create", {
        "nombre_comercial": "Cadena Copia", "modulos": ["pedidos"], "estado_contrato": "activo",
        "admin": {"usuario": "dueno.copia", "nombre": "Dueño", "password": "clave12345"},
        "restaurante": {"nombre": "Sede Uno"}}, expect=201)
    sede_dos = soporte.data("/plataforma/restaurante/create", {"empresa_id": empresa["id"], "modulos": ["pedidos"], "estado_contrato": "activo",
                                                               "restaurante": {"nombre": "Sede Dos"}}, expect=201)
    dueno, sesion = login(client, "dueno.copia", "clave12345")
    uno = sesion["restaurante"]["id"]
    dos = sede_dos["id"]

    grupo = dueno.data("/modificador/create", {"nombre": "Salsas", "minimo": 0, "maximo": 2,
                                               "opciones": [{"nombre": "Ajo", "precio_extra": 500}]}, expect=201)
    categoria = dueno.data("/categoria/create", {"nombre": "Asados"}, expect=201)
    bar = dueno.data("/punto_produccion/create", {"nombre": "Parrilla", "tipo": "cocina"}, expect=201)
    pollo = dueno.data("/producto/create", {"categoria_id": categoria["id"], "nombre": "Pollo", "precio": 20000, "descripcion": "Entero",
                                            "punto_produccion_id": bar["id"], "grupos": [grupo["id"]]}, expect=201)
    carne = dueno.data("/producto/create", {"categoria_id": categoria["id"], "nombre": "Carne", "precio": 30000}, expect=201)

    # En la otra sede ya existe Carne con su propio precio
    dueno_dos, _ = login(client, "dueno.copia", "clave12345", restaurante_id=dos)
    asados = dueno_dos.data("/categoria/create", {"nombre": "Asados"}, expect=201)
    dueno_dos.data("/producto/create", {"categoria_id": asados["id"], "nombre": "Carne", "precio": 35000}, expect=201)

    resultado = dueno.data("/producto/copiar", {"restaurante_id": dos, "productos": [pollo["id"], carne["id"]]})
    assert resultado["creados"] == 1 and resultado["omitidos"] == ["Carne"] and resultado["categorias_nuevas"] == 0

    alla = dueno_dos.data("/producto/list", {"todos": True})
    assert find(alla, nombre="Carne")["precio"] == 35000  # no se pisa
    copiado = find(alla, nombre="Pollo")
    assert copiado["precio"] == 20000 and copiado["descripcion"] == "Entero" and copiado["cartas"]
    assert copiado["punto_produccion_id"] is None  # allá no hay Parrilla: usa el de su categoría
    salsas = find(dueno_dos.data("/modificador/list"), nombre="Salsas")
    assert copiado["grupos"] == [salsas["id"]] and salsas["id"] != grupo["id"]
    assert salsas["opciones"][0]["nombre"] == "Ajo" and salsas["opciones"][0]["precio_extra"] == 500
    # Copiar de nuevo no duplica nada
    assert dueno.data("/producto/copiar", {"restaurante_id": dos, "productos": [pollo["id"]]})["creados"] == 0

    # Validaciones: mismo restaurante, otra empresa, productos ajenos y permisos
    assert dueno.post("/producto/copiar", {"restaurante_id": uno, "productos": [pollo["id"]]}).status_code == 404
    otra_empresa = esquina["admin.esquina"][1]["restaurante"]["id"]
    assert dueno.post("/producto/copiar", {"restaurante_id": otra_empresa, "productos": [pollo["id"]]}).status_code == 404
    ajeno = product_id(esquina["admin.esquina"][0], "Limonada natural")
    assert dueno.post("/producto/copiar", {"restaurante_id": dos, "productos": [ajeno]}).status_code == 404
    admin, _ = esquina["admin.esquina"]
    assert admin.post("/producto/copiar", {"restaurante_id": dos, "productos": [ajeno]}).status_code == 403
