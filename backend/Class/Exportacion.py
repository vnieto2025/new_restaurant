from Utils.tools import Tools, CustomException, to_local
from Utils.archivos import generar_csv, generar_xlsx, respuesta_archivo
from Querys.exportacion import ExportacionQuerys, NOMBRES
from Class.Reporte import Reporte, CANALES

# Tope de seguridad del archivo: se avisa en vez de entregarlo recortado
MAX_FILAS = 100000
NOTA_HORAS = "Dato operativo, no es soporte laboral"  # RN-NOM-02

# Cada conjunto: qué es, con qué módulos aplica, qué permiso adicional pide y sus columnas (docs 26, 26B y 41).
# Sin "periodo" entrega el estado actual. Lo no contratado no se ofrece (doc 26, sección 9).
CONJUNTOS = {
    "ventas_productos": {
        "titulo": "Ventas por producto", "grupo": "Ventas", "periodo": True,
        "descripcion": "Unidades y valor de todos los productos vendidos, sin recortes.",
        "columnas": ["Producto", "Unidades", "Valor"],
    },
    "ordenes": {
        "titulo": "Órdenes en detalle", "grupo": "Ventas", "periodo": True, "modulos": ["pedidos"],
        "descripcion": "Una fila por ítem: orden, canal, mesa, mesero, producto, valor y estado.",
        "columnas": ["Jornada", "Orden", "Canal", "Zona", "Mesa", "Mesero", "Producto", "Cantidad", "Precio unitario", "Total", "Estado"],
    },
    "cancelaciones": {
        "titulo": "Cancelaciones y pérdidas", "grupo": "Ventas", "periodo": True, "modulos": ["pedidos"],
        "descripcion": "Ítems cancelados con su motivo.",
        "columnas": ["Jornada", "Orden", "Mesa", "Producto", "Cantidad", "Valor", "Tipo", "Motivo"],
    },
    "cuentas": {
        "titulo": "Cuentas cobradas y anuladas", "grupo": "Caja", "periodo": True, "modulos": ["caja"],
        "descripcion": "Subtotal, descuentos, envío, propina y total de cada cuenta.",
        "columnas": ["Jornada", "Cuenta", "Estado", "Pagada en", "Mesa", "Subtotal", "Descuento", "Descuento cupón",
                     "Envío", "Descuento envío", "Propina", "Total", "Pagado", "Cobrada por", "Motivo de anulación"],
    },
    "pagos": {
        "titulo": "Pagos recibidos", "grupo": "Caja", "periodo": True, "modulos": ["caja"],
        "descripcion": "Cada pago con su medio y referencia, para conciliar.",
        "columnas": ["Fecha y hora", "Jornada", "Cuenta", "Medio", "Monto", "Referencia", "Estado", "Registrado por"],
    },
    "documentos": {
        "titulo": "Documentos de venta", "grupo": "Contabilidad", "periodo": True, "modulos": ["facturacion"], "personal": True,
        "descripcion": "Documentos POS y facturas con base, impuestos y receptor.",
        "columnas": ["Jornada", "Tipo", "Prefijo", "Número", "Estado", "Receptor", "Tipo de documento", "Documento",
                     "Base", "Impuestos", "Descuento", "Propina", "Total", "CUFE"],
    },
    "compras": {
        "titulo": "Compras", "grupo": "Contabilidad", "periodo": True, "modulos": ["inventario"],
        "descripcion": "Compras a proveedores con su factura, forma de pago y valores.",
        "columnas": ["Fecha", "Número", "Proveedor", "Estado", "Forma de pago", "Factura del proveedor", "Total", "Recibido", "Impuestos"],
    },
    "movimientos": {
        "titulo": "Movimientos de inventario", "grupo": "Inventario", "periodo": True, "modulos": ["inventario"],
        "descripcion": "Entradas, consumos, mermas y ajustes con su costo.",
        "columnas": ["Fecha y hora", "Insumo", "Tipo", "Cantidad", "Costo unitario", "Costo total", "Existencia resultante", "Motivo", "Referencia"],
    },
    "existencias": {
        "titulo": "Existencias", "grupo": "Inventario", "modulos": ["inventario"],
        "descripcion": "Insumos con su existencia, mínimo y costo promedio de hoy.",
        "columnas": ["Insumo", "Código", "Categoría", "Unidad", "Existencia", "Mínimo", "Costo promedio", "Ubicación", "Activo"],
    },
    "productos": {
        "titulo": "Productos", "grupo": "Catálogo",
        "descripcion": "Catálogo con categoría, precio y estado.",
        "columnas": ["Producto", "Categoría", "Descripción", "Precio", "Agotado", "Activo"],
    },
    "clientes": {
        "titulo": "Clientes", "grupo": "Personas", "permiso": "clientes.exportar", "personal": True,
        "descripcion": "Contacto y autorizaciones. Los clientes anonimizados no se incluyen.",
        "columnas": ["Nombre", "Teléfono", "Correo", "Tipo de documento", "Documento", "Estado", "Datos autorizados el",
                     "Comercial autorizado el", "Comercial revocado el", "Última compra"],
    },
    "entregas": {
        "titulo": "Domicilios", "grupo": "Personas", "periodo": True, "modulos": ["domicilios"], "personal": True,
        "descripcion": "Entregas por zona y domiciliario, sin dirección ni teléfono del cliente.",
        "columnas": ["Jornada", "Orden", "Zona de envío", "Domiciliario", "Estado", "Tarifa", "Pago al domiciliario",
                     "Cobrado contra entrega", "Salida", "Entrega"],
    },
    "horas": {
        "titulo": "Horas trabajadas", "grupo": "Nómina", "periodo": True, "modulos": ["pedidos"], "permiso": "nomina.exportar", "personal": True,
        "descripcion": "Turnos por persona. Son datos operativos, no soportes laborales.",
        "columnas": ["Jornada", "Persona", "Inicio", "Fin", "Horas", "Cierre automático", "Nota"],
    },
    "liquidaciones": {
        "titulo": "Propinas y pagos a domiciliarios", "grupo": "Nómina", "periodo": True, "modulos": ["propinas", "domicilios"],
        "permiso": "nomina.exportar", "personal": True,
        "descripcion": "Líneas de liquidaciones aprobadas o pagadas.",
        "columnas": ["Tipo", "Desde", "Hasta", "Estado", "Persona", "Rol", "Horas", "Entregas", "Propinas", "Pago de entregas",
                     "Descuentos", "Ajustes", "Total", "Pagado el", "Medio de pago"],
    },
}
GRUPOS = ["Ventas", "Caja", "Contabilidad", "Inventario", "Catálogo", "Personas", "Nómina"]
# Qué módulo habilita cada tipo de liquidación
TIPOS_LIQUIDACION = {"propinas": "propinas", "domiciliarios": "domicilios"}


