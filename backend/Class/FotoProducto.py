import base64
import binascii
from Utils.tools import Tools, CustomException
from Utils import imagenes
from Querys.producto import ProductoQuerys
from Models.producto_model import ProductoModel
from Models.restaurante_model import RestauranteModel


class FotoProducto:
    """ Foto opcional del producto (docs 11 y 12). La guardada es la comprimida; la original no se conserva. """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = ProductoQuerys(db, ctx)

    # La práctica usa los mismos archivos del real: cambiarlos o borrarlos allí dañaría las fotos de verdad
    def no_en_practica(self):
        if self.querys.en_practica:
            raise CustomException("Las fotos se cambian en el restaurante real; la práctica usa las mismas.", 409)

    def upload(self, data: dict):
        self.no_en_practica()
        producto = self.querys.get_own(ProductoModel, data["producto_id"], "producto")
        archivo = str(data["archivo"])
        if len(archivo) > imagenes.MAX_ARCHIVO * 4 / 3 + 4:
            raise CustomException("La foto pesa más de 6 MB.")
        try:
            contenido = base64.b64decode(archivo, validate=True)
        except (binascii.Error, ValueError):
            raise CustomException("El archivo no es una imagen válida.")
        comprimida = imagenes.comprimir(contenido)
        anterior = producto.imagen
        nueva = imagenes.guardar(comprimida, self.db.get(RestauranteModel, self.ctx["restaurante_id"]))
        try:
            self.querys.update_data(ProductoModel, producto.id, {"imagen": nueva}, "producto")
        except Exception:
            imagenes.borrar(nueva)
            raise
        # La anterior se borra solo con el cambio ya guardado
        imagenes.borrar(anterior)
        return self.tools.output(200, "Foto guardada.", {**self.querys.format_producto(producto), "peso": len(comprimida)})

    def remove(self, data: dict):
        self.no_en_practica()
        producto = self.querys.get_own(ProductoModel, data["producto_id"], "producto")
        anterior = producto.imagen
        self.querys.update_data(ProductoModel, producto.id, {"imagen": None}, "producto")
        imagenes.borrar(anterior)
        return self.tools.output(200, "Foto quitada.", self.querys.format_producto(producto))
