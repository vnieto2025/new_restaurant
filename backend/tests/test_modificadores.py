from conftest import key, find, product_id, table, option_id


def test_modificadores_suman_precio_y_llegan_a_cocina(esquina):
    mesero, _ = esquina["mesero.salon"]
    admin, _ = esquina["admin.esquina"]
    cocina, sesion_cocina = esquina["cocina.esquina"]
    mesa = table(mesero, "Mesa 6")

    # La carta de la mesa trae los grupos de cada producto
    carta = mesero.data("/orden/carta", {"mesa_id": mesa["id"]})
    clasica = find(find(carta["categorias"], nombre="Hamburguesas")["productos"], nombre="Hamburguesa clásica")
    assert [g["nombre"] for g in clasica["grupos"]] == ["Término de la carne", "Adicionales", "Quitar ingredientes"]

    elegidas = [option_id(admin, "Término de la carne", "Tres cuartos"), option_id(admin, "Adicionales", "Queso extra"),
                option_id(admin, "Adicionales", "Tocineta"), option_id(admin, "Quitar ingredientes", "Sin cebolla")]
    orden = mesero.data("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(), "items": [
        {"producto_id": clasica["id"], "cantidad": 2, "modificadores": elegidas}]}, expect=201)

    item = orden["items"][0]
    assert item["precio_unitario"] == 18000 + 3000 + 4000
    assert item["total"] == 2 * 25000
    assert [m["nombre"] for m in item["modificadores"]] == ["Tres cuartos", "Queso extra", "Tocineta", "Sin cebolla"]

    punto = find(sesion_cocina["puntos"], nombre="Cocina")
    tarjeta = find(cocina.data("/cocina/comandas", {"punto_produccion_id": punto["id"]})["en_proceso"], orden_id=orden["id"])
    assert tarjeta["items"][0]["modificadores"] == ["Tres cuartos", "Queso extra", "Tocineta", "Sin cebolla"]


def test_minimos_maximos_y_opciones_ajenas(esquina):
    mesero, _ = esquina["mesero.salon"]
    admin, _ = esquina["admin.esquina"]
    mesa = table(mesero, "Mesa 6")
    clasica = product_id(admin, "Hamburguesa clásica")
    perro = product_id(admin, "Perro sencillo")

    def pedir(producto, opciones):
        return mesero.post("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(), "items": [
            {"producto_id": producto, "cantidad": 1, "modificadores": opciones}]})

    # Grupo obligatorio sin elegir
    response = pedir(clasica, [])
    assert response.status_code == 400 and "término de la carne" in response.json()["message"]
    # Dos términos cuando el máximo es uno
    response = pedir(clasica, [option_id(admin, "Término de la carne", "Medio"),
                               option_id(admin, "Término de la carne", "Bien asada")])
    assert response.status_code == 400 and "máximo 1" in response.json()["message"]
    # Opción de un grupo que el producto no tiene (el perro no tiene término)
    response = pedir(perro, [option_id(admin, "Término de la carne", "Medio")])
    assert response.status_code == 409
    # El perro sí acepta adicionales
    assert pedir(perro, [option_id(admin, "Adicionales", "Huevo")]).status_code == 201


def test_editar_grupo_conserva_lo_ya_pedido(esquina):
    admin, _ = esquina["admin.esquina"]
    mesero, _ = esquina["mesero.terraza"]
    grupo = admin.data("/modificador/create", {"nombre": "Salsas", "minimo": 0, "maximo": 2, "opciones": [
        {"nombre": "Rosada", "precio_extra": 0}, {"nombre": "Piña", "precio_extra": 500}]}, expect=201)
    producto = admin.data("/producto/list", {"buscar": "Salchipapa"})[0]
    admin.data("/producto/update", {**producto, "producto_id": producto["id"], "grupos": [grupo["id"]]})

    pina = find(grupo["opciones"], nombre="Piña")["id"]
    mesa = table(mesero, "Terraza 1")
    orden = mesero.data("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(),
                                          "items": [{"producto_id": producto["id"], "cantidad": 1, "modificadores": [pina]}]},
                        expect=201)

    # Quitar una opción y subir el precio de otra no cambia la orden ya hecha (RG-13)
    rosada = find(grupo["opciones"], nombre="Rosada")["id"]
    actualizado = admin.data("/modificador/update", {"grupo_id": grupo["id"], "nombre": "Salsas", "minimo": 0, "maximo": 2,
                                                    "opciones": [{"id": rosada, "nombre": "Rosada", "precio_extra": 300}]})
    assert [o["nombre"] for o in actualizado["opciones"]] == ["Rosada"]
    detalle = mesero.data("/orden/get", {"orden_id": orden["id"]})
    assert detalle["items"][0]["modificadores"] == [{"grupo": "Salsas", "nombre": "Piña", "precio_extra": 500}]
    assert detalle["items"][0]["total"] == 15000 + 500

    # La opción retirada ya no se puede pedir
    response = mesero.post("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(),
                                             "items": [{"producto_id": producto["id"], "cantidad": 1, "modificadores": [pina]}]})
    assert response.status_code == 409
    admin.data("/producto/update", {**producto, "producto_id": producto["id"], "grupos": []})


def test_validaciones_del_grupo(esquina):
    admin, _ = esquina["admin.esquina"]
    assert admin.post("/modificador/create", {"nombre": "Vacío", "opciones": []}).status_code == 400
    assert admin.post("/modificador/create", {"nombre": "Raro", "minimo": 3, "maximo": 1,
                                              "opciones": [{"nombre": "A"}]}).status_code == 400
    assert admin.post("/modificador/create", {"nombre": "Negativo",
                                              "opciones": [{"nombre": "A", "precio_extra": -100}]}).status_code == 400
    mesero, _ = esquina["mesero.salon"]
    assert mesero.post("/modificador/list").status_code == 403
