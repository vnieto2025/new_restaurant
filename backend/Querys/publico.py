from Querys.base import Querys
from Models.qr_acceso_model import QrAccesoModel
from Models.restaurante_model import RestauranteModel
from Models.empresa_model import EmpresaModel
from Models.zona_model import ZonaModel
from Models.mesa_model import MesaModel


class PublicoQuerys(Querys):
    """ Consultas sin sesión. El contexto (empresa, restaurante, zona, mesa) sale siempre
        del token del QR en el servidor, nunca de lo que envíe el cliente (doc 10A). """

    def resolve_token(self, token: str):
        qr = self.db.query(QrAccesoModel).filter(
            QrAccesoModel.token == token, QrAccesoModel.activo.is_(True)
        ).first()
        if not qr:
            return None
        return {
            "qr": qr,
            "empresa": self.db.get(EmpresaModel, qr.empresa_id),
            "restaurante": self.db.get(RestauranteModel, qr.restaurante_id),
            "zona": self.db.get(ZonaModel, qr.zona_id),
            "mesa": self.db.get(MesaModel, qr.mesa_id),
        }
