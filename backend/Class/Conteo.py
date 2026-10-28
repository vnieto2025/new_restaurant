from Utils.tools import Tools, CustomException, clean_text, now
from Querys.inventario import InventarioQuerys, dec
from Models.conteo_model import ConteoModel
from Models.conteo_linea_model import ConteoLineaModel
from Models.insumo_model import InsumoModel
from Class.Insumo import cantidad

MAX_ABIERTOS = 3


class Conteo:
    """ Conteo físico total, por categoría o de unos pocos insumos (conteo rotativo, doc 22 sección 5).
        Al aplicarlo, cada diferencia se vuelve un ajuste con el usuario y el nombre del conteo (RG-14). """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = InventarioQuerys(db, ctx)

    def list(self, data: dict):
        conteos = self.querys.scoped(ConteoModel).order_by(ConteoModel.id.desc()).limit(30).all()
        return self.tools.output(200, "Conteos." if conteos else "Aún no hay conteos.", [self.format(c, resumen=True) for c in conteos])

    def create(self, data: dict):
        abiertos = self.querys.scoped(ConteoModel).filter(ConteoModel.estado == "abierto").count()
        if abiertos >= MAX_ABIERTOS:
            raise CustomException("Ya hay varios conteos abiertos. Aplica o descarta alguno antes de empezar otro.", 409)
        ids = [int(i) for i in data.get("insumo_ids") or []]
        insumos = self.querys.insumos(categoria=clean_text(data.get("categoria")))
        if ids:
            insumos = [i for i in insumos if i.id in ids]
        if not insumos:
            raise CustomException("No hay insumos activos para contar con ese filtro.")
        nombre = clean_text(data.get("nombre")) or (f"Conteo de {data['categoria']}" if data.get("categoria") else "Conteo general")
        conteo_id = self.querys.insert_data(ConteoModel, {"nombre": nombre[:80], "creado_por": self.ctx.get("usuario_id")}, commit=False)
        for insumo in insumos:
            self.querys.insert_data(ConteoLineaModel, {"conteo_id": conteo_id, "insumo_id": insumo.id}, commit=False)
        self.db.commit()
        return self.tools.output(201, f"Conteo creado con {len(insumos)} insumos.", self.format(self.get_own(conteo_id)))

    def get(self, data: dict):
        return self.tools.output(200, "Conteo.", self.format(self.get_own(data["conteo_id"])))

    # Guarda lo contado; se puede hacer por partes antes de aplicar
    def save(self, data: dict):
        conteo = self.get_own(data["conteo_id"], lock=True)
        self.check_open(conteo)
        lineas = {l.id: l for l in self.lines(conteo.id)}
        for fila in data.get("lineas") or []:
            linea = lineas.get(int(fila["linea_id"]))
            if not linea:
                raise CustomException("Una línea no pertenece a este conteo.")
            valor = fila.get("contado")
            linea.contado = None if valor in (None, "") else cantidad(valor, "cantidad contada", permitir_cero=True)
            linea.nota = clean_text(fila.get("nota"))
        self.db.commit()
        return self.tools.output(200, "Conteo guardado.", self.format(conteo))

    def apply(self, data: dict):
        conteo = self.get_own(data["conteo_id"], lock=True)
        self.check_open(conteo)
        lineas = self.lines(conteo.id)
        contadas = [l for l in lineas if l.contado is not None]
        if not contadas:
            raise CustomException("Aún no se ha contado nada.")
        ajustes = 0
        for linea in contadas:
            insumo = self.db.get(InsumoModel, linea.insumo_id)
            linea.teorico = insumo.stock
            linea.diferencia = dec(linea.contado) - dec(insumo.stock)
            if linea.diferencia != 0:
                motivo = f"{conteo.nombre}" + (f": {linea.nota}" if linea.nota else "")
                self.querys.mover(insumo.id, "ajuste", linea.diferencia, motivo=motivo[:200], conteo_id=conteo.id)
                ajustes += 1
        # Lo que no se contó no se ajusta
        for linea in lineas:
            if linea.contado is None:
                self.db.delete(linea)
        conteo.estado, conteo.aplicado_en, conteo.aplicado_por = "aplicado", now(), self.ctx.get("usuario_id")
        self.querys.audit("conteo_aplicado", "conteo", conteo.id, despues={"insumos": len(contadas), "ajustes": ajustes}, commit=False)
        self.db.commit()
        return self.tools.output(200, f"Conteo aplicado: {ajustes} ajuste(s) en {len(contadas)} insumos contados.", self.format(conteo))

    def discard(self, data: dict):
        conteo = self.get_own(data["conteo_id"], lock=True)
        self.check_open(conteo)
        conteo.estado = "descartado"
        self.db.commit()
        return self.tools.output(200, "Conteo descartado. No se hizo ningún ajuste.")

    def get_own(self, conteo_id, lock=False):
        return self.querys.get_own(ConteoModel, conteo_id, "conteo", lock=lock)

    def lines(self, conteo_id):
        return self.querys.scoped(ConteoLineaModel).filter(ConteoLineaModel.conteo_id == conteo_id).order_by(ConteoLineaModel.id).all()

    @staticmethod
    def check_open(conteo):
        if conteo.estado != "abierto":
            raise CustomException("El conteo ya se cerró.", 409)

    def format(self, conteo, resumen=False):
        lineas = self.lines(conteo.id)
        data = {
            "id": conteo.id, "nombre": conteo.nombre, "estado": conteo.estado, "creado_en": conteo.creado_en,
            "aplicado_en": conteo.aplicado_en, "total": len(lineas),
            "contados": sum(1 for l in lineas if l.contado is not None),
            "con_diferencia": sum(1 for l in lineas if l.diferencia not in (None, 0)),
        }
        if resumen:
            return data
        filas = []
        for linea in lineas:
            insumo = self.db.get(InsumoModel, linea.insumo_id)
            # Abierto: se compara con el stock de ahora; aplicado: con el que había al aplicar
            teorico = dec(linea.teorico) if linea.teorico is not None else dec(insumo.stock)
            diferencia = dec(linea.contado) - teorico if linea.contado is not None else None
            filas.append({
                "linea_id": linea.id, "insumo_id": insumo.id, "insumo": insumo.nombre, "categoria": insumo.categoria,
                "unidad": insumo.unidad, "teorico": float(teorico),
                "contado": float(linea.contado) if linea.contado is not None else None,
                "diferencia": float(diferencia) if diferencia is not None else None,
                "valor_diferencia": int(diferencia * dec(insumo.costo_promedio)) if diferencia is not None else None,
                "nota": linea.nota,
            })
        data["lineas"] = filas
        return data
