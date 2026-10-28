from Querys.base import Querys
from Models.qr_acceso_model import QrAccesoModel
from Models.mesa_model import MesaModel
from Models.zona_model import ZonaModel
from Models.restaurante_model import RestauranteModel
from Utils.tools import now


class QrQuerys(Querys):

    def get_active_by_mesa(self, mesa_id):
        return self.scoped(QrAccesoModel).filter(
            QrAccesoModel.mesa_id == mesa_id,
            QrAccesoModel.activo.is_(True),
        ).first()

    # Revoca el QR vigente de una mesa: el token deja de funcionar al instante (doc 10A, sección 3)
    def revoke_by_mesa(self, mesa_id):
        self.scoped(QrAccesoModel).filter(
            QrAccesoModel.mesa_id == mesa_id,
            QrAccesoModel.activo.is_(True),
        ).update({"activo": False, "revocado_en": now()}, synchronize_session=False)
        self.db.flush()

    def list_qr(self, zona_id=None):
        query = self.scoped(QrAccesoModel).join(
            MesaModel, MesaModel.id == QrAccesoModel.mesa_id
        ).join(
            ZonaModel, ZonaModel.id == QrAccesoModel.zona_id
        ).filter(
            QrAccesoModel.activo.is_(True),
            MesaModel.eliminado_en.is_(None),
            ZonaModel.eliminado_en.is_(None),
        ).add_columns(MesaModel, ZonaModel)
        if zona_id:
            query = query.filter(QrAccesoModel.zona_id == int(zona_id))
        rows = query.order_by(ZonaModel.orden.asc(), MesaModel.orden.asc(), MesaModel.id.asc()).all()
        return rows

    def get_restaurante_nombre(self):
        restaurante = self.db.query(RestauranteModel).filter(RestauranteModel.id == self.restaurante_id).first()
        return restaurante.nombre if restaurante else ""
