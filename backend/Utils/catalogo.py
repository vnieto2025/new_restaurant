"""
Catálogo fijo del sistema: módulos contratables, permisos y roles (docs 02A y 29).
Lo carga seed.py y lo usan los routers para declarar qué permiso y qué módulo exige cada ruta.
"""

# Módulos contratables (doc 02A, sección 3). Fase 0: base y pedidos.
MODULOS = [
    {"codigo": "base", "nombre": "Base", "depende_de": None, "obligatorio": True},
    {"codigo": "pedidos", "nombre": "Pedidos", "depende_de": "base", "obligatorio": False},
    {"codigo": "caja", "nombre": "Caja", "depende_de": "base", "obligatorio": False},
    {"codigo": "inventario", "nombre": "Inventario", "depende_de": "base", "obligatorio": False},
    {"codigo": "propinas", "nombre": "Propinas", "depende_de": "base,caja", "obligatorio": False},
    {"codigo": "domicilios", "nombre": "Domicilios", "depende_de": "pedidos", "obligatorio": False},
    {"codigo": "facturacion", "nombre": "Facturación electrónica", "depende_de": "caja", "obligatorio": False},
    {"codigo": "pagos_linea", "nombre": "Pagos en línea", "depende_de": "caja", "obligatorio": False},
    # Cupones (doc 25A); los puntos de fidelización quedan para la fase 3
    {"codigo": "fidelizacion", "nombre": "Cupones y fidelización", "depende_de": "caja", "obligatorio": False},
]

# Permisos: código -> (nombre, módulo)
PERMISOS = {
    "plataforma.gestionar": ("Gestionar empresas, restaurantes y contratos", "base"),
    "restaurante.configurar": ("Configurar el restaurante", "base"),
    "restaurante.pausar": ("Pausar o reanudar la recepción de órdenes", "base"),
    "usuarios.gestionar": ("Gestionar usuarios y roles asignados", "base"),
    "catalogo.gestionar": ("Gestionar productos, categorías y cartas", "base"),
    "catalogo.precios": ("Cambiar precios", "base"),
    "productos.agotar": ("Marcar producto agotado", "base"),
    "auditoria.ver": ("Ver auditoría", "base"),
    "reportes.ver": ("Ver reportes de ventas y por mesero", "base"),
    "reportes.propio": ("Ver su propio informe del día", "base"),
    "datos.exportar": ("Descargar datos en CSV o Excel", "base"),
    "nomina.exportar": ("Descargar horas, propinas y pagos a domiciliarios", "base"),
    "clientes.ver": ("Buscar clientes y ver sus datos de contacto", "base"),
    "clientes.gestionar": ("Editar, bloquear y anonimizar clientes", "base"),
    "clientes.exportar": ("Exportar los datos de un cliente", "base"),
    "impuestos.configurar": ("Configurar impuestos y tasas", "base"),
    "pagos_linea.configurar": ("Configurar la pasarela de pagos en línea", "pagos_linea"),
    "pagos_linea.cobrar": ("Enviar enlaces de pago en línea", "pagos_linea"),
    "pagos_linea.reembolsar": ("Reembolsar pagos en línea", "pagos_linea"),
    "pagos_linea.conciliar": ("Ver y conciliar los pagos en línea", "pagos_linea"),
    "liquidaciones.gestionar": ("Calcular, ajustar, aprobar y pagar liquidaciones de propinas", "propinas"),
    "liquidaciones.ver_propia": ("Ver su propia liquidación de propinas o entregas", "base"),
    "domicilios.liquidar": ("Liquidar el pago a domiciliarios", "domicilios"),
    "cupones.gestionar": ("Crear, pausar y enviar cupones", "fidelizacion"),
    "cupones.aplicar": ("Aplicar cupones al cobrar", "fidelizacion"),
    "cupones.ver": ("Ver los resultados de los cupones", "fidelizacion"),
    "notificaciones.configurar": ("Configurar los avisos por WhatsApp a clientes", "pedidos"),
    "notificaciones.enviar": ("Enviar los avisos por WhatsApp pendientes", "pedidos"),
    "estructura.gestionar": ("Gestionar zonas, mesas y puntos de producción", "pedidos"),
    "qr.gestionar": ("Descargar, revocar y regenerar QR", "pedidos"),
    "ordenes.ver": ("Ver órdenes y mesas", "pedidos"),
    "ordenes.crear_mesa": ("Crear orden en mesa", "pedidos"),
    "ordenes.crear_externa": ("Crear orden externa (mostrador)", "pedidos"),
    "ordenes.aprobar_qr": ("Aprobar o rechazar orden de QR", "pedidos"),
    "ordenes.agregar_items": ("Agregar ítems a orden enviada", "pedidos"),
    "ordenes.cancelar_nuevo": ("Cancelar ítem en nuevo", "pedidos"),
    "ordenes.cancelar_en_proceso": ("Cancelar ítem en proceso o posterior", "pedidos"),
    "ordenes.entregar": ("Marcar entregado", "pedidos"),
    "mesas.cerrar": ("Cerrar la sesión de una mesa", "pedidos"),
    "cocina.operar": ("Abrir y despachar comandas", "pedidos"),
    "cocina.reabrir": ("Reabrir comanda despachada", "pedidos"),
    "tirilla.imprimir": ("Imprimir y reimprimir tirillas", "pedidos"),
    "ordenes.pedir_cuenta": ("Pedir la cuenta de una mesa", "pedidos"),
    "mesas.trasladar": ("Trasladar y unir mesas", "pedidos"),
    "mesas.reasignar": ("Cambiar el mesero responsable de una mesa", "pedidos"),
    "caja.ver": ("Ver caja, cuentas y turnos", "caja"),
    "caja.turno": ("Abrir y cerrar turno de caja", "caja"),
    "caja.cobrar": ("Cobrar cuentas", "caja"),
    "caja.cobrar_externas": ("Cobrar cuentas de pedidos externos", "caja"),
    "caja.descuento": ("Aplicar descuento manual", "caja"),
    "caja.anular": ("Anular pagos y cuentas pagadas", "caja"),
    "caja.movimientos": ("Registrar gastos, retiros y aportes de caja", "caja"),
    "caja.cerrar_jornada": ("Cerrar la jornada", "caja"),
    "caja.medios": ("Configurar medios de pago", "caja"),
    "inventario.ver": ("Ver existencias, movimientos, recetas y costos", "inventario"),
    "inventario.gestionar": ("Gestionar insumos y recetas", "inventario"),
    "inventario.movimientos": ("Registrar entradas, mermas, ajustes y producción", "inventario"),
    "inventario.contar": ("Hacer conteos físicos", "inventario"),
    "compras.ver": ("Ver compras, proveedores e historial de precios", "inventario"),
    "compras.registrar": ("Registrar compras y órdenes de compra", "inventario"),
    "compras.recibir": ("Recibir mercancía de una compra", "inventario"),
    "compras.anular": ("Anular compras", "inventario"),
    "proveedores.gestionar": ("Gestionar proveedores", "inventario"),
    "domicilios.gestionar": ("Configurar zonas de envío y domiciliarios", "domicilios"),
    "domicilios.despachar": ("Asignar y seguir las entregas a domicilio", "domicilios"),
    "domicilios.entregar": ("Ver y actualizar sus propias entregas", "domicilios"),
    "domicilios.rendir": ("Recibir el efectivo que traen los domiciliarios", "domicilios"),
    "facturacion.ver": ("Ver documentos de venta", "facturacion"),
    "facturacion.facturar": ("Generar factura a nombre del cliente", "facturacion"),
    "facturacion.gestionar": ("Corregir y reenviar documentos rechazados", "facturacion"),
    "facturacion.configurar": ("Configurar resoluciones y proveedor de facturación", "facturacion"),
}

