from Querys.base import Querys
from Models.cliente_model import ClienteModel
from Models.cliente_direccion_model import ClienteDireccionModel
from Models.orden_model import OrdenModel
from Models.orden_item_model import OrdenItemModel
from Utils.estados import CANCELADO
from Utils.tools import normalize_text
from Utils.telefono import telefono_legible
from sqlalchemy import func, or_


class ClienteQuerys(Querys):

    def by_phone(self, telefono: str):
        return self.scoped(ClienteModel).filter(ClienteModel.telefono == telefono).first()

    def search(self, texto: str, limite=10):
        query = self.scoped(ClienteModel).filter(ClienteModel.anonimizado_en.is_(None))
        digitos = "".join(c for c in texto if c.isdigit())
        if digitos and len(digitos) >= 3:
            # Celular o documento de identidad (para la factura a su nombre)
            query = query.filter(or_(ClienteModel.telefono.like(f"%{digitos}%"), ClienteModel.documento.like(f"%{digitos}%")))
        else:
            needle = f"%{normalize_text(texto)}%"
            query = query.filter(or_(func.lower(ClienteModel.nombre).like(needle), func.lower(ClienteModel.correo).like(needle)))
        return query.order_by(ClienteModel.ultima_compra.desc().nullslast(), ClienteModel.nombre.asc()).limit(limite).all()

    def list_clientes(self, limite=50, offset=0):
        query = self.scoped(ClienteModel).filter(ClienteModel.anonimizado_en.is_(None))
        total = query.count()
        filas = query.order_by(ClienteModel.ultima_compra.desc().nullslast(), ClienteModel.id.desc()).offset(offset).limit(limite).all()
        return filas, total

    def direcciones(self, cliente_id):
        return self.scoped(ClienteDireccionModel).filter(
            ClienteDireccionModel.cliente_id == cliente_id, ClienteDireccionModel.activo.is_(True)
        ).order_by(ClienteDireccionModel.id.asc()).all()

    def ordenes(self, cliente_id, limite=None):
        query = self.scoped(OrdenModel).filter(OrdenModel.cliente_id == cliente_id).order_by(OrdenModel.id.desc())
        return query.limit(limite).all() if limite else query.all()

    def favoritos(self, cliente_id, limite=5):
        filas = self.scoped(OrdenItemModel).join(OrdenModel, OrdenModel.id == OrdenItemModel.orden_id).with_entities(
            OrdenItemModel.nombre_producto, func.sum(OrdenItemModel.cantidad)
        ).filter(OrdenModel.cliente_id == cliente_id, OrdenItemModel.estado != CANCELADO).group_by(
            OrdenItemModel.nombre_producto).order_by(func.sum(OrdenItemModel.cantidad).desc()).limit(limite).all()
        return [{"nombre": nombre, "unidades": int(unidades)} for nombre, unidades in filas]

    def total_gastado(self, cliente_id):
        valor = self.scoped(OrdenItemModel).join(OrdenModel, OrdenModel.id == OrdenItemModel.orden_id).with_entities(
            func.coalesce(func.sum(OrdenItemModel.total), 0)
        ).filter(OrdenModel.cliente_id == cliente_id, OrdenItemModel.estado != CANCELADO).scalar()
        return int(valor or 0)

    # Las órdenes conservan la venta, pero sin los datos personales (RN-CLI-05)
    def anonymize_orders(self, cliente_id):
        self.scoped(OrdenModel).filter(OrdenModel.cliente_id == cliente_id).update(
            {"cliente_nombre": None, "cliente_telefono": None}, synchronize_session=False)

    def delete_addresses(self, cliente_id):
        self.scoped(ClienteDireccionModel).filter(ClienteDireccionModel.cliente_id == cliente_id).delete(synchronize_session=False)

    def format_direccion(self, d):
        return {"id": d.id, "nombre": d.nombre, "direccion": d.direccion, "indicaciones": d.indicaciones, "barrio": d.barrio}

    def format_cliente(self, cliente, con_direcciones=True):
        data = {
            "id": cliente.id,
            "nombre": cliente.nombre,
            "telefono": cliente.telefono,
            "telefono_legible": telefono_legible(cliente.telefono),
            "correo": cliente.correo,
            "tipo_documento": cliente.tipo_documento,
            "documento": cliente.documento,
            "notas": cliente.notas,
            "estado": cliente.estado,
            "acepta_datos": cliente.datos_aceptado_en is not None,
            "acepta_comercial": cliente.comercial_aceptado_en is not None and cliente.comercial_revocado_en is None,
            "acepta_avisos": cliente.acepta_avisos,
            "ultima_compra": cliente.ultima_compra,
            "anonimizado": cliente.anonimizado_en is not None,
        }
        if con_direcciones:
            data["direcciones"] = [self.format_direccion(d) for d in self.direcciones(cliente.id)]
        return data
