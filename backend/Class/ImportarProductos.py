import base64
import binascii
import re
from Utils.tools import Tools, CustomException, clean_text, normalize_text
from Utils.archivos import generar_xlsx, leer_tabla, respuesta_archivo
from Querys.producto import ProductoQuerys
from Models.producto_model import ProductoModel
from Models.categoria_model import CategoriaModel
from Models.punto_produccion_model import PuntoProduccionModel
from Models.impuesto_model import ImpuestoModel
from Class.Producto import MAX_PRECIO

MAX_ARCHIVO = 2 * 1024 * 1024
MAX_FILAS = 1000
COLUMNAS = {"producto": "Producto", "categoria": "Categoría", "precio": "Precio", "descripcion": "Descripción",
            "punto": "Punto de producción", "impuesto": "Impuesto"}
OBLIGATORIAS = ["producto", "categoria", "precio"]
EJEMPLO = [["Hamburguesa clásica", "Hamburguesas", 18000, "Carne de res, queso, lechuga y tomate", "Cocina", ""],
           ["Limonada natural", "Bebidas", 6000, "", "Bar", ""]]


def leer_precio(valor):
    """ Entero en pesos. Acepta lo que escribe una persona: 18000, 18.000, 18,000 o $ 18.000; no adivina decimales """
    if isinstance(valor, bool) or valor is None:
        return None
    if isinstance(valor, (int, float)):
        return int(valor) if float(valor).is_integer() else None
    texto = re.sub(r"[\s$]", "", str(valor))
    if re.fullmatch(r"\d+", texto):
        return int(texto)
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", texto):
        return int(re.sub(r"[.,]", "", texto))
    return None


