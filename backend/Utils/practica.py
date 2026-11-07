"""
Restaurante de práctica (ADR-053): una copia de la configuración del restaurante real para entrenar al
personal. Al ser otro restaurante, sus órdenes, cobros, inventario y reportes quedan aparte por la misma
separación por restaurante que ya aísla todo el sistema.

- clonar(): copia la configuración (carta, mesas, puntos, insumos y recetas, medios de pago...) con ids
  nuevos y las referencias entre tablas traducidas.
- limpiar(): borra todo lo del restaurante de práctica, para empezar de cero. Nunca toca uno real.
"""
from decimal import Decimal
from sqlalchemy import delete, select
from Config.db import BASE
from Utils.tools import now

# Lo que nunca se practica: facturación electrónica real ante la DIAN y cobros en línea reales
SIN_MODULOS = {"facturacion", "pagos_linea"}

# Configuración que se copia. Lo que pasa en la operación (órdenes, turnos, compras, avisos, auditoría)
# empieza vacío; la configuración de facturación, pagos en línea, avisos y domicilio web no se copia.
COPIAR = {
    "caja", "carta", "impuesto", "impuesto_tarifa", "punto_produccion", "medio_pago", "liquidacion_config",
    "zona", "zona_envio", "mesa", "qr_acceso", "horario", "domiciliario", "resolucion",
    "categoria", "producto", "carta_producto", "grupo_modificador", "opcion_modificador", "producto_grupo",
    "combo_componente", "combo_opcion",
    "insumo", "insumo_presentacion", "receta", "receta_linea", "opcion_insumo", "proveedor", "proveedor_insumo",
}
# Referencias que se conservan tal cual: son de la empresa o del sistema, no del restaurante
COMPARTIDAS = {"usuario", "empresa", "modulo", "rol", "permiso"}


def tablas_de_restaurante():
    return [t for t in BASE.metadata.sorted_tables if "restaurante_id" in t.columns]


def clonar(db, real_id: int, practica_id: int) -> dict:
    """ Copia la configuración del restaurante real al de práctica. Devuelve cuántas filas copió por tabla.
        Las existencias de los insumos se copian con un ajuste, así el inventario de práctica arranca igual. """
    from Class.Qr import new_token
    mapas, copiadas, existencias = {}, {}, {}
    for tabla in tablas_de_restaurante():
        if tabla.name not in COPIAR:
            continue
        mapa = mapas.setdefault(tabla.name, {})
        filas = db.execute(select(tabla).where(tabla.c.restaurante_id == real_id).order_by(tabla.c.id)).mappings().all()
        for fila in filas:
            datos = {k: v for k, v in fila.items() if k != "id"}
            datos["restaurante_id"] = practica_id
            for columna in tabla.columns:
                for fk in columna.foreign_keys:
                    destino = fk.column.table.name
                    if destino == "restaurante":
                        datos[columna.name] = practica_id
                    elif destino in COPIAR:
                        datos[columna.name] = mapas.get(destino, {}).get(fila[columna.name])
                    elif destino not in COMPARTIDAS:
                        datos[columna.name] = None
            if "creado_en" in datos:
                datos["creado_en"] = datos["actualizado_en"] = now()
            if tabla.name == "qr_acceso":
                datos["token"] = new_token()
            if tabla.name == "resolucion":
                datos["ultimo"] = None
            if tabla.name == "insumo":
                existencias[fila["id"]] = Decimal(str(fila["stock"] or 0))
                datos["stock"] = 0
            mapa[fila["id"]] = db.execute(tabla.insert().values(**datos).returning(tabla.c.id)).scalar_one()
        copiadas[tabla.name] = len(filas)
    return {"copiadas": copiadas, "existencias": {mapas["insumo"][k]: v for k, v in existencias.items() if v}}


def limpiar(db, restaurante) -> None:
    """ Borra todo lo del restaurante de práctica, de las tablas hijas a las padres. Los clientes creados
        en la práctica también se van. El restaurante en sí se conserva, así las sesiones abiertas siguen. """
    if not restaurante.practica_de:
        raise ValueError("Solo se limpia un restaurante de práctica")
    from Models.cliente_model import ClienteModel
    from Models.cliente_direccion_model import ClienteDireccionModel
    for tabla in reversed(tablas_de_restaurante()):
        db.execute(delete(tabla).where(tabla.c.restaurante_id == restaurante.id))
    clientes = select(ClienteModel.id).where(ClienteModel.practica_restaurante_id == restaurante.id)
    db.execute(delete(ClienteDireccionModel).where(ClienteDireccionModel.cliente_id.in_(clientes)))
    db.execute(delete(ClienteModel).where(ClienteModel.practica_restaurante_id == restaurante.id))
