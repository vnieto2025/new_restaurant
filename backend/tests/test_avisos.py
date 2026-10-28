"""
Avisos por WhatsApp (doc 31B): modo manual con enlace, modo automático por el proveedor con reintentos,
registro de cada aviso, eventos configurables, baja del cliente, límite diario y que nunca frenan la orden.
"""
import random
from conftest import key, find, product_id, table


def celular():
    return "31" + "".join(random.choice("0123456789") for _ in range(8))


def pedir(caja, admin, telefono=None, nombre="Ana Avisos", **extra):
    externa = table(caja, "Para llevar", incluir_externa=True)
    return caja.data("/orden/create", {"mesa_id": externa["id"], "clave_idempotencia": key(), "cliente_nombre": nombre,
                                       "cliente_telefono": telefono,
                                       "items": [{"producto_id": product_id(admin, "Papas a la francesa"), "cantidad": 1}],
                                       **extra}, expect=201)


def despachar(cocina, sesion, orden):
    punto = find(sesion["puntos"], nombre="Cocina")["id"]
    tarjeta = find(cocina.data("/cocina/comandas", {"punto_produccion_id": punto})["en_proceso"], orden_id=orden["id"])
    cocina.data("/cocina/abrir", {"comanda_id": tarjeta["id"]})
    cocina.data("/cocina/despachar", {"comanda_id": tarjeta["id"]})
    return tarjeta


def avisos_de(api, orden):
    return [a for a in api.data("/notificacion/list") if a["orden_id"] == orden["id"]]


def configurar(admin, **cambios):
    actual = admin.data("/notificacion/config/get")
    body = {"modo": actual["modo"], "proveedor": actual["proveedor"], "limite_diario": actual["limite_diario"],
            "eventos": {e["codigo"]: e["activo"] for e in actual["eventos"]}, "plantillas": {}}
    body.update(cambios)
    return admin.post("/notificacion/config/save", body)


def test_aviso_manual_de_orden_lista(esquina):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    cocina, sesion = esquina["cocina.esquina"]
    telefono = celular()
    orden = pedir(caja, admin, telefono, nombre="Ana María Avisos")
    assert avisos_de(admin, orden) == []  # la confirmación viene apagada por defecto

    tarjeta = despachar(cocina, sesion, orden)
    pendiente = find(caja.data("/notificacion/pendientes"), orden_id=orden["id"])
    assert pendiente["evento"] == "orden_lista" and pendiente["estado"] == "manual"
    assert pendiente["telefono"] == "57" + telefono
    assert pendiente["mensaje"] == f"Hola Ana, tu orden {orden['numero_texto']} en La Esquina Centro está lista para recoger."

    enviada = caja.data("/notificacion/enviada", {"notificacion_id": pendiente["id"]})
    assert enviada["estado"] == "enviada" and enviada["enviada_por"]
    assert not any(a["orden_id"] == orden["id"] for a in caja.data("/notificacion/pendientes"))

    # Reabrir y volver a despachar no repite el aviso
    cocina.data("/cocina/reabrir", {"comanda_id": tarjeta["id"], "motivo": "Faltó la salsa"})
    cocina.data("/cocina/despachar", {"comanda_id": tarjeta["id"]})
    assert len(avisos_de(admin, orden)) == 1


def test_sin_telefono_baja_y_limite_no_frenan_la_orden(esquina):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    cocina, sesion = esquina["cocina.esquina"]

    # Sin teléfono: la orden sigue y el aviso queda omitido con el motivo (RN-NOT-01, RN-NOT-05)
    sin_telefono = pedir(caja, admin, None)
    despachar(cocina, sesion, sin_telefono)
    [aviso] = avisos_de(admin, sin_telefono)
    assert aviso["estado"] == "omitida" and aviso["error"] == "Sin teléfono válido"

    # El cliente pidió no recibir avisos
    telefono = celular()
    cliente = caja.data("/cliente/create", {"nombre": "Sin Avisos", "telefono": telefono, "acepta_datos": True}, expect=201)
    admin.data("/cliente/update", {"cliente_id": cliente["id"], "nombre": "Sin Avisos", "telefono": telefono, "acepta_avisos": False})
    orden = pedir(caja, admin, telefono, nombre="Sin Avisos")
    despachar(cocina, sesion, orden)
    assert avisos_de(admin, orden)[0]["error"] == "El cliente pidió no recibir avisos"

    # Límite diario por teléfono
    try:
        assert configurar(admin, limite_diario=1).status_code == 200
        telefono = celular()
        primera, segunda = pedir(caja, admin, telefono), pedir(caja, admin, telefono)
        despachar(cocina, sesion, primera)
        despachar(cocina, sesion, segunda)
        assert avisos_de(admin, primera)[0]["estado"] == "manual"
        assert avisos_de(admin, segunda)[0]["error"].startswith("Límite diario")
    finally:
        configurar(admin, limite_diario=5)