class Exportacion:
    """ Descarga de datos en formatos abiertos (docs 26 sección 8, 26B y 41). El archivo se arma en el servidor,
        cada descarga queda en auditoría y su contenido no se guarda en el registro de peticiones. """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = ExportacionQuerys(db, ctx, "caja" in ctx.get("modulos", set()))

    def catalog(self):
        grupos = []
        for grupo in GRUPOS:
            conjuntos = [{"clave": clave, "titulo": c["titulo"], "descripcion": c["descripcion"],
                          "periodo": c.get("periodo", False), "personal": c.get("personal", False)}
                         for clave, c in CONJUNTOS.items() if c["grupo"] == grupo and self.available(c)]
            if conjuntos:
                grupos.append({"nombre": grupo, "conjuntos": conjuntos})
        return self.tools.output(200, "Datos para descargar.", {"grupos": grupos})

    def generate(self, data: dict):
        clave, formato = data["conjunto"], data["formato"]
        conjunto = CONJUNTOS.get(clave)
        if not conjunto or not self.available(conjunto):
            raise CustomException("No tienes acceso a esos datos.", 403)

        con_periodo = conjunto.get("periodo", False)
        desde, hasta = Reporte(self.db, self.ctx).periodo(data) if con_periodo else (None, None)
        filas = getattr(self, f"rows_{clave}")(desde, hasta) if con_periodo else getattr(self, f"rows_{clave}")()
        if not filas:
            raise CustomException("No hay datos para descargar en ese periodo." if con_periodo else "Aún no hay datos para descargar.", 409)
        if len(filas) > MAX_FILAS:
            raise CustomException(f"Son más de {MAX_FILAS} filas. Elige un periodo más corto.", 409)

        contenido = generar_csv(conjunto["columnas"], filas) if formato == "csv" \
            else generar_xlsx(conjunto["titulo"], conjunto["columnas"], filas)
        self.querys.audit("datos_exportados", "exportacion", None, despues={
            "conjunto": clave, "formato": formato, "filas": len(filas),
            "desde": desde.isoformat() if desde else None, "hasta": hasta.isoformat() if hasta else None})
        return respuesta_archivo(f"{clave}_{desde}_{hasta}" if con_periodo else clave, formato, contenido)

    def available(self, conjunto):
        modulos = conjunto.get("modulos")
        if modulos and not set(modulos) & set(self.ctx.get("modulos", set())):
            return False
        return not conjunto.get("permiso") or conjunto["permiso"] in self.ctx.get("permisos", set())

    def nombres(self, tipo):
        return self.querys.nombres(NOMBRES[tipo])

    # Las fechas con hora salen en la hora del restaurante y sin zona: es lo que entiende una hoja de cálculo
    def local(self, valor):
        return to_local(valor, self.ctx.get("zona_horaria")).replace(tzinfo=None) if valor else None

    # ---- Filas de cada conjunto, en el orden de sus columnas ----

    def rows_ventas_productos(self, desde, hasta):
        return [list(fila) for fila in self.querys.por_producto(desde, hasta)]

    def rows_ordenes(self, desde, hasta):
        filas = self.querys.ordenes_items(desde, hasta)
        mesas, zonas = self.nombres("mesas"), self.nombres("zonas")
        meseros = self.querys.nombres_usuarios({o.mesero_id for _, o in filas if o.mesero_id})
        return [[o.jornada, o.numero, CANALES.get(o.canal, o.canal), zonas.get(o.zona_id), mesas.get(o.mesa_id), meseros.get(o.mesero_id),
                 i.nombre_producto, i.cantidad, i.precio_unitario, i.total, i.estado] for i, o in filas]

    def rows_cancelaciones(self, desde, hasta):
        mesas = self.nombres("mesas")
        return [[o.jornada, o.numero, mesas.get(o.mesa_id), i.nombre_producto, i.cantidad, i.total,
                 i.tipo_cancelacion or "cancelacion", i.motivo_cancelacion] for i, o in self.querys.cancelados(desde, hasta)]

    def rows_cuentas(self, desde, hasta):
        filas = self.querys.cuentas(desde, hasta)
        mesas = self.nombres("mesas")
        cajeros = self.querys.nombres_usuarios({c.cobrada_por for c in filas if c.cobrada_por})
        return [[c.jornada, c.numero, c.estado, self.local(c.pagada_en), mesas.get(c.mesa_id), c.subtotal, c.descuento, c.descuento_cupon,
                 c.envio, c.descuento_envio, c.propina, c.total, c.pagado, cajeros.get(c.cobrada_por), c.anulada_motivo] for c in filas]

    def rows_pagos(self, desde, hasta):
        filas = self.querys.pagos(desde, hasta)
        medios = self.nombres("medios")
        usuarios = self.querys.nombres_usuarios({p.usuario_id for p, _ in filas if p.usuario_id})
        return [[self.local(p.creado_en), c.jornada, c.numero, medios.get(p.medio_pago_id), p.monto, p.referencia, p.estado,
                 usuarios.get(p.usuario_id)] for p, c in filas]

    def rows_documentos(self, desde, hasta):
        return [[d.jornada, d.tipo, d.prefijo, d.numero, d.estado, d.receptor_nombre, d.receptor_tipo_documento, d.receptor_documento,
                 d.base, d.impuestos, d.descuento, d.propina, d.total, d.cufe] for d in self.querys.documentos(desde, hasta)]

    def rows_compras(self, desde, hasta):
        return [[c.fecha, c.numero, c.proveedor_nombre, c.estado, c.forma_pago, c.factura_proveedor, c.total, c.valor_recibido, c.impuestos]
                for c in self.querys.compras(desde, hasta)]

    def rows_movimientos(self, desde, hasta):
        insumos = self.nombres("insumos")
        return [[self.local(m.creado_en), insumos.get(m.insumo_id), m.tipo, m.cantidad, m.costo_unitario, m.costo_total, m.stock_resultante,
                 m.motivo, m.referencia] for m in self.querys.movimientos(desde, hasta, self.ctx.get("zona_horaria"))]

    def rows_existencias(self):
        return [[i.nombre, i.codigo, i.categoria, i.unidad, i.stock, i.stock_minimo, i.costo_promedio, i.ubicacion, i.activo]
                for i in self.querys.insumos()]

    def rows_productos(self):
        categorias = self.nombres("categorias")
        return [[p.nombre, categorias.get(p.categoria_id), p.descripcion, p.precio, p.agotado, p.activo] for p in self.querys.productos()]

    def rows_clientes(self):
        return [[c.nombre, c.telefono, c.correo, c.tipo_documento, c.documento, c.estado, self.local(c.datos_aceptado_en),
                 self.local(c.comercial_aceptado_en), self.local(c.comercial_revocado_en), c.ultima_compra] for c in self.querys.clientes()]

    def rows_entregas(self, desde, hasta):
        zonas, domiciliarios = self.nombres("zonas_envio"), self.nombres("domiciliarios")
        return [[o.jornada, o.numero, zonas.get(e.zona_envio_id), domiciliarios.get(e.domiciliario_id), e.estado, e.tarifa, e.pago_domiciliario,
                 e.monto_a_cobrar if e.contra_entrega else 0, self.local(e.salida_en), self.local(e.entregada_en)]
                for e, o in self.querys.entregas(desde, hasta)]

    def rows_horas(self, desde, hasta):
        filas = self.querys.turnos(desde, hasta)
        personas = self.querys.nombres_usuarios({t.usuario_id for t in filas})
        return [[t.jornada, personas.get(t.usuario_id), self.local(t.inicio), self.local(t.fin),
                 round((t.fin - t.inicio).total_seconds() / 3600, 2) if t.fin else None, t.cierre_automatico, NOTA_HORAS] for t in filas]

    def rows_liquidaciones(self, desde, hasta):
        modulos = self.ctx.get("modulos", set())
        tipos = [tipo for tipo, modulo in TIPOS_LIQUIDACION.items() if modulo in modulos]
        return [[l.tipo, l.desde, l.hasta, l.estado, f.nombre, f.rol, f.horas, f.entregas, f.propinas, f.pago_entregas, f.descuentos, f.ajustes,
                 f.total, self.local(f.pagado_en), f.medio_pago] for f, l in self.querys.liquidaciones(desde, hasta, tipos)]
