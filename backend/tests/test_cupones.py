"""
Cupones (doc 25A): reglas validadas en el servidor con un mensaje que dice cuál falla, descuento que nunca deja la
cuenta en negativo, redención registrada que solo se revierte anulando la cuenta, cupón personal, cupón automático
para la próxima visita, aplicación desde el celular del cliente y resultados.
"""
from types import SimpleNamespace
import pytest
from conftest import Api, key, find, product_id, table, ensure_shift, qr_token, medio, pay_table
from Class.Cupon import descuento_de
from Utils.tools import CustomException


def cupon(**campos):
    base = {"tipo": "porcentaje", "valor": 10, "tope": None, "monto_minimo": 0, "productos": None, "categorias": None,
            "producto_id": None}
    return SimpleNamespace(**{**base, **campos})


LINEAS = [{"producto_id": 1, "categoria_id": 10, "cantidad": 2, "total": 12000},
          {"producto_id": 2, "categoria_id": 20, "cantidad": 1, "total": 7000}]


def test_calculo_del_descuento():
    assert descuento_de(cupon(), LINEAS, 0, 19000) == (1900, 0)
    assert descuento_de(cupon(tope=1000), LINEAS, 0, 19000) == (1000, 0)
    # Solo sobre la categoría elegida
    assert descuento_de(cupon(categorias=[20]), LINEAS, 0, 19000) == (700, 0)
    # Valor fijo: nunca más que lo disponible (RN-CUP-02)
    assert descuento_de(cupon(tipo="valor", valor=50000), LINEAS, 0, 19000) == (19000, 0)
    assert descuento_de(cupon(tipo="valor", valor=5000), LINEAS, 0, 3000) == (3000, 0)
    # Producto gratis: una unidad
    assert descuento_de(cupon(tipo="producto", valor=100, producto_id=1), LINEAS, 0, 19000) == (6000, 0)
    assert descuento_de(cupon(tipo="envio", valor=0), LINEAS, 4000, 19000) == (0, 4000)
    with pytest.raises(CustomException, match="faltan \\$1.000"):
        descuento_de(cupon(monto_minimo=20000), LINEAS, 0, 19000)
    with pytest.raises(CustomException, match="no tiene domicilio"):
        descuento_de(cupon(tipo="envio"), LINEAS, 0, 19000)
    with pytest.raises(CustomException, match="Postre y no está"):
        descuento_de(cupon(tipo="producto", producto_id=99), LINEAS, 0, 19000, "Postre")


def crear(admin, **campos):
    body = {"nombre": campos.pop("nombre", "Cupón de prueba"), "tipo": "porcentaje", "valor": 10, **campos}
    return admin.data("/cupon/save", body, expect=201)


def abrir(caja, admin, mesa, productos=(("Limonada natural", 2),)):
    mesa_id = table(caja, mesa)["id"]
    caja.data("/orden/create", {"mesa_id": mesa_id, "clave_idempotencia": key(), "items": [
        {"producto_id": product_id(admin, nombre), "cantidad": cantidad} for nombre, cantidad in productos]}, expect=201)
    return caja.data("/cuenta/abrir", {"mesa_id": mesa_id})


def cobrar(caja, cuenta):
    return caja.data("/cuenta/pagar", {"cuenta_id": cuenta["id"], "clave_idempotencia": key(), "pagos": [
        {"medio_pago_id": medio(caja, "Efectivo"), "monto": cuenta["saldo"]}]})


def mensaje(response):
    return response.json()["message"]