_OPERACION_MESERO = [
    "ordenes.ver", "ordenes.crear_mesa", "ordenes.aprobar_qr", "ordenes.agregar_items",
    "ordenes.cancelar_nuevo", "ordenes.entregar", "mesas.cerrar", "ordenes.pedir_cuenta", "reportes.propio",
    "liquidaciones.ver_propia",
]

_CAJERO = ["caja.ver", "caja.turno", "caja.cobrar", "caja.movimientos", "facturacion.ver", "facturacion.facturar",
           "domicilios.despachar", "domicilios.rendir", "notificaciones.enviar", "pagos_linea.cobrar",
           "cupones.aplicar", "liquidaciones.ver_propia"]

_ADMIN_RESTAURANTE = [
    "restaurante.configurar", "restaurante.pausar", "usuarios.gestionar", "catalogo.gestionar", "reportes.ver",
    "datos.exportar", "nomina.exportar", "clientes.ver", "clientes.gestionar", "clientes.exportar", "impuestos.configurar",
    "facturacion.gestionar", "facturacion.configurar",
    "inventario.ver", "inventario.gestionar", "inventario.movimientos", "inventario.contar",
    "compras.ver", "compras.registrar", "compras.recibir", "compras.anular", "proveedores.gestionar",
    "domicilios.gestionar", "notificaciones.configurar",
    "pagos_linea.configurar", "pagos_linea.reembolsar", "pagos_linea.conciliar",
    "cupones.gestionar", "cupones.ver", "liquidaciones.gestionar", "domicilios.liquidar",
    "catalogo.precios", "productos.agotar", "auditoria.ver", "estructura.gestionar", "qr.gestionar",
    "ordenes.crear_externa", "ordenes.cancelar_en_proceso", "cocina.reabrir", "tirilla.imprimir",
    "caja.descuento", "caja.anular", "caja.cerrar_jornada", "caja.medios", "mesas.trasladar", "mesas.reasignar",
] + _OPERACION_MESERO + _CAJERO

