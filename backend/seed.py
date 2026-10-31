"""
Aplica las migraciones (Alembic), configura el aislamiento por empresa (RLS) y carga el catálogo fijo
del sistema (módulos, permisos y roles). Se puede ejecutar varias veces: no duplica lo que ya existe
y sincroniza los permisos de cada rol.

Uso:
    python seed.py                                   (tablas y catálogo)
    python seed.py --superadmin soporte --password "ClaveLarga123" --nombre "Soporte"
    python seed.py --demo                            (dos empresas de ejemplo para probar)
"""
import argparse
import json
import Models  # noqa: F401 (registra todas las tablas)
import os
from pathlib import Path
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy.orm import sessionmaker
from Config.db import admin_engine
from Utils import rls
from Models.modulo_model import ModuloModel
from Models.permiso_model import PermisoModel
from Models.rol_model import RolModel
from Models.rol_permiso_model import RolPermisoModel
from Models.usuario_model import UsuarioModel
from Models.usuario_rol_model import UsuarioRolModel
from Models.empresa_model import EmpresaModel
from Utils.catalogo import MODULOS, PERMISOS, ROLES
from Class.Auth import hash_password, validate_password

DEMO_PASSWORD = "demo1234"


def migrate():
    """ Lleva la base de datos a la última versión del esquema (ADR-025) """
    base = Path(__file__).resolve().parent
    config = AlembicConfig(str(base / "alembic.ini"))
    config.set_main_option("script_location", str(base / "migrations"))
    command.upgrade(config, "head")


def seed_catalog(db):
    for row in MODULOS:
        modulo = db.query(ModuloModel).filter(ModuloModel.codigo == row["codigo"]).first()
        if not modulo:
            db.add(ModuloModel(row))
        else:
            modulo.nombre, modulo.depende_de, modulo.obligatorio = row["nombre"], row["depende_de"], row["obligatorio"]

    for codigo, (nombre, modulo) in PERMISOS.items():
        permiso = db.query(PermisoModel).filter(PermisoModel.codigo == codigo).first()
        if not permiso:
            db.add(PermisoModel({"codigo": codigo, "nombre": nombre, "modulo": modulo}))
        else:
            permiso.nombre, permiso.modulo = nombre, modulo
    db.flush()

    permisos = {p.codigo: p.id for p in db.query(PermisoModel).all()}
    for row in ROLES:
        rol = db.query(RolModel).filter(RolModel.codigo == row["codigo"]).first()
        if not rol:
            rol = RolModel({"codigo": row["codigo"], "nombre": row["nombre"], "alcance": row["alcance"]})
            db.add(rol)
            db.flush()
        else:
            rol.nombre, rol.alcance = row["nombre"], row["alcance"]

        # Los roles son fijos en el MVP: sus permisos quedan exactamente como dice el catálogo
        deseados = {permisos[codigo] for codigo in row["permisos"]}
        actuales = {rp.permiso_id: rp for rp in db.query(RolPermisoModel).filter(RolPermisoModel.rol_id == rol.id).all()}
        for permiso_id, rol_permiso in actuales.items():
            if permiso_id not in deseados:
                db.delete(rol_permiso)
        for permiso_id in deseados - set(actuales):
            db.add(RolPermisoModel({"rol_id": rol.id, "permiso_id": permiso_id}))
    db.commit()


def create_superadmin(db, usuario: str, password: str, nombre: str):
    usuario = usuario.strip().lower()
    if db.query(UsuarioModel).filter(UsuarioModel.usuario == usuario).first():
        print(f"El usuario {usuario} ya existe.")
        return
    validate_password(password)
    user = UsuarioModel({"usuario": usuario, "nombre": nombre, "password": hash_password(password)})
    db.add(user)
    db.flush()
    rol = db.query(RolModel).filter(RolModel.codigo == "superadmin").first()
    db.add(UsuarioRolModel({"usuario_id": user.id, "rol_id": rol.id}))
    db.commit()
    print(f"Superadministrador {usuario} creado.")


