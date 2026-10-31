"""
Asistente de configuración inicial (doc 41, sección 2): cada paso se deduce de los datos reales, los manuales los
confirma una persona y el ensayo en vacío (RN-ONB-01) exige que lo obligatorio esté listo.
"""
from conftest import find, login


def paso(estado, clave):
    return find(estado["pasos"], clave=clave)


def test_un_restaurante_nuevo_avanza_paso_a_paso(client):
    soporte, _ = login(client, "soporte", "Soporte12345")
    soporte.data("/plataforma/empresa/create", {
        "nombre_comercial": "Asador Nuevo", "modulos": ["pedidos", "caja"], "estado_contrato": "activo",
        "admin": {"usuario": "dueno.asador", "nombre": "Dueño Asador", "password": "clave12345"},
        "restaurante": {"nombre": "Asador Centro"},
    }, expect=201)
    dueno, _ = login(client, "dueno.asador", "clave12345")

    estado = dueno.data("/restaurante/puesta_en_marcha")
    assert not estado["listo"] and estado["hechos"] < estado["total"]
    assert paso(estado, "cocina")["hecho"]  # viene creada con el restaurante
    for clave in ("datos", "mesas", "carta", "personal", "qr", "ensayo"):
        assert paso(estado, clave)["obligatorio"] and not paso(estado, clave)["hecho"], clave
    assert not paso(estado, "horario")["obligatorio"]
    assert not [p for p in estado["pasos"] if p["clave"] in ("impuestos", "domicilios")]  # módulos no contratados

    # El ensayo no se confirma con cosas pendientes, y dice cuáles
    rechazo = dueno.post("/restaurante/puesta_en_marcha/marcar", {"paso": "ensayo", "hecho": True})
    assert rechazo.status_code == 409 and "Carta" in rechazo.json()["message"]
    # Lo que se deduce de los datos no se puede marcar a mano
    assert dueno.post("/restaurante/puesta_en_marcha/marcar", {"paso": "carta", "hecho": True}).status_code == 400

    # Se completa por los caminos normales: no hay dos verdades
    dueno.data("/restaurante/update", {"nombre": "Asador Centro", "tipo": "restaurante", "direccion": "Calle 1 # 2-3", "telefono": "3001112233"})
    zona = find(dueno.data("/zona/list"), nombre="Salón")
    dueno.data("/mesa/create_lote", {"zona_id": zona["id"], "desde": 1, "hasta": 5, "prefijo": "Mesa"}, expect=201)
    categoria = dueno.data("/categoria/create", {"nombre": "Parrilla"}, expect=201)
    dueno.data("/producto/create", {"categoria_id": categoria["id"], "nombre": "Churrasco", "precio": 40000}, expect=201)
    dueno.data("/usuario/create", {"usuario": "mesero.asador", "nombre": "Mesero", "password": "clave12345", "roles": ["mesero"], "zonas": [zona["id"]]}, expect=201)
    dueno.data("/restaurante/puesta_en_marcha/marcar", {"paso": "qr", "hecho": True})

    estado = dueno.data("/restaurante/puesta_en_marcha")
    assert estado["hechos"] == estado["total"] - 1 and not estado["listo"]
    assert paso(estado, "qr")["marca"]["por"] == "Dueño Asador"

    estado = dueno.data("/restaurante/puesta_en_marcha/marcar", {"paso": "ensayo", "hecho": True})
    assert estado["listo"] and estado["hechos"] == estado["total"]
    assert any(r["accion"] == "puesta_en_marcha" for r in dueno.data("/auditoria/list", {"accion": "puesta_en_marcha"}))
    # Se puede reabrir
    assert not dueno.data("/restaurante/puesta_en_marcha/marcar", {"paso": "ensayo", "hecho": False})["listo"]
    dueno.data("/restaurante/puesta_en_marcha/marcar", {"paso": "ensayo", "hecho": True})


def test_se_adapta_a_los_modulos_y_a_los_permisos(client, esquina, napoli):
    admin, _ = esquina["admin.esquina"]
    estado = admin.data("/restaurante/puesta_en_marcha")
    assert estado["listo"]  # el restaurante demo ya está abierto
    assert {"impuestos", "domicilios"} <= {p["clave"] for p in estado["pasos"]}

    pizzeria, _ = napoli["napoli"]
    assert not pizzeria.data("/restaurante/puesta_en_marcha")["listo"]

    # Plan sin pedidos: nada de mesas ni QR, y el personal no es obligatorio
    trigo, _ = login(client, "trigo")
    plan = trigo.data("/restaurante/puesta_en_marcha")
    claves = {p["clave"] for p in plan["pasos"]}
    assert not {"mesas", "qr", "cocina", "dispositivos"} & claves and not paso(plan, "personal")["obligatorio"]

    caja, _ = esquina["caja.esquina"]
    assert caja.post("/restaurante/puesta_en_marcha").status_code == 403
    assert caja.post("/restaurante/puesta_en_marcha/marcar", {"paso": "qr", "hecho": True}).status_code == 403
