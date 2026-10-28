from datetime import datetime, time, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo
from conftest import Api, key, find, product_id, table, qr_token
from Utils.horarios import en_franja, abierto, proxima_apertura

BOGOTA = ZoneInfo("America/Bogota")


def franja(dia, desde, hasta):
    return SimpleNamespace(dia_semana=dia, desde=time.fromisoformat(desde), hasta=time.fromisoformat(hasta), carta_id=None)


def test_franjas_que_cruzan_medianoche():
    viernes_noche = franja(4, "22:00", "02:00")
    assert en_franja(datetime(2026, 10, 23, 23, 30), viernes_noche)       # viernes 23:30
    assert en_franja(datetime(2026, 10, 24, 1, 59), viernes_noche)        # sábado 01:59
    assert not en_franja(datetime(2026, 10, 24, 2, 0), viernes_noche)     # sábado 02:00
    assert not en_franja(datetime(2026, 10, 23, 21, 59), viernes_noche)   # viernes antes de abrir
    assert abierto([], "America/Bogota")  # sin horario no hay restricción

    lunes = datetime(2026, 10, 26, 9, 0, tzinfo=BOGOTA)
    assert proxima_apertura([franja(0, "12:00", "15:00")], "America/Bogota", lunes) == "hoy a las 12:00"
    assert proxima_apertura([franja(1, "12:00", "15:00")], "America/Bogota", lunes) == "mañana a las 12:00"
    assert proxima_apertura([franja(4, "18:00", "23:00")], "America/Bogota", lunes) == "el viernes a las 18:00"


def ahora_local():
    return datetime.now(BOGOTA)


def franja_cerrada():
    """ Una franja de una hora que empieza dentro de 3 horas: ahora está cerrado """
    inicio = ahora_local() + timedelta(hours=3)
    fin = inicio + timedelta(hours=1)
    return {"dia_semana": inicio.weekday(), "desde": inicio.strftime("%H:00"), "hasta": fin.strftime("%H:00")}


def franja_abierta():
    """ Franja que cubre la hora actual de hoy """
    actual = ahora_local()
    inicio = actual - timedelta(hours=1)
    fin = actual + timedelta(hours=2)
    return {"dia_semana": inicio.weekday(), "desde": inicio.strftime("%H:00"), "hasta": fin.strftime("%H:00")}


def test_horario_de_zona_cierra_pedidos(client, esquina):
    admin, _ = esquina["admin.esquina"]
    mesero, _ = esquina["mesero.terraza"]
    terraza = find(admin.data("/zona/list"), nombre="Terraza")
    mesa = table(mesero, "Terraza 2")
    limonada = product_id(admin, "Limonada natural")

    admin.data("/horario/set", {"zona_id": terraza["id"], "tipo": "atencion", "franjas": [franja_cerrada()]})
    try:
        response = mesero.post("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(),
                                                 "items": [{"producto_id": limonada, "cantidad": 1}]})
        assert response.status_code == 409 and "Terraza no está atendiendo" in response.json()["message"]
        carta = Api(client).data("/publico/qr", {"token": qr_token(admin, "Terraza 2")})
        assert carta["disponible"] is False and "Abre" in carta["mensaje"]
    finally:
        admin.data("/horario/set", {"zona_id": terraza["id"], "tipo": "atencion", "franjas": []})

    mesero.data("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(),
                                  "items": [{"producto_id": limonada, "cantidad": 1}]}, expect=201)


def test_carta_por_franja(esquina):
    admin, _ = esquina["admin.esquina"]
    mesero, _ = esquina["mesero.terraza"]
    terraza = find(admin.data("/zona/list"), nombre="Terraza")
    jugo = product_id(admin, "Jugo de mango")
    desayuno = admin.data("/carta/create", {"nombre": "Desayunos", "productos": [jugo]}, expect=201)
    mesa = table(mesero, "Terraza 3")

    admin.data("/horario/set", {"zona_id": terraza["id"], "tipo": "carta",
                                "franjas": [{**franja_abierta(), "carta_id": desayuno["id"]}]})
    try:
        carta = mesero.data("/orden/carta", {"mesa_id": mesa["id"]})
        assert [p["nombre"] for c in carta["categorias"] for p in c["productos"]] == ["Jugo de mango"]
        response = mesero.post("/orden/create", {"mesa_id": mesa["id"], "clave_idempotencia": key(),
                                                 "items": [{"producto_id": product_id(admin, "Salchipapa"), "cantidad": 1}]})
        assert response.status_code == 409
    finally:
        admin.data("/horario/set", {"zona_id": terraza["id"], "tipo": "carta", "franjas": []})
    assert len(mesero.data("/orden/carta", {"mesa_id": mesa["id"]})["categorias"]) > 1


def test_horario_del_restaurante_y_validaciones(esquina):
    admin, _ = esquina["admin.esquina"]
    mesero, _ = esquina["mesero.salon"]
    assert admin.post("/horario/set", {"tipo": "atencion", "franjas": [{"dia_semana": 7, "desde": "08:00", "hasta": "10:00"}]}).status_code == 400
    assert admin.post("/horario/set", {"tipo": "atencion", "franjas": [{"dia_semana": 1, "desde": "08:00", "hasta": "08:00"}]}).status_code == 400
    assert admin.post("/horario/set", {"tipo": "carta", "franjas": []}).status_code == 400
    assert mesero.post("/horario/set", {"tipo": "atencion", "franjas": []}).status_code == 403

    semana = [{"dia_semana": d, "desde": "11:00", "hasta": "23:00"} for d in range(7)]
    guardado = admin.data("/horario/set", {"tipo": "atencion", "franjas": semana})
    assert len(guardado) == 7
    assert len(admin.data("/horario/get")["atencion"]) == 7
    admin.data("/horario/set", {"tipo": "atencion", "franjas": []})