def data_of(response):
    return json.loads(response.body)["data"]


def admin_ctx(empresa_id, restaurante_id):
    return {
        "empresa_id": empresa_id,
        "restaurante_id": restaurante_id,
        "usuario_id": None,
        "roles": ["admin_empresa"],
        "permisos": set(PERMISOS),
        "modulos": {"base", "pedidos", "caja", "facturacion", "inventario"},
        "zonas": None,
        "puntos": None,
    }


def demo_company(db, nombre, restaurante, admin, zonas, puntos_extra, categorias, personal, modificadores=(),
                 modulos=("pedidos",), facturacion=None, inventario=None, domicilios=None, pagos_linea=None,
                 cupones=(), cobro=None):
    """ Empresa de ejemplo armada con las mismas clases que usa la API """
    from Class.Plataforma import Plataforma
    from Class.Zona import Zona
    from Class.Mesa import Mesa
    from Class.PuntoProduccion import PuntoProduccion
    from Class.Categoria import Categoria
    from Class.Producto import Producto
    from Class.Usuario import Usuario
    from Class.Modificador import Modificador
    from Querys.zona import ZonaQuerys
    from Querys.punto_produccion import PuntoProduccionQuerys

    if db.query(EmpresaModel).filter(EmpresaModel.nombre_comercial == nombre).first():
        print(f"La empresa demo {nombre} ya existe.")
        return

    empresa = data_of(Plataforma(db, {"plataforma": True}).create_company({
        "nombre_comercial": nombre,
        "restaurante": restaurante,
        "modulos": list(modulos),
        "estado_contrato": "activo",
        "admin": {"usuario": admin, "nombre": f"Dueño {nombre}", "password": DEMO_PASSWORD},
    }))
    restaurante_id = empresa["restaurantes"][0]["id"]
    ctx = admin_ctx(empresa["id"], restaurante_id)

    puntos = {p.nombre: p.id for p in PuntoProduccionQuerys(db, ctx).list_puntos()}
    for punto in puntos_extra:
        puntos[punto["nombre"]] = data_of(PuntoProduccion(db, ctx).create(punto))["id"]

    zonas_existentes = {z.nombre: z for z in ZonaQuerys(db, ctx).list_zonas()}
    carta_id = zonas_existentes["Salón"].carta_id
    zona_ids = {}
    for zona in zonas:
        if zona["nombre"] in zonas_existentes:
            existente = zonas_existentes[zona["nombre"]]
            Zona(db, ctx).update({"zona_id": existente.id, **zona, "carta_id": carta_id,
                                  "punto_produccion_id": puntos["Cocina"]})
            zona_ids[zona["nombre"]] = existente.id
        else:
            zona_ids[zona["nombre"]] = data_of(Zona(db, ctx).create({
                **zona, "carta_id": carta_id, "punto_produccion_id": puntos["Cocina"]}))["id"]
        Mesa(db, ctx).create_batch({"zona_id": zona_ids[zona["nombre"]], "desde": 1,
                                    "hasta": zona["mesas"], "prefijo": zona["prefijo"]})

    # Grupos de modificadores y a qué categorías se aplican
    grupos_por_categoria = {}
    for grupo in modificadores:
        grupo_id = data_of(Modificador(db, ctx).create({
            "nombre": grupo["nombre"], "minimo": grupo["minimo"], "maximo": grupo["maximo"],
            "opciones": [{"nombre": n, "precio_extra": p} for n, p in grupo["opciones"]],
        }))["id"]
        for categoria in grupo["categorias"]:
            grupos_por_categoria.setdefault(categoria, []).append(grupo_id)

    for orden, (categoria, punto, productos) in enumerate(categorias, start=1):
        categoria_id = data_of(Categoria(db, ctx).create({
            "nombre": categoria, "orden": orden, "punto_produccion_id": puntos.get(punto)}))["id"]
        for producto_orden, (producto, precio, descripcion) in enumerate(productos, start=1):
            Producto(db, ctx).create({"categoria_id": categoria_id, "nombre": producto, "precio": precio,
                                      "descripcion": descripcion, "orden": producto_orden,
                                      "grupos": grupos_por_categoria.get(categoria, [])})

    for persona in personal:
        Usuario(db, ctx).create({
            "usuario": persona["usuario"],
            "nombre": persona["nombre"],
            "password": DEMO_PASSWORD,
            "roles": persona["roles"],
            "zonas": [zona_ids[z] for z in persona.get("zonas", [])],
            "puntos": [puntos[p] for p in persona.get("puntos", [])],
        })

    if facturacion:
        demo_facturacion(db, ctx, facturacion)
    if inventario:
        demo_inventario(db, ctx, inventario)
    if domicilios:
        demo_domicilios(db, ctx, domicilios)
    if pagos_linea:
        # Pasarela simulada en ambiente de pruebas: su página de pago es una pantalla de la propia aplicación
        from Class.PagoLinea import PagoLinea
        PagoLinea(db, ctx).save_config(pagos_linea)
    if cupones:
        from Class.Cupon import Cupon
        ctx = {**ctx, "modulos": set(ctx["modulos"]) | {"fidelizacion"}}
        for cupon in cupones:
            Cupon(db, ctx).save(dict(cupon))

    if cobro:
        # Cobro del servicio de ejemplo (doc 42): mensualidad y vencimiento relativo a hoy
        from Models.contrato_model import ContratoModel
        from datetime import timedelta
        from Utils.tools import jornada as hoy_de
        contrato = db.query(ContratoModel).filter(ContratoModel.restaurante_id == restaurante_id).first()
        contrato.mensualidad = cobro["mensualidad"]
        contrato.proximo_vencimiento = hoy_de() + timedelta(days=cobro["vence_en_dias"])
        db.commit()

    print(f"Empresa demo {nombre} creada. Usuarios: {admin}, " +
          ", ".join(p["usuario"] for p in personal) + f" (clave {DEMO_PASSWORD})")


