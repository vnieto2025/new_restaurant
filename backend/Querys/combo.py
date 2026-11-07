from Querys.base import Querys
from Models.producto_model import ProductoModel
from Models.combo_componente_model import ComboComponenteModel
from Models.combo_opcion_model import ComboOpcionModel


class ComboQuerys(Querys):
    """ Componentes de los combos y sus opciones (doc 12, sección 4) """

    def componentes_de(self, combo_ids: list):
        """ {combo_id: [componente con sus opciones]} en tres consultas; cada opción trae el estado de su producto """
        componentes = self.scoped(ComboComponenteModel).filter(ComboComponenteModel.combo_id.in_(combo_ids or [0])).order_by(
            ComboComponenteModel.orden, ComboComponenteModel.id).all()
        opciones = self.scoped(ComboOpcionModel).filter(
            ComboOpcionModel.componente_id.in_([c.id for c in componentes] or [0])).order_by(ComboOpcionModel.orden, ComboOpcionModel.id).all()
        productos = {p.id: p for p in self.scoped(ProductoModel, include_deleted=True).filter(
            ProductoModel.id.in_([o.producto_id for o in opciones] or [0])).all()}
        por_componente = {}
        for opcion in opciones:
            producto = productos[opcion.producto_id]
            por_componente.setdefault(opcion.componente_id, []).append({
                "producto_id": producto.id, "nombre": producto.nombre, "precio_extra": opcion.precio_extra,
                "disponible": producto.activo and not producto.agotado and producto.eliminado_en is None,
                "agotado": producto.agotado, "imagen": producto.imagen,
            })
        resultado = {}
        for componente in componentes:
            resultado.setdefault(componente.combo_id, []).append({
                "id": componente.id, "nombre": componente.nombre, "cantidad": componente.cantidad,
                "opciones": por_componente.get(componente.id, []),
            })
        return resultado

    def set_componentes(self, combo_id, componentes: list):
        """ Reemplaza los componentes. Las órdenes ya hechas no se afectan: guardan su propia copia de cada ítem """
        anteriores = [c.id for c in self.scoped(ComboComponenteModel).filter(ComboComponenteModel.combo_id == combo_id).all()]
        self.scoped(ComboOpcionModel).filter(ComboOpcionModel.componente_id.in_(anteriores or [0])).delete(synchronize_session=False)
        self.scoped(ComboComponenteModel).filter(ComboComponenteModel.combo_id == combo_id).delete(synchronize_session=False)
        for posicion, componente in enumerate(componentes):
            componente_id = self.insert_data(ComboComponenteModel, {"combo_id": combo_id, "nombre": componente["nombre"],
                                                                    "cantidad": componente["cantidad"], "orden": posicion}, commit=False)
            for orden, opcion in enumerate(componente["opciones"]):
                self.insert_data(ComboOpcionModel, {"componente_id": componente_id, "producto_id": opcion["producto_id"],
                                                    "precio_extra": opcion["precio_extra"], "orden": orden}, commit=False)
        self.db.flush()

    def combos_que_usan(self, producto_id):
        """ Nombres de los combos donde un producto es opción """
        filas = self.scoped(ComboOpcionModel).join(ComboComponenteModel, ComboComponenteModel.id == ComboOpcionModel.componente_id).join(
            ProductoModel, ProductoModel.id == ComboComponenteModel.combo_id).filter(
            ComboOpcionModel.producto_id == producto_id, ProductoModel.eliminado_en.is_(None)).with_entities(ProductoModel.nombre).distinct().all()
        return [nombre for (nombre,) in filas]
