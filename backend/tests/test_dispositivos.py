"""
Tablet compartida (doc 08 sección 2, ADR-026): dispositivo autorizado, PIN por persona y turno del mesero.
"""
from conftest import Api, key, find, table, product_id, pay_table


def emparejar(client, admin, tipo="zona", zona="Salón", punto=None, nombre="Tablet Salón"):
    body = {"nombre": nombre, "tipo": tipo}
    if tipo == "zona":
        body["zona_id"] = find(admin.data("/zona/list"), nombre=zona)["id"]
    else:
        body["punto_produccion_id"] = find(admin.data("/punto_produccion/list"), nombre=punto)["id"]
    creado = admin.data("/dispositivo/create", body, expect=201)
    assert len(creado["codigo"]) == 6
    pareado = Api(client).data("/dispositivo/emparejar", {"codigo": creado["codigo"]})
    return creado, pareado["token"]


def usuario_id(admin, usuario):
    return find(admin.data("/usuario/list"), usuario=usuario)["id"]


def test_pin_en_tablet_de_zona_y_turno_del_mesero(client, esquina):
    admin, _ = esquina["admin.esquina"]
    caja, _ = esquina["caja.esquina"]
    creado, token = emparejar(client, admin)

    # El código es de un solo uso
    assert Api(client).post("/dispositivo/emparejar", {"codigo": creado["codigo"]}).status_code == 404

    # PIN débil o repetido se rechaza; cada persona tiene el suyo
    carlos = usuario_id(admin, "mesero.salon")
    assert admin.post("/usuario/pin", {"usuario_id": carlos, "pin": "1111"}).status_code == 400
    admin.data("/usuario/pin", {"usuario_id": carlos, "pin": "4821"})
    ana = usuario_id(admin, "mesero.terraza")
    assert admin.post("/usuario/pin", {"usuario_id": ana, "pin": "4821"}).status_code == 400
    admin.data("/usuario/pin", {"usuario_id": ana, "pin": "7305"})

    # Carlos entra con su PIN en la tablet del Salón; su sesión queda ligada al dispositivo
    sesion = Api(client).data("/dispositivo/pin", {"token": token, "pin": "4821"})
    assert sesion["usuario"]["usuario"] == "mesero.salon"
    assert sesion["dispositivo"]["nombre"] == "Tablet Salón"
    carlos_api = Api(client, sesion["token"])
    assert carlos_api.data("/turno_mesero/actual")["estado"] == "abierto"

    # Ana atiende Terraza: su PIN no sirve en la tablet del Salón
    assert Api(client).post("/dispositivo/pin", {"token": token, "pin": "7305"}).status_code == 400
    assert any(r["accion"] == "pin_fallido" for r in admin.data("/auditoria/list", {"accion": "pin_fallido"}))

    # No termina el turno con una mesa a su cargo (RN-MSR-04)
    mesa = table(carlos_api, "Mesa 6")
    if mesa["estado"] != "libre":
        pay_table(caja, mesa_id=mesa["id"])
    carlos_api.data("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(),
                                      "items": [{"producto_id": product_id(admin, "Agua sin gas"), "cantidad": 1}]}, expect=201)
    response = carlos_api.post("/turno_mesero/cerrar")
    assert response.status_code == 409 and "Mesa 6" in response.json()["message"]
    pay_table(caja, mesa_id=mesa["id"])
    assert carlos_api.data("/turno_mesero/cerrar")["estado"] == "cerrado"

    # Desautorizar el dispositivo corta la sesión abierta con PIN al instante
    admin.data("/dispositivo/change_status", {"dispositivo_id": creado["id"], "activo": False})
    assert carlos_api.post("/mesa/list").status_code == 401
    assert Api(client).post("/dispositivo/pin", {"token": token, "pin": "4821"}).status_code == 401


def test_pin_en_pantalla_de_cocina(client, esquina):
    admin, _ = esquina["admin.esquina"]
    _, token = emparejar(client, admin, tipo="produccion", punto="Bar", nombre="Pantalla Bar")
    sofia = usuario_id(admin, "bar.esquina")
    pedro = usuario_id(admin, "cocina.esquina")
    admin.data("/usuario/pin", {"usuario_id": sofia, "pin": "2468"})
    admin.data("/usuario/pin", {"usuario_id": pedro, "pin": "1357"})

    sesion = Api(client).data("/dispositivo/pin", {"token": token, "pin": "2468"})
    assert sesion["dispositivo"]["tipo"] == "produccion"
    # Pedro es de Cocina: no entra en la pantalla del Bar
    assert Api(client).post("/dispositivo/pin", {"token": token, "pin": "1357"}).status_code == 400


def test_pin_bloqueo_por_intentos_y_codigo_ajeno(client, esquina, napoli):
    admin, _ = esquina["admin.esquina"]
    _, token = emparejar(client, admin, nombre="Tablet Salón 2")
    codigos = [Api(client).post("/dispositivo/pin", {"token": token, "pin": "9090"}).status_code for _ in range(6)]
    assert codigos[:5] == [400] * 5 and codigos[5] == 429

    # Un dispositivo de otra empresa no reconoce los PIN de esta
    admin_napoli, _ = napoli["napoli"]
    _, token_napoli = emparejar(client, admin_napoli, nombre="Tablet Napoli")
    assert Api(client).post("/dispositivo/pin", {"token": token_napoli, "pin": "4821"}).status_code == 400

    # Un token inventado no sirve
    assert Api(client).post("/dispositivo/info", {"token": "x" * 40}).status_code == 401