def demo_domicilios(db, ctx, config):
    """ Zonas de envío con tarifa fija y domiciliarios; el primero con usuario para ver sus entregas """
    from Class.Domicilio import Domicilio
    from Models.usuario_model import UsuarioModel
    for zona in config["zonas"]:
        Domicilio(db, ctx).save_zone(zona)
    for domiciliario in config["domiciliarios"]:
        datos = dict(domiciliario)
        if datos.get("usuario"):
            datos["usuario_id"] = db.query(UsuarioModel).filter(UsuarioModel.usuario == datos.pop("usuario")).first().id
        Domicilio(db, ctx).save_courier(datos)
    if config.get("web"):
        Domicilio(db, ctx).save_web(config["web"])


def demo_facturacion(db, ctx, config):
    """ Impuestos, resoluciones y proveedor simulado de ejemplo. Los valores son de demostración:
        cada restaurante configura los suyos con su contador (doc 21A). """
    from Class.Impuesto import Impuesto
    from Class.Resolucion import Resolucion
    from Class.Facturacion import Facturacion
    for impuesto in config["impuestos"]:
        Impuesto(db, ctx).create(impuesto)
    for resolucion in config["resoluciones"]:
        Resolucion(db, ctx).create(resolucion)
    Facturacion(db, ctx).save_config({"proveedor": "simulado", "ambiente": "pruebas", "documento_defecto": "pos",
                                      "credenciales": {"modo": "aceptar"}, "activo": True})


