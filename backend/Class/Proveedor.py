from datetime import timedelta
from Utils.tools import Tools, CustomException, clean_text
from Querys.compra import CompraQuerys
from Querys.inventario import dec
from Models.proveedor_model import ProveedorModel, FORMAS_PAGO_PROVEEDOR
from Models.proveedor_insumo_model import ProveedorInsumoModel
from Models.insumo_model import InsumoModel
from Models.insumo_presentacion_model import InsumoPresentacionModel
from Class.Cliente import TIPOS_DOCUMENTO
from Class.Caja import dia_actual, validar_monto

MAX_INSUMOS = 200


class Proveedor:
    """ Directorio de proveedores, insumos que suministran e historial de precios (doc 24) """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = CompraQuerys(db, ctx)

    def list(self, data: dict):
        proveedores = self.querys.proveedores(data.get("todos") is True, clean_text(data.get("buscar")))
        totales = self.querys.totales_por_proveedor(dia_actual(self.ctx) - timedelta(days=90))
        result = []
        for proveedor in proveedores:
            fila = self.format(proveedor)
            fila["comprado_90_dias"], fila["compras_90_dias"] = totales.get(proveedor.id, (0, 0))
            fila["insumos"] = len(self.querys.insumos_de_proveedor(proveedor.id))
            result.append(fila)
        return self.tools.output(200, "Proveedores." if result else "Aún no hay proveedores.", result)

    def get(self, data: dict):
        proveedor = self.querys.get_own(ProveedorModel, data["proveedor_id"], "proveedor")
        result = self.format(proveedor)
        result["insumos"] = [self.format_supply(f) for f in self.querys.insumos_de_proveedor(proveedor.id)]
        result["insumos"].sort(key=lambda f: f["insumo"])
        result["precios"] = [self.format_price(linea, compra) for linea, compra in self.querys.historial_precios(proveedor.id)]
        from Class.Compra import Compra
        compras = Compra(self.db, self.ctx)
        result["compras"] = [compras.format_summary(c) for c in self.querys.compras(proveedor_id=proveedor.id, limite=20)]
        return self.tools.output(200, "Proveedor.", result)

    def create(self, data: dict):
        fields = self.clean_data(data)
        if self.querys.nombre_proveedor_existe(fields["nombre"]):
            raise CustomException("Ya existe un proveedor con ese nombre.")
        proveedor_id = self.querys.insert_data(ProveedorModel, fields)
        return self.tools.output(201, "Proveedor creado.", self.format(self.db.get(ProveedorModel, proveedor_id)))

    def update(self, data: dict):
        proveedor = self.querys.get_own(ProveedorModel, data["proveedor_id"], "proveedor")
        fields = self.clean_data(data)
        if self.querys.nombre_proveedor_existe(fields["nombre"], exclude_id=proveedor.id):
            raise CustomException("Ya existe otro proveedor con ese nombre.")
        self.querys.update_data(ProveedorModel, proveedor.id, fields, "proveedor")
        return self.tools.output(200, "Proveedor actualizado.", self.format(proveedor))

    # Un proveedor con compras no se borra: se inactiva y su historial queda (RN-PRV-01)
    def change_status(self, data: dict):
        proveedor = self.querys.get_own(ProveedorModel, data["proveedor_id"], "proveedor")
        activo = data["activo"] is True
        self.querys.update_data(ProveedorModel, proveedor.id, {"activo": activo}, "proveedor")
        return self.tools.output(200, "Proveedor activado." if activo else "Proveedor inactivado.")

    def save_supplies(self, data: dict):
        """ Insumos que suministra, con su presentación habitual y si es el preferido. Conserva el
            último precio de los que ya estaban; solo un proveedor es el preferido de cada insumo. """
        proveedor = self.querys.get_own(ProveedorModel, data["proveedor_id"], "proveedor")
        filas = data.get("insumos") or []
        if len(filas) > MAX_INSUMOS:
            raise CustomException(f"Máximo {MAX_INSUMOS} insumos por proveedor.")
        actuales = {f.insumo_id: f for f in self.querys.insumos_de_proveedor(proveedor.id)}
        vistos = set()
        for fila in filas:
            insumo = self.querys.get_own(InsumoModel, fila["insumo_id"], "insumo")
            if insumo.id in vistos:
                raise CustomException(f"{insumo.nombre} está repetido.")
            vistos.add(insumo.id)
            presentacion_id = int(fila["presentacion_id"]) if fila.get("presentacion_id") else None
            if presentacion_id:
                presentacion = self.db.get(InsumoPresentacionModel, presentacion_id)
                if not presentacion or presentacion.insumo_id != insumo.id:
                    raise CustomException(f"La presentación no es de {insumo.nombre}.")
            preferido = fila.get("preferido") is True
            if preferido:
                for otro in self.querys.proveedores_de_insumo(insumo.id):
                    if otro.proveedor_id != proveedor.id:
                        otro.preferido = False
            if insumo.id in actuales:
                actuales[insumo.id].presentacion_id = presentacion_id
                actuales[insumo.id].preferido = preferido
            else:
                self.querys.insert_data(ProveedorInsumoModel, {
                    "proveedor_id": proveedor.id, "insumo_id": insumo.id, "presentacion_id": presentacion_id,
                    "preferido": preferido}, commit=False)
        for insumo_id, fila in actuales.items():
            if insumo_id not in vistos:
                self.db.delete(fila)
        self.db.commit()
        return self.tools.output(200, f"Insumos de {proveedor.nombre} guardados.",
                                 [self.format_supply(f) for f in self.querys.insumos_de_proveedor(proveedor.id)])

    # ---- Formato ----

    def format(self, proveedor):
        return {
            "id": proveedor.id, "nombre": proveedor.nombre, "razon_social": proveedor.razon_social,
            "tipo_documento": proveedor.tipo_documento, "documento": proveedor.documento,
            "contacto": proveedor.contacto, "telefono": proveedor.telefono, "whatsapp": proveedor.whatsapp,
            "correo": proveedor.correo, "direccion": proveedor.direccion, "forma_pago": proveedor.forma_pago,
            "plazo_dias": proveedor.plazo_dias, "dias_entrega": proveedor.dias_entrega,
            "pedido_minimo": proveedor.pedido_minimo, "notas": proveedor.notas, "activo": proveedor.activo,
        }

    def format_supply(self, fila):
        insumo = self.db.get(InsumoModel, fila.insumo_id)
        presentacion = self.db.get(InsumoPresentacionModel, fila.presentacion_id) if fila.presentacion_id else None
        return {
            "insumo_id": insumo.id, "insumo": insumo.nombre, "unidad": insumo.unidad,
            "presentacion_id": presentacion.id if presentacion else None,
            "presentacion": presentacion.nombre if presentacion else None,
            "factor": float(presentacion.factor) if presentacion else 1.0,
            "preferido": fila.preferido,
            "ultimo_precio": float(fila.ultimo_precio) if fila.ultimo_precio is not None else None,
            "ultimo_costo_unitario": float(fila.ultimo_costo_unitario) if fila.ultimo_costo_unitario is not None else None,
            "ultima_compra_en": fila.ultima_compra_en,
            "costo_promedio": float(insumo.costo_promedio),
        }

    def format_price(self, linea, compra):
        insumo = self.db.get(InsumoModel, linea.insumo_id)
        return {
            "fecha": compra.fecha, "compra_id": compra.id, "numero": compra.numero, "proveedor": compra.proveedor_nombre,
            "insumo_id": insumo.id, "insumo": insumo.nombre, "unidad": insumo.unidad,
            "presentacion": linea.presentacion_nombre, "precio_unitario": float(linea.precio_unitario),
            "costo_unitario": float(dec(linea.precio_unitario) / dec(linea.factor)),
        }

    def clean_data(self, data: dict):
        forma = data.get("forma_pago") or "contado"
        if forma not in FORMAS_PAGO_PROVEEDOR:
            raise CustomException("La forma de pago debe ser contado o crédito.")
        tipo, documento = data.get("tipo_documento") or None, clean_text(data.get("documento"))
        if documento and tipo not in TIPOS_DOCUMENTO:
            raise CustomException("Elige el tipo de documento.")
        plazo = int(data.get("plazo_dias") or 0)
        if plazo < 0 or plazo > 365:
            raise CustomException("El plazo debe estar entre 0 y 365 días.")
        return {
            "nombre": clean_text(data["nombre"]),
            "razon_social": clean_text(data.get("razon_social")),
            "tipo_documento": tipo if documento else None,
            "documento": documento,
            "contacto": clean_text(data.get("contacto")),
            "telefono": clean_text(data.get("telefono")),
            "whatsapp": clean_text(data.get("whatsapp")),
            "correo": clean_text(data.get("correo")),
            "direccion": clean_text(data.get("direccion")),
            "forma_pago": forma,
            "plazo_dias": plazo if forma == "credito" else 0,
            "dias_entrega": clean_text(data.get("dias_entrega")),
            "pedido_minimo": validar_monto(data.get("pedido_minimo") or 0, "pedido mínimo", permitir_cero=True),
            "notas": clean_text(data.get("notas")),
        }