# Roles fijos (ADR-017). La matriz sale del doc 29.
ROLES = [
    {
        "codigo": "superadmin", "nombre": "Superadministrador de plataforma", "alcance": "plataforma",
        "permisos": ["plataforma.gestionar"],
    },
    {
        "codigo": "admin_empresa", "nombre": "Administrador de empresa", "alcance": "empresa",
        "permisos": [
            "restaurante.configurar", "usuarios.gestionar", "catalogo.gestionar", "catalogo.precios",
            "auditoria.ver", "estructura.gestionar", "qr.gestionar", "ordenes.ver", "caja.ver", "caja.medios", "reportes.ver",
            "datos.exportar", "nomina.exportar", "clientes.ver", "clientes.gestionar", "clientes.exportar", "impuestos.configurar", "facturacion.ver",
            "inventario.ver", "inventario.gestionar", "compras.ver", "proveedores.gestionar", "domicilios.gestionar",
        ],
    },
    {
        "codigo": "admin_restaurante", "nombre": "Administrador de restaurante", "alcance": "restaurante",
        "permisos": _ADMIN_RESTAURANTE,
    },
    {
        "codigo": "cajero", "nombre": "Cajero", "alcance": "restaurante",
        "permisos": [
            "ordenes.ver", "ordenes.crear_mesa", "ordenes.crear_externa", "ordenes.agregar_items",
            "ordenes.cancelar_nuevo", "ordenes.entregar", "mesas.cerrar", "productos.agotar",
            "tirilla.imprimir", "ordenes.pedir_cuenta", "mesas.trasladar", "clientes.ver",
        ] + _CAJERO,
    },
    {
        "codigo": "encargado_externos", "nombre": "Encargado de pedidos externos", "alcance": "restaurante",
        "permisos": [
            "ordenes.ver", "ordenes.crear_externa", "ordenes.agregar_items", "ordenes.cancelar_nuevo",
            "ordenes.entregar", "tirilla.imprimir", "caja.ver", "caja.cobrar_externas", "clientes.ver",
            "domicilios.despachar", "domicilios.rendir", "notificaciones.enviar", "pagos_linea.cobrar",
            "cupones.aplicar", "liquidaciones.ver_propia",
        ],
    },
    {
        "codigo": "mesero", "nombre": "Mesero", "alcance": "zona",
        "permisos": _OPERACION_MESERO,
    },
    {
        "codigo": "domiciliario", "nombre": "Domiciliario", "alcance": "restaurante",
        "permisos": ["domicilios.entregar", "liquidaciones.ver_propia"],
    },
    {
        "codigo": "cocina", "nombre": "Cocina / bar", "alcance": "punto",
        "permisos": ["cocina.operar", "cocina.reabrir", "productos.agotar", "tirilla.imprimir",
                     "inventario.movimientos", "inventario.contar", "compras.recibir",
                     "liquidaciones.ver_propia"],
    },
]

# Paquetes comerciales (doc 42, sección 2; doc 02A). Hipótesis a validar con los primeros clientes.
# El plan no se guarda: se deduce de los módulos del contrato, que son la fuente de verdad.
PLANES = [
    {"codigo": "pedidos", "nombre": "Pedidos", "modulos": ["pedidos"],
     "para": "Quien ya factura y lleva caja con otro sistema"},
    {"codigo": "gestion", "nombre": "Gestión", "modulos": ["caja", "inventario"],
     "para": "Panaderías, tiendas de comida y negocios de mostrador: venta directa sin mesas ni cocina"},
    {"codigo": "completo", "nombre": "Completo", "modulos": ["pedidos", "caja", "inventario", "facturacion", "propinas"],
     "para": "Restaurantes que quieren operar de punta a punta"},
]

# Se venden aparte, encima de un plan (doc 42, sección 2)
COMPLEMENTOS = ["facturacion", "domicilios", "pagos_linea", "fidelizacion"]


def plan_de(modulos) -> str:
    """ Código del plan que corresponde a unos módulos contratados, o "personalizado" """
    contratados = set(modulos or []) - {"base"}
    for plan in PLANES:
        nucleo = set(plan["modulos"])
        if nucleo <= contratados and not (contratados - nucleo - set(COMPLEMENTOS)):
            return plan["codigo"]
    return "personalizado"