def demo_inventario(db, ctx, config):
    """ Insumos con existencia inicial, recetas y una preparación. Costos de ejemplo. """
    from Class.Insumo import Insumo
    from Class.Inventario import Inventario
    from Class.Receta import Receta
    from Models.producto_model import ProductoModel
    from Models.opcion_modificador_model import OpcionModificadorModel
    ids = {}
    for nombre, categoria, unidad, costo, stock, minimo, presentaciones, preparacion in config["insumos"]:
        ids[nombre] = data_of(Insumo(db, ctx).create({
            "nombre": nombre, "categoria": categoria, "unidad": unidad, "stock_minimo": minimo,
            "es_preparacion": preparacion, "presentaciones": [{"nombre": n, "factor": f} for n, f in presentaciones],
        }))["id"]
        if stock and not preparacion:
            Inventario(db, ctx).entry({"insumo_id": ids[nombre], "cantidad": stock, "costo_unitario": costo,
                                       "motivo": "Inventario inicial"})
    for preparacion, rendimiento, lineas, producir in config["preparaciones"]:
        Receta(db, ctx).save({"insumo_id": ids[preparacion], "rendimiento": rendimiento,
                              "lineas": [{"insumo_id": ids[i], "cantidad": c} for i, c in lineas]})
        Inventario(db, ctx).produce({"insumo_id": ids[preparacion], "cantidad": producir})
    productos = {p.nombre: p.id for p in db.query(ProductoModel).filter(ProductoModel.restaurante_id == ctx["restaurante_id"])}
    for producto, lineas in config["recetas"].items():
        Receta(db, ctx).save({"producto_id": productos[producto], "rendimiento": 1, "lineas": [
            {"insumo_id": ids[i], "cantidad": c, "merma": m} for i, c, m in lineas]})
    opciones = {o.nombre: o.id for o in db.query(OpcionModificadorModel).filter(
        OpcionModificadorModel.restaurante_id == ctx["restaurante_id"])}
    for opcion, lineas in config["opciones"].items():
        Receta(db, ctx).save_option_supplies({"opcion_id": opciones[opcion],
                                              "lineas": [{"insumo_id": ids[i], "cantidad": c} for i, c in lineas]})
    if config.get("proveedores"):
        demo_compras(db, ctx, config, ids)


def demo_compras(db, ctx, config, ids):
    """ Proveedores con sus insumos, una orden pendiente por recibir y una compra de plaza """
    from Class.Proveedor import Proveedor
    from Class.Compra import Compra
    from Models.insumo_presentacion_model import InsumoPresentacionModel
    presentaciones = {(p.insumo_id, p.nombre): p.id for p in db.query(InsumoPresentacionModel).filter(
        InsumoPresentacionModel.restaurante_id == ctx["restaurante_id"])}
    proveedores = {}
    for proveedor in config["proveedores"]:
        datos = {k: v for k, v in proveedor.items() if k != "insumos"}
        proveedores[datos["nombre"]] = data_of(Proveedor(db, ctx).create(datos))["id"]
        Proveedor(db, ctx).save_supplies({"proveedor_id": proveedores[datos["nombre"]], "insumos": [
            {"insumo_id": ids[i], "presentacion_id": presentaciones.get((ids[i], p)), "preferido": True}
            for i, p in proveedor["insumos"]]})
    for compra in config["compras"]:
        lineas = [{"insumo_id": ids[i], "presentacion_id": presentaciones.get((ids[i], p)), "cantidad": c, "precio_unitario": precio}
                  for i, p, c, precio in compra["lineas"]]
        datos = {"proveedor_id": proveedores.get(compra.get("proveedor")), "proveedor_nombre": compra.get("plaza"),
                 "forma_pago": compra["forma_pago"], "lineas": lineas}
        if compra.get("rapida"):
            Compra(db, ctx).quick(datos)
        else:
            Compra(db, ctx).create({**datos, "solicitar": True})