def test_aplicar_cobrar_agotar_y_revertir(esquina):
    admin, _ = esquina["admin.esquina"]
    caja, _ = esquina["caja.esquina"]
    mesero, _ = esquina["mesero.terraza"]
    ensure_shift(caja)
    nuevo = crear(admin, codigo="  bienvenida 10 ", nombre="Bienvenida", tope=1000, usos_maximos=1)
    assert nuevo["codigo"] == "BIENVENIDA10" and nuevo["estado_actual"] == "activo"
    # El código es único en el restaurante
    assert admin.post("/cupon/save", {"nombre": "Otro", "tipo": "valor", "valor": 1000, "codigo": "BIENVENIDA10"}).status_code == 409
    # Solo administración crea cupones; el mesero no los aplica (doc 29)
    assert caja.post("/cupon/save", {"nombre": "X", "tipo": "valor", "valor": 1, "codigo": "XYZ"}).status_code == 403

    cuenta = abrir(caja, admin, "Terraza 1")  # 2 limonadas = 12.000
    assert mesero.post("/cupon/aplicar", {"cuenta_id": cuenta["id"], "codigo": "BIENVENIDA10"}).status_code == 403
    assert "no existe" in mensaje(caja.post("/cupon/aplicar", {"cuenta_id": cuenta["id"], "codigo": "NOEXISTE"}))
    cuenta = caja.data("/cupon/aplicar", {"cuenta_id": cuenta["id"], "codigo": "bienvenida10"})
    assert cuenta["descuento_cupon"] == 1000 and cuenta["total"] == cuenta["subtotal"] - 1000
    assert cuenta["cupones"][0]["codigo"] == "BIENVENIDA10"
    assert "ya está aplicado" in mensaje(caja.post("/cupon/aplicar", {"cuenta_id": cuenta["id"], "codigo": "BIENVENIDA10"}))
    # La propina sugerida se calcula después del cupón
    assert cuenta["propina_sugerida"] == round((cuenta["subtotal"] - 1000) * cuenta["propina_porcentaje"] / 100)

    pagada = cobrar(caja, cuenta)
    assert pagada["estado"] == "pagada" and pagada["cupones"][0]["valor"] == 1000
    documento = admin.data("/documento/get", {"documento_id": pagada["documentos"][0]["id"]})
    assert documento["descuento"] == 1000 and documento["total"] == pagada["subtotal"] - 1000

    # Usos totales: el segundo uso se rechaza con el motivo (RN-CUP-01)
    otra = abrir(caja, admin, "Terraza 1")
    assert "máximo de veces" in mensaje(caja.post("/cupon/aplicar", {"cuenta_id": otra["id"], "codigo": "BIENVENIDA10"}))
    assert admin.data("/cupon/get", {"cupon_id": nuevo["id"]})["estado_actual"] == "agotado"

    # Anular la cuenta revierte la redención y el cupón vuelve a estar disponible (RN-CUP-03)
    admin.data("/cuenta/anular", {"cuenta_id": pagada["id"], "motivo": "Prueba de reversión"})
    detalle = admin.data("/cupon/get", {"cupon_id": nuevo["id"]})
    assert detalle["usos"] == 0 and detalle["redenciones"][0]["estado"] == "revertida"
    otra = caja.data("/cupon/aplicar", {"cuenta_id": otra["id"], "codigo": "BIENVENIDA10"})
    # Quitarlo antes de pagar lo libera; pagada la cuenta, ya no se quita
    otra = caja.data("/cupon/quitar", {"cuenta_id": otra["id"], "redencion_id": otra["cupones"][0]["redencion_id"]})
    assert otra["descuento_cupon"] == 0 and not otra["cupones"]
    cobrar(caja, otra)


def test_reglas_con_su_motivo(esquina):
    admin, _ = esquina["admin.esquina"]
    caja, _ = esquina["caja.esquina"]
    ensure_shift(caja)
    crear(admin, codigo="SOLODOMI", tipo="valor", valor=2000, canales=["domicilio"])
    crear(admin, codigo="MINIMO50", tipo="valor", valor=5000, monto_minimo=50000)
    crear(admin, codigo="PAUSADO1", tipo="valor", valor=1000)
    crear(admin, codigo="VENCIDO1", tipo="valor", valor=1000, inicia="2025-01-01", termina="2025-01-31")
    crear(admin, codigo="PAPASGRATIS", tipo="producto", producto_id=product_id(admin, "Papas a la francesa"))
    crear(admin, codigo="LIMON20", valor=20)
    pausado = find(admin.data("/cupon/list", {"buscar": "PAUSADO1"}), codigo="PAUSADO1")
    admin.data("/cupon/change_status", {"cupon_id": pausado["id"], "estado": "pausado"})

    cuenta = abrir(caja, admin, "Mesa 5")
    aplicar = lambda codigo: caja.post("/cupon/aplicar", {"cuenta_id": cuenta["id"], "codigo": codigo})  # noqa: E731
    assert "solo en domicilio" in mensaje(aplicar("SOLODOMI"))
    assert "compra mínima de $50.000" in mensaje(aplicar("MINIMO50"))
    assert "pausado" in mensaje(aplicar("PAUSADO1"))
    assert "venció el 31/01/2025" in mensaje(aplicar("VENCIDO1"))
    assert "Papas a la francesa y no está" in mensaje(aplicar("PAPASGRATIS"))

    caja.data("/cupon/aplicar", {"cuenta_id": cuenta["id"], "codigo": "LIMON20"})
    # No acumulable por defecto
    assert "no se pueden combinar" in mensaje(aplicar("PAPASGRATIS"))

    # Si la cuenta deja de cumplir, el cupón no descuenta y explica por qué; al pagar queda quitado
    caja.data("/orden/create", {"mesa_id": cuenta["mesa_id"], "clave_idempotencia": key(), "items": [
        {"producto_id": product_id(admin, "Papas a la francesa"), "cantidad": 1}]}, expect=201)
    cuenta = caja.data("/cuenta/get", {"cuenta_id": cuenta["id"]})
    assert cuenta["descuento_cupon"] == round(cuenta["subtotal"] * 0.2)

    # Descuento manual + cupón nunca dejan la cuenta en negativo (RN-CUP-02)
    cuenta = admin.data("/cuenta/ajustar", {"cuenta_id": cuenta["id"], "descuento": cuenta["subtotal"] - 1000,
                                            "descuento_motivo": "Prueba de tope"})
    assert cuenta["descuento_cupon"] == 1000 and cuenta["total"] == 0 + cuenta["propina"]
    admin.data("/cuenta/ajustar", {"cuenta_id": cuenta["id"], "descuento": 0})
    pay_table(caja, cuenta["mesa_id"])


