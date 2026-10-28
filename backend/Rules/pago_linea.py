from Rules.campo import campo


def origen(params):
    return [
        campo("string", "código QR", params.get("token"), False, limite={"min": 8, "max": 120}),
        campo("string", "seguimiento", params.get("seguimiento"), False, limite={"min": 8, "max": 120}),
    ]


RULES = {
    "/publico/pago/cuenta": origen,
    "/publico/pago/cupon": lambda p: origen(p) + [campo("string", "código del cupón", p["codigo"], limite={"min": 3, "max": 30})],
    "/publico/pago/crear": lambda p: origen(p) + [
        campo("int", "propina", p.get("propina"), False),
        campo("string", "clave de idempotencia", p["clave_idempotencia"], limite={"min": 8, "max": 80})],
    "/publico/pago/estado": lambda p: [campo("string", "pago", p["pago"], limite={"min": 8, "max": 120})],
    "/publico/pasarela/ver": lambda p: [campo("string", "referencia", p["referencia"], limite={"min": 4, "max": 40})],
    "/publico/pasarela/responder": lambda p: [
        campo("string", "referencia", p["referencia"], limite={"min": 4, "max": 40}),
        campo("opcion", "decisión", p["decision"], opciones=["aprobar", "rechazar"])],
    "/pago_linea/config/save": lambda p: [
        campo("string", "pasarela", p.get("pasarela"), False, limite={"min": 2, "max": 30}),
        campo("opcion", "ambiente", p.get("ambiente"), False, opciones=["pruebas", "produccion"]),
        campo("bool", "activo", p.get("activo"), False), campo("bool", "propina", p.get("permitir_propina"), False),
        campo("int", "minutos para pagar", p.get("minutos_expiracion"), False)],
    "/pago_linea/enlace": lambda p: [campo("int", "pedido", p["sesion_mesa_id"])],
    "/pago_linea/list": lambda p: [campo("date", "desde", p.get("desde"), False), campo("date", "hasta", p.get("hasta"), False)],
    "/pago_linea/reembolsar": lambda p: [
        campo("int", "pago en línea", p["intento_pago_id"]), campo("int", "monto", p.get("monto"), False),
        campo("string", "motivo", p["motivo"], limite={"min": 3, "max": 200})],
    "/pago_linea/conciliar": lambda p: [
        campo("int", "pago en línea", p["intento_pago_id"]), campo("date", "fecha de abono", p["fecha_abono"]),
        campo("int", "comisión", p.get("comision"), False),
        campo("string", "nota", p.get("nota"), False, limite={"min": 1, "max": 200})],
}
