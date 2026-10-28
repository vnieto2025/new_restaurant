from Querys.base import Querys
from Models.empresa_model import EmpresaModel
from Models.restaurante_model import RestauranteModel
from Models.usuario_model import UsuarioModel
from Models.rol_model import RolModel
from Utils.tools import CustomException


class PlataformaQuerys(Querys):

    def get_empresa(self, empresa_id):
        empresa = self.db.query(EmpresaModel).filter(EmpresaModel.id == int(empresa_id)).first()
        if not empresa:
            raise CustomException("La empresa no existe.", 404)
        return empresa

    def list_empresas(self):
        return self.db.query(EmpresaModel).order_by(EmpresaModel.id.asc()).all()

    def list_restaurantes(self, empresa_id):
        return self.db.query(RestauranteModel).filter(
            RestauranteModel.empresa_id == empresa_id
        ).order_by(RestauranteModel.id.asc()).all()

    def usuario_exists(self, usuario: str):
        return self.db.query(UsuarioModel).filter(UsuarioModel.usuario == usuario).first() is not None

    def get_rol(self, codigo: str):
        rol = self.db.query(RolModel).filter(RolModel.codigo == codigo).first()
        if not rol:
            raise CustomException(f"El rol {codigo} no existe. Ejecute seed.py.")
        return rol