def test_cupon_personal_y_cupon_automatico(esquina):
    admin, _ = esquina["admin.esquina"]
    caja, _ = esquina["caja.esquina"]
    ensure_shift(caja)
    ana = caja.data("/cliente/create", {"nombre": "Ana Cupones", "telefono": "3015550101", "acepta_datos": True,
                                        "acepta_comercial": True}, expect=201)
    beto = caja.data("/cliente/create", {"nombre": "Beto Cupones", "telefono": "3015550202", "acepta_datos": True},
                     expect=201)
    plantilla = admin.data("/cupon/save", {"nombre": "Vuelve pronto", "descripcion": "15 % en tu próxima visita",
                                           "tipo": "porcentaje", "valor": 15, "plantilla": True, "emitir_desde": 10000,
                                           "dias_validez": 15}, expect=201)
    assert plantilla["plantilla"] and plantilla["codigo"].startswith("AUTO-")

    # Ana compra 12.000 identificada al cobrar: se le emite su cupón para la próxima visita
    cuenta = abrir(caja, admin, "Terraza 1")
    cuenta = caja.data("/cupon/cliente", {"cuenta_id": cuenta["id"], "cliente_id": ana["id"]})
    assert cuenta["cliente"]["nombre"] == "Ana Cupones"
    pagada = cobrar(caja, cuenta)
    obsequio = pagada["cupon_obsequio"]
    assert obsequio and obsequio["descripcion"] == "15 % en tu próxima visita"
    # Una plantilla no se canjea directamente
    otra = abrir(caja, admin, "Terraza 1")
    assert "no existe" in mensaje(caja.post("/cupon/aplicar", {"cuenta_id": otra["id"], "codigo": plantilla["codigo"]}))

    # El cupón de Ana es personal (RN-CUP-04)
    assert "identifica al cliente" in mensaje(caja.post("/cupon/aplicar", {"cuenta_id": otra["id"], "codigo": obsequio["codigo"]}))
    assert "de otro cliente" in mensaje(caja.post("/cupon/aplicar", {"cuenta_id": otra["id"], "codigo": obsequio["codigo"],
                                                                      "cliente_id": beto["id"]}))
    otra = caja.data("/cupon/cliente", {"cuenta_id": otra["id"], "cliente_id": ana["id"]})
    assert [c["codigo"] for c in otra["cupones_cliente"]] == [obsequio["codigo"]]
    otra = caja.data("/cupon/aplicar", {"cuenta_id": otra["id"], "codigo": obsequio["codigo"]})
    assert otra["descuento_cupon"] == round(otra["subtotal"] * 0.15)
    # Si cambia el cliente, el cupón personal de Ana sale de la cuenta
    cambiada = caja.data("/cupon/cliente", {"cuenta_id": otra["id"], "cliente_id": beto["id"]})
    assert not cambiada["cupones"]
    otra = caja.data("/cupon/cliente", {"cuenta_id": otra["id"], "cliente_id": ana["id"]})
    otra = caja.data("/cupon/aplicar", {"cuenta_id": otra["id"], "codigo": obsequio["codigo"]})
    pagada_2 = cobrar(caja, otra)
    # Ya tenía un cupón emitido: al usarlo, esta compra le emite el siguiente
    assert pagada_2["cupon_obsequio"]["codigo"] != obsequio["codigo"]

    # Envío por WhatsApp solo con consentimiento comercial (RN-CLI-04)
    emitido = find(admin.data("/cupon/list", {"cliente_id": ana["id"]}), codigo=pagada_2["cupon_obsequio"]["codigo"])
    enviado = admin.data("/cupon/enviar", {"cupon_id": emitido["id"]})
    assert enviado["telefono"] == "573015550101" and emitido["codigo"] in enviado["mensaje"]
    personal_beto = crear(admin, nombre="Cortesía Beto", tipo="valor", valor=3000, cliente_id=beto["id"])
    assert len(personal_beto["codigo"]) == 8
    assert "no autorizó" in mensaje(admin.post("/cupon/enviar", {"cupon_id": personal_beto["id"]}))

    ficha = admin.data("/cliente/get", {"cliente_id": ana["id"]})
    assert any(u["codigo"] == obsequio["codigo"] for u in ficha["cupones"]["usados"])

    # Anular la cuenta que lo emitió anula el cupón obsequio si no se usó
    admin.data("/cuenta/anular", {"cuenta_id": pagada_2["id"], "motivo": "Prueba de anulación"})
    assert admin.data("/cupon/get", {"cupon_id": emitido["id"]})["estado"] == "anulado"
    admin.data("/cupon/change_status", {"cupon_id": plantilla["id"], "estado": "pausado"})