class ImportarProductos:
    """ Carga de la carta desde una hoja de cálculo (docs 12 y 41). Primero se revisa sin guardar nada;
        al aplicar se vuelve a validar el mismo archivo y entra completo o no entra. """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = ProductoQuerys(db, ctx)

    def template(self):
        contenido = generar_xlsx("Productos", list(COLUMNAS.values()), EJEMPLO)
        return respuesta_archivo("plantilla_productos", "xlsx", contenido)

    def preview(self, data: dict):
        return self.tools.output(200, "Revisión del archivo.", self.summary(self.review(data)))

    def apply(self, data: dict):
        revision = self.review(data)
        resumen = self.summary(revision)
        if resumen["errores"]:
            raise CustomException(f"El archivo tiene {resumen['errores']} filas con errores. Corrígelas y súbelo de nuevo.", 409, resumen)
        if not resumen["crear"] and not resumen["actualizar"]:
            raise CustomException("No hay productos nuevos ni cambios para aplicar.", 409, resumen)

        categorias = dict(revision["categorias"])
        for nombre in revision["categorias_nuevas"]:
            categorias[nombre.lower()] = self.querys.insert_data(CategoriaModel, {"nombre": nombre}, commit=False)
        cartas = [carta.id for carta in self.querys.get_cartas()]
        for fila in revision["filas"]:
            campos = {"categoria_id": categorias[fila["categoria"].lower()], "precio": fila["precio"], "nombre": fila["producto"]}
            campos.update({k: fila[k] for k in ("descripcion", "punto_produccion_id", "impuesto_id") if fila.get(k)})
            if fila["accion"] == "crear":
                producto_id = self.querys.insert_data(ProductoModel, campos, commit=False)
                self.querys.set_cartas_producto(producto_id, cartas)
            elif fila["accion"] == "actualizar":
                existente = fila["existente"]
                if existente.precio != fila["precio"]:
                    self.querys.audit("precio_cambiado", "producto", existente.id, antes={"precio": existente.precio},
                                      despues={"precio": fila["precio"]}, commit=False)
                self.querys.update_data(ProductoModel, existente.id, campos, "producto", commit=False)
        self.querys.audit("productos_importados", "producto", None, despues={
            "archivo": clean_text(data["nombre"]), "creados": resumen["crear"], "actualizados": resumen["actualizar"],
            "categorias_nuevas": revision["categorias_nuevas"]}, commit=False)
        self.querys.commit()
        return self.tools.output(200, f"Importación lista. Nuevos: {resumen['crear']}. Actualizados: {resumen['actualizar']}.", resumen)

    def review(self, data: dict):
        filas_archivo = self.read_file(data)
        actualizar = data.get("existentes") == "actualizar"
        puede_precios = "catalogo.precios" in self.ctx.get("permisos", set())
        productos = {p.nombre.lower(): p for p in self.querys.scoped(ProductoModel, include_deleted=True).all()}
        categorias = {c.nombre.lower(): c.id for c in self.querys.scoped(CategoriaModel).all()}
        borradas = {c.nombre.lower() for c in self.querys.scoped(CategoriaModel, include_deleted=True).all()} - set(categorias)
        puntos = {p.nombre.lower(): p.id for p in self.querys.scoped(PuntoProduccionModel).all()}
        impuestos = {i.nombre.lower(): i.id for i in self.querys.scoped(ImpuestoModel).all()}

        filas, vistos, nuevas = [], set(), {}
        for numero, valores in filas_archivo:
            fila = {"fila": numero, "errores": [], "accion": "crear"}
            nombre = clean_text(valores.get("producto"))
            categoria = clean_text(valores.get("categoria"))
            fila["producto"], fila["categoria"] = nombre, categoria
            fila["descripcion"] = clean_text(valores.get("descripcion"))
            fila["precio"] = leer_precio(valores.get("precio"))

            if not nombre or not 2 <= len(nombre) <= 100:
                fila["errores"].append("El nombre debe tener de 2 a 100 caracteres.")
            elif nombre.lower() in vistos:
                fila["errores"].append("Este producto ya aparece en una fila anterior.")
            if not categoria or not 2 <= len(categoria) <= 60:
                fila["errores"].append("La categoría debe tener de 2 a 60 caracteres.")
            elif categoria.lower() in borradas:
                fila["errores"].append(f"La categoría {categoria} fue eliminada: usa otro nombre.")
            if fila["precio"] is None or fila["precio"] > MAX_PRECIO:
                fila["errores"].append("El precio debe ser un valor en pesos, sin decimales.")
            if fila["descripcion"] and len(fila["descripcion"]) > 500:
                fila["errores"].append("La descripción puede tener máximo 500 caracteres.")
            fila["punto_produccion_id"] = self.lookup(valores.get("punto"), puntos, "punto de producción", fila)
            fila["impuesto_id"] = self.lookup(valores.get("impuesto"), impuestos, "impuesto", fila)

            existente = productos.get(nombre.lower()) if nombre else None
            if existente is not None:
                if getattr(existente, "eliminado_en", None):
                    fila["errores"].append("Ya hubo un producto con este nombre y fue eliminado: usa otro nombre.")
                elif not actualizar:
                    fila["accion"] = "omitir"
                else:
                    fila["accion"], fila["existente"] = "actualizar", existente
                    fila["precio_anterior"] = existente.precio
                    if fila["precio"] is not None and fila["precio"] != existente.precio and not puede_precios:
                        fila["errores"].append("No tienes permiso para cambiar precios.")
            if nombre:
                vistos.add(nombre.lower())
            if not fila["errores"] and fila["accion"] != "omitir" and categoria.lower() not in categorias:
                nuevas.setdefault(categoria.lower(), categoria)
            filas.append(fila)
        return {"filas": filas, "categorias": categorias, "categorias_nuevas": list(nuevas.values())}

    def lookup(self, valor, opciones, etiqueta, fila):
        texto = clean_text(valor)
        if not texto:
            return None
        if texto.lower() not in opciones:
            fila["errores"].append(f"No existe el {etiqueta} {texto}.")
            return None
        return opciones[texto.lower()]

    def read_file(self, data: dict):
        nombre = str(data["nombre"]).lower()
        if not nombre.endswith((".xlsx", ".csv")):
            raise CustomException("El archivo debe ser Excel (.xlsx) o CSV.")
        archivo = str(data["archivo"])
        if len(archivo) > MAX_ARCHIVO * 4 / 3 + 4:
            raise CustomException("El archivo pesa más de 2 MB. Súbelo por partes.")
        try:
            contenido = base64.b64decode(archivo, validate=True)
        except (binascii.Error, ValueError):
            raise CustomException("No se pudo leer el archivo.")
        titulos, filas = leer_tabla(contenido, nombre.rsplit(".", 1)[1], MAX_FILAS)

        posiciones = {}
        alias = {normalize_text(titulo): clave for clave, titulo in COLUMNAS.items()}
        for posicion, titulo in enumerate(titulos):
            clave = alias.get(normalize_text(str(titulo))) if titulo is not None else None
            if clave and clave not in posiciones:
                posiciones[clave] = posicion
        faltan = [COLUMNAS[c] for c in OBLIGATORIAS if c not in posiciones]
        if faltan:
            raise CustomException(f"Al archivo le faltan las columnas: {', '.join(faltan)}. Usa la plantilla.")
        resultado = [(numero, {c: fila[p] if p < len(fila) else None for c, p in posiciones.items()}) for numero, fila in filas]
        if not resultado:
            raise CustomException("El archivo no tiene productos.")
        return resultado

    def summary(self, revision: dict):
        filas = revision["filas"]
        return {
            "total": len(filas),
            "crear": sum(1 for f in filas if not f["errores"] and f["accion"] == "crear"),
            "actualizar": sum(1 for f in filas if not f["errores"] and f["accion"] == "actualizar"),
            "omitir": sum(1 for f in filas if not f["errores"] and f["accion"] == "omitir"),
            "errores": sum(1 for f in filas if f["errores"]),
            "categorias_nuevas": revision["categorias_nuevas"],
            "filas": [{k: f.get(k) for k in ("fila", "producto", "categoria", "precio", "precio_anterior", "accion", "errores")} for f in filas],
        }
