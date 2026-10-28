from Querys.base import Querys
from Utils.tools import CustomException
from Models.restaurante_model import RestauranteModel
from Models.contrato_model import ContratoModel
from Models.contrato_modulo_model import ContratoModuloModel
from Models.modulo_model import ModuloModel
from Models.sesion_mesa_model import SesionMesaModel


class RestauranteQuerys(Querys):

    def get_restaurante(self, restaurante_id=None):
        record = self.db.query(RestauranteModel).filter(
            RestauranteModel.id == (restaurante_id or self.restaurante_id)
        )
        if self.empresa_id:
            record = record.filter(RestauranteModel.empresa_id == self.empresa_id)
        record = record.first()
        if not record:
            raise CustomException("El restaurante no existe.", 404)
        return record

    def get_contrato(self, restaurante_id):
        return self.db.query(ContratoModel).filter(ContratoModel.restaurante_id == restaurante_id).first()

    def get_modulos_contrato(self, contrato_id):
        rows = self.db.query(ModuloModel.codigo).join(
            ContratoModuloModel, ContratoModuloModel.modulo_id == ModuloModel.id
        ).filter(ContratoModuloModel.contrato_id == contrato_id).order_by(ModuloModel.id.asc()).all()
        return [codigo for (codigo,) in rows]

    def get_modulos(self, codigos: list = None):
        query = self.db.query(ModuloModel)
        if codigos is not None:
            query = query.filter(ModuloModel.codigo.in_(codigos or [""]))
        return query.order_by(ModuloModel.id.asc()).all()

    # Reemplaza los módulos de un contrato por los indicados
    def set_modulos_contrato(self, contrato, modulos: list):
        self.db.query(ContratoModuloModel).filter(ContratoModuloModel.contrato_id == contrato.id).delete()
        for modulo in modulos:
            self.db.add(ContratoModuloModel({
                "empresa_id": contrato.empresa_id,
                "contrato_id": contrato.id,
                "modulo_id": modulo.id,
            }))
        self.db.flush()

    def count_sesiones_abiertas(self):
        return self.scoped(SesionMesaModel).filter(SesionMesaModel.estado == "abierta").count()

    def format_restaurante(self, record):
        contrato = self.get_contrato(record.id)
        return {
            "id": record.id,
            "empresa_id": record.empresa_id,
            "nombre": record.nombre,
            "tipo": record.tipo,
            "direccion": record.direccion,
            "telefono": record.telefono,
            "zona_horaria": record.zona_horaria,
            "hora_inicio_jornada": record.hora_inicio_jornada.strftime("%H:%M"),
            "moneda": record.moneda,
            "estado": record.estado,
            "mensaje_carta": record.mensaje_carta,
            "propina_sugerida": record.propina_sugerida,
            "reiniciar_agotados": record.reiniciar_agotados,
            "aviso_datos": record.aviso_datos,
            "aviso_version": record.aviso_version,
            "politica_url": record.politica_url,
            "contrato": {
                "id": contrato.id,
                "estado": contrato.estado,
                "fecha_inicio": contrato.fecha_inicio,
                "fecha_fin": contrato.fecha_fin,
                "modulos": self.get_modulos_contrato(contrato.id),
            } if contrato else None,
        }