def test_cupon_desde_el_celular_y_envio_gratis(esquina, client):
    admin, _ = esquina["admin.esquina"]
    caja, _ = esquina["caja.esquina"]
    mesero, _ = esquina["mesero.terraza"]
    ensure_shift(caja)
    crear(admin, codigo="CELULAR5", tipo="valor", valor=500)
    publico = Api(client)
    mesero.data("/orden/create", {"mesa_id": table(mesero, "Terraza 2")["id"], "clave_idempotencia": key(), "items": [
        {"producto_id": product_id(admin, "Limonada natural"), "cantidad": 1}]}, expect=201)
    origen = {"token": qr_token(admin, "Terraza 2")}
    cuenta = publico.data("/publico/pago/cuenta", origen)
    assert cuenta["acepta_cupones"]
    aplicada = publico.data("/publico/pago/cupon", {**origen, "codigo": "celular5"})
    assert aplicada["saldo"] == cuenta["saldo"] - 500 and aplicada["cupones"][0]["codigo"] == "CELULAR5"
    detalle = caja.data("/cuenta/abrir", {"mesa_id": table(caja, "Terraza 2")["id"]})
    assert detalle["cupones"][0]["aplicado_por"] == "Cliente"
    # Con un pago en línea en curso no se cambia la cuenta
    publico.data("/publico/pago/crear", {**origen, "propina": 0, "clave_idempotencia": key()}, expect=201)
    crear(admin, codigo="CELULAR6", tipo="valor", valor=600, acumulable=True)
    assert "pago en línea en curso" in mensaje(publico.post("/publico/pago/cupon", {**origen, "codigo": "CELULAR6"}))
    # Probar muchos códigos desde el mismo dispositivo se frena
    for _ in range(8):
        publico.post("/publico/pago/cupon", {**origen, "codigo": "ADIVINA"})
    assert publico.post("/publico/pago/cupon", {**origen, "codigo": "ADIVINA"}).status_code == 429
    pay_table(caja, table(caja, "Terraza 2")["id"])

    # Envío gratis en un domicilio: el documento no factura el domicilio
    crear(admin, codigo="ENVIOGRATIS", nombre="Envío gratis", tipo="envio", canales=["domicilio"])
    zona = find(caja.data("/domicilio/zona/list"), nombre="Centro")
    externa = table(caja, "Para llevar", incluir_externa=True)
    orden = caja.data("/orden/create", {
        "mesa_id": externa["id"], "clave_idempotencia": key(), "cliente_nombre": "Cupón domicilio",
        "cliente_telefono": "3109990011", "items": [{"producto_id": product_id(admin, "Papas a la francesa"), "cantidad": 1}],
        "entrega": {"zona_envio_id": zona["id"], "direccion": "Calle 20 # 3-10", "barrio": "Centro"}}, expect=201)
    cuenta = caja.data("/cuenta/abrir", {"sesion_mesa_id": orden["sesion_mesa_id"]})
    cuenta = caja.data("/cupon/aplicar", {"cuenta_id": cuenta["id"], "codigo": "ENVIOGRATIS"})
    assert cuenta["descuento_envio"] == zona["tarifa"] and cuenta["total"] == cuenta["subtotal"] + cuenta["propina"]
    pagada = cobrar(caja, cuenta)
    documento = admin.data("/documento/get", {"documento_id": pagada["documentos"][0]["id"]})
    assert not any(l["descripcion"] == "Domicilio" for l in documento["lineas"])

    resultados = admin.data("/cupon/resultados", {})
    envio = find(resultados["por_cupon"], nombre="ENVIOGRATIS")
    assert envio["redenciones"] == 1 and envio["descuento"] == zona["tarifa"]
    assert resultados["resumen"]["redenciones"] >= 3 and resultados["resumen"]["ticket_con_cupon"] > 0
    assert find(resultados["por_usuario"], nombre="El cliente desde su celular")["redenciones"] == 1
    assert caja.post("/cupon/resultados", {}).status_code == 403