def test_envio_automatico_con_reintentos_y_fallo(esquina):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]

    assert configurar(admin, plantillas={"orden_recibida": "Hola {cliente}"}).status_code == 400  # variable desconocida
    actual = admin.data("/notificacion/config/get")
    if not actual["tiene_credenciales"]:
        assert configurar(admin, modo="automatico").status_code == 400  # sin credenciales
    try:
        configurar(admin, modo="automatico", credenciales={"modo": "aceptar"},
                   eventos={"orden_recibida": True, "orden_lista": True, "domicilio_salio": True, "entrega_fallida": True},
                   plantillas={"orden_recibida": "Recibimos tu pedido {numero}, {nombre}."})
        config = admin.data("/notificacion/config/get")
        assert config["modo"] == "automatico" and config["tiene_credenciales"] and "credenciales" not in config

        orden = pedir(caja, admin, celular(), nombre="Pedro Auto")
        [aviso] = avisos_de(admin, orden)
        assert aviso["estado"] == "pendiente" and aviso["mensaje"] == f"Recibimos tu pedido {orden['numero_texto']}, Pedro."
        assert admin.data("/notificacion/procesar")["enviados"] >= 1
        assert avisos_de(admin, orden)[0]["estado"] == "enviada"

        # Proveedor caído: se reintenta con espera; no frena la orden
        configurar(admin, modo="automatico", credenciales={"modo": "caido"})
        caida = pedir(caja, admin, celular())
        admin.data("/notificacion/procesar")
        aviso = avisos_de(admin, caida)[0]
        assert aviso["estado"] == "pendiente" and aviso["intentos"] == 1 and "no responde" in aviso["error"]

        # Rechazado por el proveedor: queda fallido y aparece para avisar a mano
        configurar(admin, modo="automatico", credenciales={"modo": "rechazar"})
        rechazada = pedir(caja, admin, celular())
        admin.data("/notificacion/procesar")
        fallida = find(caja.data("/notificacion/pendientes"), orden_id=rechazada["id"])
        assert fallida["estado"] == "fallida"
        configurar(admin, modo="automatico", credenciales={"modo": "aceptar"})
        assert caja.data("/notificacion/reintentar", {"notificacion_id": fallida["id"]})["estado"] == "pendiente"
        admin.data("/notificacion/procesar")
        assert avisos_de(admin, rechazada)[0]["estado"] == "enviada"
        assert admin.data("/notificacion/prueba", {"telefono": "3001234567"})["referencia"].startswith("SIM-")
    finally:
        configurar(admin, modo="manual", eventos={"orden_recibida": False, "orden_lista": True, "domicilio_salio": True,
                                                  "entrega_fallida": True})
        for aviso in admin.data("/notificacion/list", {"estado": "pendiente"}):
            admin.data("/notificacion/descartar", {"notificacion_id": aviso["id"]})


def test_aviso_de_domicilio_en_camino(esquina):
    caja, _ = esquina["caja.esquina"]
    admin, _ = esquina["admin.esquina"]
    cocina, sesion = esquina["cocina.esquina"]
    centro = find(caja.data("/domicilio/zona/list"), nombre="Centro")
    orden = pedir(caja, admin, celular(), nombre="Lucía Casa",
                  entrega={"zona_envio_id": centro["id"], "direccion": "Calle 5 # 6-7"})
    despachar(cocina, sesion, orden)
    assert avisos_de(admin, orden) == []  # un domicilio no avisa "lista para recoger"
    entrega = next(e for e in caja.data("/entrega/list")["activas"] if e["orden_id"] == orden["id"])
    d02 = find(caja.data("/domicilio/domiciliario/list"), codigo="D02")
    caja.data("/entrega/asignar", {"entrega_id": entrega["id"], "domiciliario_id": d02["id"]})
    caja.data("/entrega/salir", {"entrega_id": entrega["id"]})
    [aviso] = avisos_de(admin, orden)
    assert aviso["evento"] == "domicilio_salio" and "ya va en camino" in aviso["mensaje"]


def test_permisos_de_avisos(esquina):
    caja, _ = esquina["caja.esquina"]
    mesero, _ = esquina["mesero.salon"]
    assert mesero.post("/notificacion/pendientes").status_code == 403
    assert caja.post("/notificacion/config/get").status_code == 403
    assert caja.post("/notificacion/list").status_code == 403
