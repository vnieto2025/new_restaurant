from Utils.tools import Tools, CustomException
from Utils import imagenes
from Querys.base import Querys
from Models.restaurante_model import RestauranteModel

# Tamaño que se recomienda al subirlo: horizontal 3:1, se ve bien en la carta, la tirilla y el menú
TAMANO_SUGERIDO = "600 × 200 px"


class LogoRestaurante:
    """ Logo del restaurante (ADR-060): lo sube su administrador o soporte desde la consola de plataforma.
        Debe ser horizontal; se guarda comprimido en la carpeta del restaurante. """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = Querys(db, ctx)

    def restaurante(self, data: dict):
        # Soporte elige el restaurante; el administrador solo cambia el suyo
        restaurante_id = data.get("restaurante_id") if self.ctx.get("plataforma") else self.ctx["restaurante_id"]
        restaurante = self.db.query(RestauranteModel).filter(RestauranteModel.id == int(restaurante_id or 0)).with_for_update().first()
        if not restaurante:
            raise CustomException("El restaurante no existe.", 404)
        if restaurante.practica_de:
            raise CustomException("El logo se cambia en el restaurante real; la práctica usa el mismo.", 409)
        return restaurante

    # Queda en la auditoría del restaurante, también cuando lo cambia soporte
    def audit(self, restaurante, accion):
        Querys(self.db, {**self.ctx, "empresa_id": restaurante.empresa_id, "restaurante_id": restaurante.id}).audit(
            accion, "restaurante", restaurante.id, commit=False)

    def upload(self, data: dict):
        restaurante = self.restaurante(data)
        contenido = imagenes.comprimir(imagenes.decodificar(data["archivo"]), lado_maximo=800, horizontal=True)
        anterior = restaurante.logo
        restaurante.logo = imagenes.guardar(contenido, restaurante, "logo")
        self.audit(restaurante, "logo_cambiado")
        self.db.commit()
        imagenes.borrar(anterior)
        return self.tools.output(200, "Logo guardado.", {"logo": restaurante.logo, "peso": len(contenido)})

    def remove(self, data: dict):
        restaurante = self.restaurante(data)
        anterior = restaurante.logo
        restaurante.logo = None
        self.audit(restaurante, "logo_quitado")
        self.db.commit()
        imagenes.borrar(anterior)
        return self.tools.output(200, "Logo quitado.", {"logo": None})