def seed_demo(db):
    demo_company(
        db, "La Esquina",
        {"nombre": "La Esquina Centro", "tipo": "comida_rapida", "direccion": "Calle 10 # 5-20",
         "hora_inicio_jornada": "06:00"},
        "esquina",
        modulos=("pedidos", "caja", "facturacion", "inventario", "domicilios", "pagos_linea", "fidelizacion", "propinas"),
        cobro={"mensualidad": 250000, "vence_en_dias": 20},
        # Cupones de ejemplo (doc 25A): uno general, uno de domicilio y la plantilla del cupón de la próxima visita
        cupones=[
            {"codigo": "BIENVENIDO", "nombre": "Bienvenida", "descripcion": "10 % en tu primera compra", "tipo": "porcentaje",
             "valor": 10, "tope": 5000, "usos_por_cliente": 1},
            {"codigo": "DOMIGRATIS", "nombre": "Domicilio gratis", "descripcion": "Domicilio sin costo desde $25.000",
             "tipo": "envio", "canales": ["domicilio"], "monto_minimo": 25000},
            {"nombre": "Vuelve pronto", "descripcion": "$3.000 de descuento en tu próxima visita", "tipo": "valor",
             "valor": 3000, "monto_minimo": 15000, "plantilla": True, "emitir_desde": 20000, "dias_validez": 30},
        ],
        pagos_linea={"activo": True, "pasarela": "simulada", "ambiente": "pruebas", "permitir_propina": True,
                     "minutos_expiracion": 30, "credenciales": {"modo": "normal"}},
        domicilios={
            # Tarifa al cliente y pago al domiciliario por zona (doc 15B). Valores de ejemplo
            "zonas": [
                {"nombre": "Centro", "barrios": "Centro, La Candelaria, San Nicolás", "tarifa": 3000, "pago_domiciliario": 2500, "orden": 1},
                {"nombre": "Norte", "barrios": "Los Álamos, El Prado, Villa del Norte", "tarifa": 5000, "pago_domiciliario": 4000,
                 "pedido_minimo": 20000, "orden": 2},
                {"nombre": "Sur", "barrios": "La Esperanza, San Fernando", "tarifa": 4500, "pago_domiciliario": 3500, "orden": 3},
            ],
            "domiciliarios": [
                {"nombre": "Julián Moto", "codigo": "D01", "telefono": "3201112233", "vinculo": "propio", "usuario": "domi.esquina"},
                {"nombre": "Andrés Bici", "codigo": "D02", "telefono": "3204445566", "vinculo": "independiente"},
            ],
            # Pedidos del cliente por enlace o QR de domicilios, confirmados por quien despacha (doc 17A)
            "web": {"activo": True, "aprobacion": True, "mensaje": "Domicilios de 11:00 a. m. a 9:00 p. m. Tiempo estimado: 40 minutos."},
        },
        inventario={
            # nombre, categoría, unidad, costo por unidad base, existencia inicial, mínimo, presentaciones, preparación
            "insumos": [
                ("Pan de hamburguesa", "Panadería", "und", 900, 60, 20, [("Bolsa x 12", 12)], False),
                ("Pan de perro", "Panadería", "und", 700, 40, 15, [("Bolsa x 10", 10)], False),
                ("Carne de res molida", "Carnes", "g", 28, 8000, 2000, [("Paquete 1 kg", 1000)], False),
                ("Pechuga de pollo", "Carnes", "g", 22, 4000, 1000, [("Paquete 1 kg", 1000)], False),
                ("Salchicha americana", "Carnes", "und", 1200, 40, 10, [("Paquete x 20", 20)], False),
                ("Tocineta", "Carnes", "g", 45, 250, 300, [], False),
                ("Queso mozzarella", "Lácteos", "g", 30, 2000, 500, [("Bloque 2,5 kg", 2500)], False),
                ("Huevo", "Lácteos", "und", 600, 30, 12, [("Panal x 30", 30)], False),
                ("Lechuga", "Verduras", "g", 6, 1500, 300, [], False),
                ("Tomate", "Verduras", "g", 5, 2000, 500, [], False),
                ("Papa", "Verduras", "g", 3, 10000, 3000, [("Bulto 25 kg", 25000)], False),
                ("Limón", "Verduras", "und", 300, 50, 20, [], False),
                ("Pulpa de mango", "Frutas", "g", 12, 2000, 500, [], False),
                ("Ajo", "Verduras", "g", 20, 200, 50, [], False),
                ("Mayonesa", "Salsas", "g", 14, 3000, 1000, [("Galón 3,8 kg", 3800)], False),
                ("Aceite", "Abarrotes", "ml", 9, 5000, 1000, [("Garrafa 5 l", 5000)], False),
                ("Azúcar", "Abarrotes", "g", 4, 3000, 500, [("Bolsa 1 kg", 1000)], False),
                ("Cerveza nacional", "Bebidas", "und", 3200, 48, 12, [("Canasta x 30", 30)], False),
                ("Gaseosa 400 ml", "Bebidas", "und", 2000, 24, 12, [("Paca x 12", 12)], False),
                ("Agua sin gas", "Bebidas", "und", 1300, 6, 6, [("Paca x 24", 24)], False),
                ("Salsa de la casa", "Preparaciones", "g", 0, 0, 200, [], True),
            ],
            # preparación, rendimiento, ingredientes, cantidad a producir
            "preparaciones": [("Salsa de la casa", 1000, [("Mayonesa", 950), ("Ajo", 20)], 1000)],
            # producto: [(insumo, cantidad, merma %)]. Jugo de mango queda sin receta a propósito.
            "recetas": {
                "Hamburguesa clásica": [("Pan de hamburguesa", 1, 0), ("Carne de res molida", 150, 5), ("Queso mozzarella", 30, 0),
                                        ("Lechuga", 20, 10), ("Tomate", 30, 10), ("Salsa de la casa", 20, 0)],
                "Hamburguesa doble": [("Pan de hamburguesa", 1, 0), ("Carne de res molida", 300, 5), ("Queso mozzarella", 60, 0),
                                      ("Lechuga", 20, 10), ("Tomate", 30, 10), ("Salsa de la casa", 20, 0)],
                "Hamburguesa de pollo": [("Pan de hamburguesa", 1, 0), ("Pechuga de pollo", 160, 10), ("Lechuga", 20, 10),
                                         ("Salsa de la casa", 25, 0)],
                "Perro sencillo": [("Pan de perro", 1, 0), ("Salchicha americana", 1, 0), ("Papa", 30, 15), ("Salsa de la casa", 15, 0)],
                "Papas a la francesa": [("Papa", 250, 15), ("Aceite", 30, 0)],
                "Salchipapa": [("Papa", 300, 15), ("Salchicha americana", 1, 0), ("Aceite", 35, 0), ("Salsa de la casa", 20, 0)],
                "Limonada natural": [("Limón", 2, 0), ("Azúcar", 30, 0)],
                "Cerveza nacional": [("Cerveza nacional", 1, 0)],
                "Gaseosa 400 ml": [("Gaseosa 400 ml", 1, 0)],
                "Agua sin gas": [("Agua sin gas", 1, 0)],
            },
            "opciones": {
                "Queso extra": [("Queso mozzarella", 30)],
                "Tocineta": [("Tocineta", 40)],
                "Huevo": [("Huevo", 1)],
                "Sin tomate": [("Tomate", -30)],
            },
            "proveedores": [
                {"nombre": "Distribuidora Andina", "razon_social": "Distribuidora Andina SAS", "tipo_documento": "NIT",
                 "documento": "900456789-1", "contacto": "Marta Gómez", "whatsapp": "3104567890", "forma_pago": "credito",
                 "plazo_dias": 30, "dias_entrega": "Martes y viernes", "pedido_minimo": 150000,
                 "insumos": [("Carne de res molida", "Paquete 1 kg"), ("Pechuga de pollo", "Paquete 1 kg"),
                             ("Queso mozzarella", "Bloque 2,5 kg"), ("Tocineta", None), ("Salchicha americana", "Paquete x 20")]},
                {"nombre": "Fruver La Cosecha", "contacto": "Don Jairo", "whatsapp": "3157894561", "forma_pago": "contado",
                 "dias_entrega": "Todos los días", "insumos": [("Lechuga", None), ("Tomate", None), ("Papa", "Bulto 25 kg"),
                                                               ("Limón", None)]},
                {"nombre": "Bebidas del Valle", "telefono": "6023334455", "forma_pago": "credito", "plazo_dias": 15,
                 "dias_entrega": "Lunes", "insumos": [("Cerveza nacional", "Canasta x 30"), ("Gaseosa 400 ml", "Paca x 12"),
                                                      ("Agua sin gas", "Paca x 24")]},
            ],
            # Una orden por recibir y una compra de plaza ya registrada. Tocineta y agua quedan en su mínimo
            # para que la lista de compras sugerida tenga qué mostrar
            "compras": [
                {"proveedor": "Fruver La Cosecha", "forma_pago": "contado",
                 "lineas": [("Papa", "Bulto 25 kg", 1, 80000), ("Tomate", None, 4000, 5), ("Lechuga", None, 2000, 6)]},
                {"plaza": "Plaza de mercado", "forma_pago": "contado", "rapida": True,
                 "lineas": [("Limón", None, 30, 300), ("Ajo", None, 250, 20)]},
            ],
        },
        facturacion={
            "impuestos": [
                {"nombre": "Impuesto al consumo", "tipo": "consumo", "codigo": "04", "porcentaje": 8,
                 "vigente_desde": "2026-01-01", "por_defecto": True},
                {"nombre": "IVA", "tipo": "iva", "codigo": "01", "porcentaje": 19, "vigente_desde": "2026-01-01"},
            ],
            "resoluciones": [
                {"tipo_documento": "pos", "numero_resolucion": "DEMO-POS-2026", "prefijo": "POSE", "desde": 1,
                 "hasta": 5000, "vigente_desde": "2026-01-01", "vigente_hasta": "2027-12-31", "alerta_restantes": 200},
                {"tipo_documento": "factura", "numero_resolucion": "DEMO-FE-2026", "prefijo": "FE", "desde": 1,
                 "hasta": 1000, "vigente_desde": "2026-01-01", "vigente_hasta": "2027-12-31", "alerta_restantes": 50},
            ],
        },
        zonas=[
            {"nombre": "Salón", "modo_qr": "aprobacion", "mesas": 8, "prefijo": "Mesa", "orden": 1},
            {"nombre": "Terraza", "modo_qr": "libre", "mesas": 4, "prefijo": "Terraza", "orden": 2},
        ],
        puntos_extra=[{"nombre": "Bar", "tipo": "bar"}],
        categorias=[
            ("Hamburguesas", "Cocina", [
                ("Hamburguesa clásica", 18000, "Carne de res, queso, lechuga y tomate"),
                ("Hamburguesa doble", 26000, "Doble carne y doble queso"),
                ("Hamburguesa de pollo", 19000, "Pechuga apanada y salsa de la casa"),
            ]),
            ("Perros y papas", "Cocina", [
                ("Perro sencillo", 12000, "Salchicha americana, papa ripio y salsas"),
                ("Papas a la francesa", 7000, None),
                ("Salchipapa", 15000, None),
            ]),
            ("Bebidas", "Bar", [
                ("Limonada natural", 6000, None),
                ("Cerveza nacional", 7000, None),
                ("Jugo de mango", 7000, "En agua o en leche"),
            ]),
            ("Gaseosas", "Bar", [
                ("Gaseosa 400 ml", 4500, None),
                ("Agua sin gas", 3500, None),
            ]),
        ],
        modificadores=[
            {"nombre": "Término de la carne", "minimo": 1, "maximo": 1, "categorias": ["Hamburguesas"],
             "opciones": [("Medio", 0), ("Tres cuartos", 0), ("Bien asada", 0)]},
            {"nombre": "Adicionales", "minimo": 0, "maximo": 3, "categorias": ["Hamburguesas", "Perros y papas"],
             "opciones": [("Queso extra", 3000), ("Tocineta", 4000), ("Huevo", 2500)]},
            {"nombre": "Quitar ingredientes", "minimo": 0, "maximo": 3, "categorias": ["Hamburguesas"],
             "opciones": [("Sin cebolla", 0), ("Sin tomate", 0), ("Sin salsas", 0)]},
        ],
        personal=[
            {"usuario": "admin.esquina", "nombre": "Laura Admin", "roles": ["admin_restaurante"]},
            {"usuario": "mesero.salon", "nombre": "Carlos Mesero", "roles": ["mesero"], "zonas": ["Salón"]},
            {"usuario": "mesero.terraza", "nombre": "Ana Mesera", "roles": ["mesero"], "zonas": ["Terraza"]},
            {"usuario": "cocina.esquina", "nombre": "Pedro Cocina", "roles": ["cocina"], "puntos": ["Cocina"]},
            {"usuario": "bar.esquina", "nombre": "Sofía Bar", "roles": ["cocina"], "puntos": ["Bar"]},
            {"usuario": "caja.esquina", "nombre": "Marta Caja", "roles": ["cajero"]},
            {"usuario": "contador.esquina", "nombre": "Pedro Contador", "roles": ["contador"]},
            {"usuario": "domi.esquina", "nombre": "Julián Moto", "roles": ["domiciliario"]},
        ],
    )
    demo_company(
        db, "Pizzería Napoli",
        {"nombre": "Napoli Norte", "tipo": "restaurante", "hora_inicio_jornada": "10:00"},
        "napoli",
        zonas=[{"nombre": "Salón", "modo_qr": "libre", "mesas": 5, "prefijo": "Mesa", "orden": 1}],
        puntos_extra=[],
        categorias=[
            ("Pizzas", "Cocina", [
                ("Pizza margarita", 32000, "Tomate, mozzarella y albahaca"),
                ("Pizza napolitana", 36000, None),
            ]),
        ],
        personal=[
            {"usuario": "mesero.napoli", "nombre": "Luis Mesero", "roles": ["mesero"], "zonas": ["Salón"]},
            {"usuario": "cocina.napoli", "nombre": "Gina Cocina", "roles": ["cocina"], "puntos": ["Cocina"]},
        ],
    )
    # Plan Gestión (caja + inventario, sin pedidos): vende con el POS de mostrador (ADR-007). En mora para la demo.
    demo_company(
        db, "Panadería Dulce Trigo",
        {"nombre": "Dulce Trigo", "tipo": "panaderia", "hora_inicio_jornada": "05:00"},
        "trigo",
        modulos=("caja", "inventario"),
        zonas=[],
        puntos_extra=[],
        categorias=[
            ("Panes", None, [
                ("Pan francés", 600, None),
                ("Pan de bono", 2500, None),
                ("Croissant", 4500, "De mantequilla"),
            ]),
            ("Bebidas", None, [
                ("Café con leche", 3500, None),
                ("Chocolate", 4000, None),
            ]),
        ],
        personal=[{"usuario": "caja.trigo", "nombre": "Rosa Caja", "roles": ["cajero"]}],
        cobro={"mensualidad": 120000, "vence_en_dias": -3},
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--superadmin")
    parser.add_argument("--password")
    parser.add_argument("--nombre")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    if args.superadmin and not (args.password and args.nombre):
        parser.error("Para crear el superadministrador se necesitan --superadmin --password --nombre")

    migrate()
    tablas = rls.configurar(admin_engine, os.getenv("DB_APP_USER"), os.getenv("DB_APP_PASS"))
    print(f"Aislamiento por empresa (RLS) activo en {len(tablas)} tablas.")
    if not os.getenv("DB_APP_USER"):
        print("AVISO: sin DB_APP_USER la aplicación usa el dueño de las tablas y RLS no la limita.")
    db = sessionmaker(bind=admin_engine)()
    try:
        seed_catalog(db)
        print("Esquema al día y catálogo listo.")
        if args.superadmin:
            create_superadmin(db, args.superadmin, args.password, args.nombre)
        if args.demo:
            seed_demo(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
