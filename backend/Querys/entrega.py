from Querys.base import Querys
from Models.zona_envio_model import ZonaEnvioModel
from Models.domiciliario_model import DomiciliarioModel
from Models.entrega_model import EntregaModel
from Models.rendicion_model import RendicionModel
from Models.orden_model import OrdenModel


class EntregaQuerys(Querys):

    def zonas(self, incluir_inactivas=False):
        query = self.scoped(ZonaEnvioModel)
        if not incluir_inactivas:
            query = query.filter(ZonaEnvioModel.activo.is_(True))
        return query.order_by(ZonaEnvioModel.orden.asc(), ZonaEnvioModel.nombre.asc()).all()

    def domiciliarios(self, incluir_inactivos=False):
        query = self.scoped(DomiciliarioModel)
        if not incluir_inactivos:
            query = query.filter(DomiciliarioModel.activo.is_(True))
        return query.order_by(DomiciliarioModel.codigo.asc()).all()

    def domiciliario_de_usuario(self, usuario_id):
        return self.scoped(DomiciliarioModel).filter(DomiciliarioModel.usuario_id == usuario_id,
                                                     DomiciliarioModel.activo.is_(True)).first()

    def nombre_existe(self, model, campo, valor, exclude_id=None):
        query = self.scoped(model).filter(getattr(model, campo).ilike(valor))
        if exclude_id:
            query = query.filter(model.id != exclude_id)
        return query.first() is not None

    def entregas(self, estados=None, jornada=None, domiciliario_id=None):
        query = self.scoped(EntregaModel).join(OrdenModel, OrdenModel.id == EntregaModel.orden_id)
        if estados:
            query = query.filter(EntregaModel.estado.in_(estados))
        if jornada:
            query = query.filter(OrdenModel.jornada == jornada)
        if domiciliario_id:
            query = query.filter(EntregaModel.domiciliario_id == domiciliario_id)
        return query.order_by(EntregaModel.id.asc()).all()

    def en_camino_de(self, domiciliario_id):
        return self.scoped(EntregaModel).filter(EntregaModel.domiciliario_id == domiciliario_id,
                                                EntregaModel.estado == "en_camino").count()

    # Entregadas con cobro contra entrega que aún no se rinden en caja
    def por_rendir(self, domiciliario_id=None):
        query = self.scoped(EntregaModel).filter(EntregaModel.estado == "entregada", EntregaModel.contra_entrega.is_(True),
                                                 EntregaModel.rendicion_id.is_(None))
        if domiciliario_id:
            query = query.filter(EntregaModel.domiciliario_id == domiciliario_id)
        return query.order_by(EntregaModel.entregada_en.asc()).all()

    def rendiciones(self, jornada_desde=None, limite=50):
        query = self.scoped(RendicionModel)
        if jornada_desde:
            query = query.filter(RendicionModel.creado_en >= jornada_desde)
        return query.order_by(RendicionModel.id.desc()).limit(limite).all()
