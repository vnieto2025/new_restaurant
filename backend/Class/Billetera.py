from Utils.tools import Tools, CustomException, clean_text
from Utils.telefono import normalizar_telefono, telefono_legible
from Utils import imagenes
from Querys.base import Querys
from Models.billetera_model import BilleteraModel
from Models.restaurante_model import RestauranteModel

MAX_BILLETERAS = 6


def billeteras_publicas(db, restaurante_id) -> list:
    """ Lo que ve el cliente para pagar por billetera: solo las activas, sin ids internos """
    filas = db.query(BilleteraModel).filter(BilleteraModel.restaurante_id == restaurante_id, BilleteraModel.activo.is_(True)) \
        .order_by(BilleteraModel.orden, BilleteraModel.id).all()
    return [{"nombre": b.nombre, "telefono": telefono_legible(b.telefono) if b.telefono else None, "titular": b.titular,
             "qr": b.qr_imagen} for b in filas]


class Billetera:
    """ Billeteras digitales del restaurante (ADR-060): nombre, teléfono, titular y QR para que el cliente sepa
        cómo pagar. Solo informan; el cobro se registra en caja con su medio de pago. """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = Querys(db, ctx)

    def list(self, data: dict = None):
        filas = self.querys.scoped(BilleteraModel).order_by(BilleteraModel.orden, BilleteraModel.id).all()
        return self.tools.output(200, "Billeteras.", [self.format(b) for b in filas])

    def save(self, data: dict):
        nombre = clean_text(data["nombre"])
        telefono = normalizar_telefono(data.get("telefono")) if data.get("telefono") else None
        if not telefono and not data.get("qr_archivo") and not data.get("billetera_id"):
            raise CustomException("Pon el teléfono de la billetera, la imagen del QR o ambos.")
        fields = {"nombre": nombre, "telefono": telefono, "titular": clean_text(data.get("titular")),
                  "orden": int(data.get("orden") or 0), "activo": data.get("activo") is not False}
        if data.get("billetera_id"):
            billetera = self.querys.get_own(BilleteraModel, data["billetera_id"], "billetera")
        else:
            if self.querys.scoped(BilleteraModel).count() >= MAX_BILLETERAS:
                raise CustomException(f"Se pueden tener hasta {MAX_BILLETERAS} billeteras.")
            billetera = BilleteraModel(self.querys._with_tenant(BilleteraModel, fields))
            self.db.add(billetera)
        for campo, valor in fields.items():
            setattr(billetera, campo, valor)

        anterior = None
        if data.get("qr_archivo") or data.get("quitar_qr"):
            self.no_en_practica()
            anterior = billetera.qr_imagen
            billetera.qr_imagen = None
            if data.get("qr_archivo"):
                # Sin pérdida: un QR borroso no se puede leer
                contenido = imagenes.comprimir(imagenes.decodificar(data["qr_archivo"]), lado_maximo=800, sin_perdida=True)
                billetera.qr_imagen = imagenes.guardar(contenido, self.restaurante(), "billeteras")
        if not billetera.telefono and not billetera.qr_imagen:
            raise CustomException("Pon el teléfono de la billetera, la imagen del QR o ambos.")
        self.db.commit()
        # La anterior se borra solo con el cambio ya guardado
        imagenes.borrar(anterior)
        return self.tools.output(200, "Billetera guardada.", self.format(billetera))

    def delete(self, data: dict):
        billetera = self.querys.get_own(BilleteraModel, data["billetera_id"], "billetera")
        imagen = billetera.qr_imagen
        if imagen:
            self.no_en_practica()
        self.db.delete(billetera)
        self.db.commit()
        imagenes.borrar(imagen)
        return self.tools.output(200, "Billetera eliminada.")

    def restaurante(self):
        return self.db.get(RestauranteModel, self.ctx["restaurante_id"])

    # La práctica usa los mismos archivos del real: cambiarlos allí borraría los de verdad (ADR-053)
    def no_en_practica(self):
        if self.querys.en_practica:
            raise CustomException("Las imágenes se cambian en el restaurante real; la práctica usa las mismas.", 409)

    def format(self, billetera):
        return {"id": billetera.id, "nombre": billetera.nombre, "telefono": telefono_legible(billetera.telefono) if billetera.telefono else None,
                "titular": billetera.titular, "qr": billetera.qr_imagen, "orden": billetera.orden, "activo": billetera.activo}
