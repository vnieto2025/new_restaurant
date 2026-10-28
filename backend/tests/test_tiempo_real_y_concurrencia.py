"""
Tiempo real y operaciones simultáneas (doc 17, sección 7):
reconexión, dos meseros en la misma mesa, dos envíos duplicados a la vez.
"""
import threading
from conftest import key, find, product_id, table
from Config.db import SessionLocal
from Utils.contexto import cargar_contexto
from Class.Orden import Orden
from Models.mesa_model import MesaModel
from Utils.tools import CustomException


def run_parallel(functions):
    results, errors = [None] * len(functions), []
    barrier = threading.Barrier(len(functions))

    def runner(index, function):
        db = SessionLocal()
        try:
            barrier.wait()
            results[index] = function(db)
        except Exception as ex:
            errors.append(ex)
        finally:
            db.close()

    threads = [threading.Thread(target=runner, args=(i, f)) for i, f in enumerate(functions)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results, errors


def events_for(ws, orden_id, cantidad):
    """ Lee avisos hasta juntar los de esta orden (otras pruebas pueden dejar comandas abiertas) """
    tipos = []
    while len(tipos) < cantidad:
        evento = ws.receive_json()
        if evento.get("orden_id") == orden_id:
            tipos.append(evento["tipo"])
    return tipos


def ctx_of(sesion):
    return cargar_contexto({"usuario_id": sesion["usuario"]["id"], "restaurante_id": sesion["restaurante"]["id"]})


def test_cocina_recibe_aviso_por_websocket(client, esquina):
    cocina, sesion_cocina = esquina["cocina.esquina"]
    mesero, sesion_mesero = esquina["mesero.salon"]
    admin, _ = esquina["admin.esquina"]
    punto = find(sesion_cocina["puntos"], nombre="Cocina")
    zona = find(sesion_mesero["zonas"], nombre="Salón")

    with client.websocket_connect(f"/ws?token={cocina.token}&canales=punto:{punto['id']}") as ws_cocina, \
            client.websocket_connect(f"/ws?token={mesero.token}&canales=zona:{zona['id']}") as ws_mesero:
        assert ws_cocina.receive_json()["tipo"] == "conectado"
        assert ws_mesero.receive_json()["tipo"] == "conectado"

        orden = mesero.data("/orden/create", {
            "mesa_id": table(mesero, "Mesa 8")["id"], "clave_idempotencia": key(),
            "items": [{"producto_id": product_id(admin, "Perro sencillo"), "cantidad": 1}]}, expect=201)

        evento = ws_cocina.receive_json()
        assert evento["tipo"] == "orden.nueva" and evento["orden_id"] == orden["id"]
        assert ws_mesero.receive_json()["orden_id"] == orden["id"]

        # La cocina pide el estado (eso confirma la recepción) y el mesero se entera
        kds = cocina.data("/cocina/comandas", {"punto_produccion_id": punto["id"]})
        tarjeta = find(kds["en_proceso"], orden_id=orden["id"])
        assert events_for(ws_mesero, orden["id"], 1) == ["comanda.recibida"]
        assert mesero.data("/orden/get", {"orden_id": orden["id"]})["comandas"][0]["recibida_en"]

        cocina.data("/cocina/abrir", {"comanda_id": tarjeta["id"]})
        cocina.data("/cocina/despachar", {"comanda_id": tarjeta["id"]})
        tipos = events_for(ws_mesero, orden["id"], 2)
        assert tipos == ["comanda.abierta", "comanda.despachada"]

        ws_mesero.send_text("ping")
        assert ws_mesero.receive_text() == "pong"

    # Reconexión: los eventos son avisos; el estado completo se vuelve a pedir y está al día
    assert mesero.data("/orden/get", {"orden_id": orden["id"]})["estado"] == "lista"
    mesero.data("/orden/entregar", {"orden_id": orden["id"]})


def test_websocket_rechaza_token_invalido_y_canal_sin_permiso(client, esquina):
    mesero, _ = esquina["mesero.salon"]
    _, sesion_cocina = esquina["cocina.esquina"]
    punto = find(sesion_cocina["puntos"], nombre="Cocina")
    for url in ["/ws?token=falso&canales=ordenes", f"/ws?token={mesero.token}&canales=punto:{punto['id']}",
                f"/ws?token={mesero.token}&canales=ordenes"]:
        try:
            with client.websocket_connect(url) as ws:
                ws.receive_json()
            raise AssertionError(f"{url} no debió conectar")
        except AssertionError:
            raise
        except Exception:
            pass


def test_dos_meseros_agregan_items_a_la_vez(esquina):
    mesero, sesion = esquina["mesero.salon"]
    admin, sesion_admin = esquina["admin.esquina"]
    papas = product_id(admin, "Papas a la francesa")
    limonada = product_id(admin, "Limonada natural")
    orden = mesero.data("/orden/create", {"mesa_id": table(mesero, "Mesa 2")["id"], "clave_idempotencia": key(),
                                          "items": [{"producto_id": papas, "cantidad": 1}]}, expect=201)

    def agregar(ctx, producto):
        return lambda db: Orden(db, ctx).add_items({"orden_id": orden["id"], "clave_idempotencia": key(),
                                                    "items": [{"producto_id": producto, "cantidad": 1}]})

    _, errores = run_parallel([agregar(ctx_of(sesion), limonada), agregar(ctx_of(sesion_admin), papas)])
    assert errores == []

    final = mesero.data("/orden/get", {"orden_id": orden["id"]})
    assert len(final["items"]) == 3
    assert final["total"] == 7000 + 6000 + 7000
    assert sum(c["es_adicion"] for c in final["comandas"]) == 2


def test_dos_envios_simultaneos_con_la_misma_clave(esquina):
    _, sesion = esquina["mesero.terraza"]
    admin, _ = esquina["admin.esquina"]
    mesero, _ = esquina["mesero.terraza"]
    mesa_id = table(mesero, "Terraza 3")["id"]
    clave = key()
    items = [{"producto_id": product_id(admin, "Salchipapa"), "cantidad": 1}]
    ctx = ctx_of(sesion)

    def enviar(db):
        orden_class = Orden(db, ctx)
        mesa = orden_class.querys.get_own(MesaModel, mesa_id, "mesa", lock=True)
        orden, creada = orden_class.create_order(mesa=mesa, canal="tablet", items=items, clave=clave,
                                                 mesero_id=ctx["usuario_id"])
        return orden.id, creada

    resultados, errores = run_parallel([enviar, enviar, enviar])
    assert errores == []
    assert len({orden_id for orden_id, _ in resultados}) == 1
    assert sorted(creada for _, creada in resultados) == [False, False, True]


def test_ordenes_simultaneas_en_mesas_distintas_tienen_numeros_distintos(esquina):
    _, sesion = esquina["mesero.salon"]
    mesero, _ = esquina["mesero.salon"]
    admin, _ = esquina["admin.esquina"]
    ctx = ctx_of(sesion)
    gaseosa = product_id(admin, "Gaseosa 400 ml")
    mesas = [table(mesero, nombre)["id"] for nombre in ["Mesa 4", "Mesa 6", "Mesa 7"]]

    def enviar(mesa_id):
        def run(db):
            orden_class = Orden(db, ctx)
            mesa = orden_class.querys.get_own(MesaModel, mesa_id, "mesa", lock=True)
            orden, _ = orden_class.create_order(mesa=mesa, canal="tablet", clave=key(), mesero_id=ctx["usuario_id"],
                                                items=[{"producto_id": gaseosa, "cantidad": 1}])
            return orden.numero
        return run

    numeros, errores = run_parallel([enviar(m) for m in mesas])
    assert errores == []
    assert len(set(numeros)) == 3


def test_mesa_bloqueada_rechaza_ordenes(esquina):
    admin, _ = esquina["admin.esquina"]
    mesero, _ = esquina["mesero.salon"]
    mesa = table(admin, "Mesa 1")
    admin.data("/mesa/change_status", {"mesa_id": mesa["id"], "bloqueada": True})
    try:
        assert table(mesero, "Mesa 1")["estado"] == "bloqueada"
        response = mesero.post("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(),
                                                 "items": [{"producto_id": product_id(admin, "Salchipapa"), "cantidad": 1}]})
        assert response.status_code == 409
    finally:
        admin.data("/mesa/change_status", {"mesa_id": mesa["id"], "bloqueada": False})


def test_excepcion_de_negocio_no_deja_transaccion_rota(esquina):
    """ Tras un error de validación la siguiente petición funciona normal """
    mesero, _ = esquina["mesero.salon"]
    assert mesero.post("/orden/create", {"mesa_id": 999999, "clave_idempotencia": key(),
                                         "items": [{"producto_id": 1, "cantidad": 1}]}).status_code == 404
    assert mesero.post("/mesa/list").status_code == 200
    assert CustomException
