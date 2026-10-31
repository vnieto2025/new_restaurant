from datetime import timedelta

# Qué puede hacer un restaurante según su contrato (doc 02A, sección 3; doc 06, sección 6)
COMPLETO = "completo"
LECTURA = "lectura"
EXPORTACION = "exportacion"

# Plazo para bajar los datos después de cancelar (doc 41, sección 6). Hipótesis hasta definirlo en el contrato
DIAS_EXPORTACION = 90
PERMISOS_EXPORTACION = {"datos.exportar", "nomina.exportar", "clientes.exportar"}

MENSAJES = {
    LECTURA: "El servicio de este restaurante está suspendido: puedes consultar y descargar tu información, "
             "pero no registrar cambios. Comunícate con soporte para reactivarlo.",
    EXPORTACION: "El contrato de este restaurante está cancelado: solo puedes descargar tus datos.",
}

RUTAS_SESION = {"/auth/sesion", "/auth/cambiar_password", "/auth/cambiar_restaurante"}
RUTAS_EXPORTACION = RUTAS_SESION | {"/exportacion/catalogo", "/exportacion/generar"}
# Lista cerrada: una ruta nueva queda bloqueada en solo lectura hasta que se agregue aquí a propósito
RUTAS_LECTURA = RUTAS_EXPORTACION | {
    "/auditoria/list",
    "/caja/estado", "/caja/jornada/estado", "/caja/medio_pago/list", "/caja/turno/get", "/caja/turno/list",
    "/carta/get", "/carta/list", "/categoria/list",
    "/cliente/buscar", "/cliente/exportar", "/cliente/get", "/cliente/list",
    "/cocina/comandas", "/cocina/tirilla",
    "/compra/get", "/compra/list", "/compra/sugerida",
    "/conteo/get", "/conteo/list",
    "/cuenta/get", "/cuenta/list", "/cuenta/pendientes",
    "/cupon/get", "/cupon/list", "/cupon/resultados",
    "/dispositivo/list",
    "/documento/get", "/documento/impuestos", "/documento/list",
    "/domicilio/domiciliario/list", "/domicilio/web/get", "/domicilio/zona/list",
    "/entrega/list", "/entrega/por_rendir",
    "/facturacion/config/get", "/facturacion/estado",
    "/horario/get", "/impuesto/list", "/insumo/list",
    "/inventario/estado", "/inventario/movimientos",
    "/liquidacion/config/get", "/liquidacion/get", "/liquidacion/list", "/liquidacion/mias", "/liquidacion/periodo",
    "/mesa/list", "/mesa/meseros", "/modificador/list",
    "/notificacion/config/get", "/notificacion/list", "/notificacion/pendientes",
    "/orden/carta", "/orden/get", "/orden/list", "/orden/tirilla",
    "/pago_linea/config/get", "/pago_linea/list",
    "/pos/carta", "/producto/list",
    "/proveedor/get", "/proveedor/insumos", "/proveedor/list",
    "/punto_produccion/list", "/qr/list",
    "/receta/costos", "/receta/get", "/receta/opcion/list",
    "/reporte/cancelaciones", "/reporte/dashboard", "/reporte/mesero", "/reporte/meseros", "/reporte/ventas",
    "/resolucion/list", "/restaurante/get", "/restaurante/plan", "/turno_mesero/actual",
    "/usuario/get", "/usuario/list", "/usuario/roles", "/zona/list",
}
RUTAS_POR_MODO = {LECTURA: RUTAS_LECTURA, EXPORTACION: RUTAS_EXPORTACION}


def acceso_de(empresa, contrato, hoy):
    """ Modo de acceso y, si está cancelado, hasta cuándo se pueden bajar los datos. Devuelve (modo, hasta);
        modo None significa que el plazo terminó y ya no hay acceso. La empresa pesa sobre todos sus restaurantes. """
    contrato_estado = contrato.estado if contrato else None
    if empresa.estado == "cancelada" or contrato_estado == "cancelado":
        fechas = [f for f in (empresa.cancelada_en if empresa.estado == "cancelada" else None,
                              contrato.cancelado_en if contrato_estado == "cancelado" else None) if f]
        hasta = min(fechas).date() + timedelta(days=DIAS_EXPORTACION) if fechas else None
        return (None if hasta and hoy > hasta else EXPORTACION), hasta
    vencido = bool(contrato and contrato.fecha_fin and contrato.fecha_fin < hoy)
    if empresa.estado == "suspendida" or contrato_estado == "suspendido" or vencido:
        return LECTURA, None
    return COMPLETO, None
