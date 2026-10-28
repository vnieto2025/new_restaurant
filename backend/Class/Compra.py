import math
from decimal import Decimal
from Utils.tools import Tools, CustomException, clean_text, now, to_local, fecha_local
from Querys.compra import CompraQuerys
from Querys.inventario import InventarioQuerys, dec, pesos
from Querys.caja import CajaQuerys
from Models.compra_model import CompraModel, FORMAS_PAGO_COMPRA
from Models.compra_linea_model import CompraLineaModel
from Models.compra_recepcion_model import CompraRecepcionModel
from Models.proveedor_model import ProveedorModel
from Models.proveedor_insumo_model import ProveedorInsumoModel
from Models.insumo_model import InsumoModel
from Models.insumo_presentacion_model import InsumoPresentacionModel
from Models.movimiento_caja_model import MovimientoCajaModel
from Class.Insumo import cantidad
from Class.Impuesto import Impuesto
from Class.Inventario import Inventario
from Class.Caja import dia_actual

MAX_LINEAS = 60
PLAZA = "Compra de plaza"
# Variación de costo desde la que se avisa al administrador (doc 23, sección 5)
UMBRAL_ALERTA = Decimal("5")
ESTADOS_TEXTO = {"borrador": "Borrador", "solicitada": "Solicitada", "parcial": "Recibida en parte",
                 "recibida": "Recibida", "cerrada": "Cerrada", "anulada": "Anulada"}
FORMAS_TEXTO = {"contado": "Contado", "credito": "Crédito", "caja": "Pagada de caja"}


class Compra:
    """ Compras formales y rápidas, recepción total o parcial y anulación (doc 23). Toda entrada
        al inventario pasa por InventarioQuerys.mover con tipo "compra" y recalcula el costo promedio. """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = CompraQuerys(db, ctx)
        self.inventario = InventarioQuerys(db, ctx)

    def list(self, data: dict):
        compras = self.querys.compras(
            estado=data.get("estado"), proveedor_id=data.get("proveedor_id"),
            desde=Impuesto.parse_date(data.get("desde")), hasta=Impuesto.parse_date(data.get("hasta")),
            buscar=clean_text(data.get("buscar")), limite=min(int(data.get("limite") or 100), 300))
        result = [self.format_summary(c) for c in compras]
        return self.tools.output(200, "Compras." if result else "No hay compras con ese filtro.", result)

    def get(self, data: dict):
        compra = self.querys.get_own(CompraModel, data["compra_id"], "compra")
        return self.tools.output(200, "Compra.", self.format(compra))

    # Orden de compra al proveedor: queda en borrador o se marca como solicitada
    def create(self, data: dict):
        header, lineas = self.clean_header(data), self.clean_lines(data.get("lineas"))
        estado = "solicitada" if data.get("solicitar") is True else "borrador"
        compra = self.insert(header, lineas, estado)
        self.querys.audit("compra_creada", "compra", compra.id, despues={"numero": compra.numero, "total": compra.total},
                          commit=False)
        self.db.commit()
        return self.tools.output(201, f"Compra {compra.numero} {'solicitada' if estado == 'solicitada' else 'guardada'}.",
                                 self.format(compra))

    # Mientras no llegue nada, la orden se puede corregir; después no (RN-COM-01)
    def update(self, data: dict):
        compra = self.querys.get_own(CompraModel, data["compra_id"], "compra", lock=True)
        if compra.estado not in ("borrador", "solicitada"):
            raise CustomException("Solo se edita una compra que aún no se ha recibido.", 409)
        header, lineas = self.clean_header(data), self.clean_lines(data.get("lineas"))
        for key, value in header.items():
            setattr(compra, key, value)
        self.querys.scoped(CompraLineaModel).filter(CompraLineaModel.compra_id == compra.id).delete(synchronize_session=False)
        self.insert_lines(compra, lineas)
        self.recalc(compra)
        self.db.commit()
        return self.tools.output(200, f"Compra {compra.numero} actualizada.", self.format(compra))

    def request(self, data: dict):
        compra = self.querys.get_own(CompraModel, data["compra_id"], "compra", lock=True)
        if compra.estado != "borrador":
            raise CustomException(f"La compra está {ESTADOS_TEXTO[compra.estado].lower()}.", 409)
        compra.estado, compra.solicitada_en = "solicitada", now()
        self.db.commit()
        return self.tools.output(200, f"Compra {compra.numero} solicitada.", self.format(compra))

    def receive(self, data: dict):
        """ Recepción de mercancía: lo que llegó puede diferir de lo pedido (doc 23, sección 4).
            Lo que falta queda pendiente en la compra (RN-COM-02). """
        compra = self.querys.get_own(CompraModel, data["compra_id"], "compra", lock=True)
        if compra.estado not in ("borrador", "solicitada", "parcial"):
            raise CustomException(f"La compra ya está {ESTADOS_TEXTO[compra.estado].lower()}.", 409)
        resultado = self.apply_reception(compra, data.get("lineas") or [], clean_text(data.get("notas")))
        if data.get("factura_proveedor"):
            compra.factura_proveedor = clean_text(data["factura_proveedor"])
        self.db.commit()
        mensaje = "Mercancía recibida. La compra queda completa." if compra.estado == "recibida" else \
            "Mercancía recibida. Lo que faltó queda pendiente en la compra."
        return self.tools.output(200, mensaje, {**self.format(compra), **resultado})

    def quick(self, data: dict):
        """ Compra rápida (plaza, tienda): se registra ya recibida en un solo paso (doc 23, sección 1) """
        header, lineas = self.clean_header(data), self.clean_lines(data.get("lineas"))
        compra = self.insert(header, lineas, "borrador", rapida=True)
        entradas = [{"compra_linea_id": linea.id, "cantidad": linea.cantidad} for linea in self.querys.lineas(compra.id)]
        resultado = self.apply_reception(compra, entradas, None)
        compra.factura_proveedor = clean_text(data.get("factura_proveedor"))
        compra.estado, compra.cerrada_en, compra.cerrada_por = "cerrada", now(), self.ctx.get("usuario_id")
        self.querys.audit("compra_rapida", "compra", compra.id, despues={"numero": compra.numero, "total": compra.total,
                                                                         "forma_pago": compra.forma_pago}, commit=False)
        self.db.commit()
        return self.tools.output(201, f"Compra {compra.numero} registrada y sumada al inventario.",
                                 {**self.format(compra), **resultado})

    # Conciliada con la factura del proveedor; con faltantes se cierra solo si se confirma
    def close(self, data: dict):
        compra = self.querys.get_own(CompraModel, data["compra_id"], "compra", lock=True)
        if compra.estado not in ("recibida", "parcial"):
            raise CustomException("Solo se cierra una compra recibida.", 409)
        if compra.estado == "parcial" and data.get("cerrar_con_pendiente") is not True:
            pendientes = sum(1 for l in self.querys.lineas(compra.id) if dec(l.cantidad_recibida) < dec(l.cantidad))
            raise CustomException(f"Hay {pendientes} insumos sin recibir completos. Confirma para cerrar sin esperarlos.",
                                  409, {"pendientes": pendientes})
        if data.get("factura_proveedor"):
            compra.factura_proveedor = clean_text(data["factura_proveedor"])
        if data.get("notas"):
            compra.notas = self.join_notes(compra.notas, clean_text(data["notas"]))
        compra.estado, compra.cerrada_en, compra.cerrada_por = "cerrada", now(), self.ctx.get("usuario_id")
        self.db.commit()
        return self.tools.output(200, f"Compra {compra.numero} cerrada.", self.format(compra))

    def void(self, data: dict):
        """ Anular: si ya entró mercancía se revierte con movimientos contrarios al mismo costo
            (RN-COM-05). La existencia puede quedar negativa si ya se consumió. """
        compra = self.querys.get_own(CompraModel, data["compra_id"], "compra", lock=True)
        if compra.estado == "anulada":
            raise CustomException("La compra ya estaba anulada.", 409)
        motivo = clean_text(data["motivo"])
        negativos = []
        for movimiento in self.querys.movimientos_de_compra(compra.id):
            self.inventario.mover(movimiento.insumo_id, "anulacion_compra", -dec(movimiento.cantidad),
                                  costo_unitario=movimiento.costo_unitario, motivo=f"Anulación: {motivo}"[:200],
                                  referencia=f"Compra {compra.numero}", compra_id=compra.id)
            insumo = self.db.get(InsumoModel, movimiento.insumo_id)
            if dec(insumo.stock) < 0 and insumo.nombre not in negativos:
                negativos.append(insumo.nombre)

        reintegro = 0
        if data.get("reintegrar_caja") is True:
            reintegro = sum(r.valor for r in self.querys.recepciones(compra.id) if r.movimiento_caja_id)
            if reintegro:
                turno = self.open_shift()
                self.querys.insert_data(MovimientoCajaModel, {
                    "turno_caja_id": turno.id, "tipo": "aporte", "monto": reintegro,
                    "concepto": f"Reintegro compra {compra.numero}", "usuario_id": self.ctx.get("usuario_id"),
                }, commit=False)

        antes = compra.estado
        compra.estado, compra.anulada_en = "anulada", now()
        compra.anulada_por, compra.motivo_anulacion = self.ctx.get("usuario_id"), motivo
        self.querys.audit("compra_anulada", "compra", compra.id, antes={"estado": antes},
                          despues={"valor_recibido": compra.valor_recibido, "reintegro_caja": reintegro}, motivo=motivo, commit=False)
        self.db.commit()
        mensaje = f"Compra {compra.numero} anulada."
        if compra.valor_recibido:
            mensaje += " Se revirtieron sus entradas al inventario."
        if reintegro:
            mensaje += f" Se devolvieron {self.tools.format_number(reintegro)} a la caja."
        if negativos:
            mensaje += f" Quedaron en negativo: {', '.join(negativos)}. Revisa el inventario."
        return self.tools.output(200, mensaje, self.format(compra))

    def suggested(self, data: dict):
        """ Lista de compras sugerida: insumos en o bajo su mínimo, para llevarlos al doble del mínimo,
            descontando lo que ya viene en camino, agrupados por el proveedor preferido. """
        en_camino = {}
        for compra in self.querys.compras(estado="pendientes", limite=300):
            for linea in self.querys.lineas(compra.id):
                faltante = max(dec(linea.cantidad) - dec(linea.cantidad_recibida), Decimal(0)) * dec(linea.factor)
                en_camino[linea.insumo_id] = en_camino.get(linea.insumo_id, Decimal(0)) + faltante
        preferidos = self.querys.preferidos()
        grupos = {}
        for insumo in self.inventario.insumos():
            minimo, stock = dec(insumo.stock_minimo), dec(insumo.stock)
            if insumo.es_preparacion or minimo <= 0 or stock > minimo:
                continue
            faltante = minimo * 2 - stock - en_camino.get(insumo.id, Decimal(0))
            if faltante <= 0:
                continue
            relacion = preferidos.get(insumo.id)
            presentacion = self.presentation_for(insumo, relacion)
            factor = dec(presentacion.factor) if presentacion else Decimal(1)
            unidades = math.ceil(faltante / factor)
            precio = dec(relacion.ultimo_precio) if relacion and relacion.ultimo_precio is not None \
                else dec(insumo.costo_promedio) * factor
            proveedor = self.db.get(ProveedorModel, relacion.proveedor_id) if relacion else None
            clave = proveedor.id if proveedor else 0
            grupo = grupos.setdefault(clave, {
                "proveedor_id": proveedor.id if proveedor else None,
                "proveedor": proveedor.nombre if proveedor else "Sin proveedor preferido",
                "whatsapp": (proveedor.whatsapp or proveedor.telefono) if proveedor else None,
                "pedido_minimo": proveedor.pedido_minimo if proveedor else 0, "items": [], "total_estimado": 0})
            item = {
                "insumo_id": insumo.id, "insumo": insumo.nombre, "unidad": insumo.unidad, "stock": float(stock),
                "stock_minimo": float(minimo), "en_camino": float(en_camino.get(insumo.id, 0)),
                "presentacion_id": presentacion.id if presentacion else None,
                "presentacion": presentacion.nombre if presentacion else None, "factor": float(factor),
                "cantidad": unidades, "precio_estimado": pesos(precio), "total_estimado": pesos(precio * unidades),
            }
            grupo["items"].append(item)
            grupo["total_estimado"] += item["total_estimado"]
        result = sorted(grupos.values(), key=lambda g: (g["proveedor_id"] is None, g["proveedor"]))
        return self.tools.output(200, "Compras sugeridas." if result else "Ningún insumo está bajo su mínimo.", result)

    # ---- Recepción ----

    def apply_reception(self, compra, entradas: list, notas):
        lineas = {linea.id: linea for linea in self.querys.lineas(compra.id, lock=True)}
        if compra.forma_pago == "caja":
            self.check_cash_permission()
        antes = self.dish_costs()
        valor, alertas_precio, recibidas = 0, [], 0
        referencia = f"Compra {compra.numero}"
        for entrada in entradas:
            linea = lineas.get(int(entrada["compra_linea_id"]))
            if not linea:
                raise CustomException("Una de las líneas no es de esta compra.")
            insumo = self.db.get(InsumoModel, linea.insumo_id)
            llegada = cantidad(entrada.get("cantidad") or 0, f"cantidad de {insumo.nombre}", permitir_cero=True)
            if entrada.get("precio_unitario") not in (None, ""):
                nuevo = dec(entrada["precio_unitario"])
                if nuevo < 0:
                    raise CustomException(f"El precio de {insumo.nombre} no es válido.")
                if nuevo != dec(linea.precio_unitario):
                    if dec(linea.cantidad_recibida) > 0:
                        raise CustomException(f"{insumo.nombre} ya tuvo una recepción con otro precio: regístralo en otra compra.")
                    linea.precio_unitario, linea.total = nuevo, pesos(dec(linea.cantidad) * nuevo)
            if entrada.get("novedad"):
                linea.novedad = self.join_notes(linea.novedad, clean_text(entrada["novedad"]), 200)
            if llegada == 0:
                continue
            factor = dec(linea.factor)
            costo = dec(linea.precio_unitario) / factor
            self.inventario.mover(insumo.id, "compra", (llegada * factor).quantize(Decimal("0.001")), costo_unitario=costo,
                                  motivo=f"{referencia} · {compra.proveedor_nombre}"[:200], referencia=referencia, compra_id=compra.id)
            linea.cantidad_recibida = dec(linea.cantidad_recibida) + llegada
            valor += pesos(llegada * dec(linea.precio_unitario))
            recibidas += 1
            alerta = self.update_supplier_price(compra, linea, insumo, costo)
            if alerta:
                alertas_precio.append(alerta)
        if not recibidas:
            raise CustomException("Indica cuánto llegó de al menos un insumo.")

        movimiento_caja_id = None
        if compra.forma_pago == "caja" and valor > 0:
            movimiento_caja_id = self.pay_from_cash(compra, valor)
        self.querys.insert_data(CompraRecepcionModel, {
            "compra_id": compra.id, "usuario_id": self.ctx.get("usuario_id"), "valor": valor, "notas": notas,
            "movimiento_caja_id": movimiento_caja_id}, commit=False)

        completa = all(dec(l.cantidad_recibida) >= dec(l.cantidad) for l in lineas.values())
        compra.estado = "recibida" if completa else "parcial"
        compra.recibida_en, compra.recibida_por = now(), self.ctx.get("usuario_id")
        self.recalc(compra)
        self.querys.audit("compra_recibida", "compra", compra.id, despues={"valor": valor, "estado": compra.estado},
                          motivo=notas, commit=False)
        self.db.flush()
        return {"recibido": valor, "alertas_precio": alertas_precio, "alertas_costo": self.cost_alerts(antes)}

    def update_supplier_price(self, compra, linea, insumo, costo):
        """ Último precio del proveedor para ese insumo. Si subió más del umbral, se avisa (doc 24, sección 2) """
        if not compra.proveedor_id:
            return None
        relacion = self.querys.proveedor_insumo(compra.proveedor_id, insumo.id)
        alerta = None
        if relacion and relacion.ultimo_costo_unitario:
            anterior = dec(relacion.ultimo_costo_unitario)
            variacion = (costo - anterior) * 100 / anterior
            if variacion >= UMBRAL_ALERTA:
                alerta = {"insumo": insumo.nombre, "presentacion": linea.presentacion_nombre or insumo.unidad,
                          "antes": pesos(anterior * dec(linea.factor)), "despues": pesos(linea.precio_unitario),
                          "variacion": float(round(variacion, 1))}
        if not relacion:
            # El primer proveedor que surte un insumo queda como preferido
            sin_preferido = not any(r.preferido for r in self.querys.proveedores_de_insumo(insumo.id))
            self.querys.insert_data(ProveedorInsumoModel, {
                "proveedor_id": compra.proveedor_id, "insumo_id": insumo.id, "presentacion_id": linea.presentacion_id,
                "preferido": sin_preferido}, commit=False)
            relacion = self.querys.proveedor_insumo(compra.proveedor_id, insumo.id)
        relacion.ultimo_precio, relacion.ultimo_costo_unitario = linea.precio_unitario, costo.quantize(Decimal("0.0001"))
        relacion.ultima_compra_en = now()
        if not relacion.presentacion_id and linea.presentacion_id:
            relacion.presentacion_id = linea.presentacion_id
        return alerta

    def dish_costs(self):
        costos = {}
        for receta in self.inventario.recetas():
            if receta.producto_id:
                costos[receta.producto_id] = self.inventario.costo_receta(receta)
        return costos

    def cost_alerts(self, antes: dict):
        """ Platos que la compra encareció más del umbral (doc 23, sección 5) """
        from Models.producto_model import ProductoModel
        alertas = []
        for producto_id, despues in self.dish_costs().items():
            previo = antes.get(producto_id)
            if not previo or previo <= 0:
                continue
            variacion = (despues - previo) * 100 / previo
            if variacion >= UMBRAL_ALERTA:
                producto = self.db.get(ProductoModel, producto_id)
                alertas.append({"producto_id": producto_id, "producto": producto.nombre, "antes": pesos(previo),
                                "despues": pesos(despues), "variacion": float(round(variacion, 1))})
        return sorted(alertas, key=lambda a: -a["variacion"])

    # ---- Caja ----

    def check_cash_permission(self):
        if "caja" not in self.ctx.get("modulos", set()):
            raise CustomException("El restaurante no tiene el módulo de caja: elige otra forma de pago.")
        if "caja.movimientos" not in self.ctx.get("permisos", set()):
            raise CustomException("No tienes permiso para registrar gastos de caja: elige otra forma de pago.", 403)

    def open_shift(self):
        caja = CajaQuerys(self.db, self.ctx)
        turno = caja.get_turno_abierto(caja.get_caja().id)
        if not turno:
            raise CustomException("Abre el turno de caja para mover el efectivo de esta compra.", 409)
        return turno

    def pay_from_cash(self, compra, valor):
        """ Gasto de caja ligado a la compra, sin digitarlo dos veces (doc 23, sección 6) """
        turno = self.open_shift()
        disponible = CajaQuerys(self.db, self.ctx).resumen_turno(turno)["efectivo_esperado"]
        if valor > disponible:
            raise CustomException(f"En caja debería haber {self.tools.format_number(disponible)}: no alcanza para pagar "
                                  f"{self.tools.format_number(valor)}. Elige otra forma de pago.")
        concepto = f"Compra {compra.numero} · {compra.proveedor_nombre}"[:200]
        movimiento_id = self.querys.insert_data(MovimientoCajaModel, {
            "turno_caja_id": turno.id, "tipo": "gasto", "monto": valor, "concepto": concepto,
            "usuario_id": self.ctx.get("usuario_id")}, commit=False)
        self.querys.audit("caja_gasto", "movimiento_caja", movimiento_id, despues={"monto": valor, "compra_id": compra.id},
                          motivo=concepto, commit=False)
        return movimiento_id

    # ---- Datos ----

    def clean_header(self, data: dict):
        proveedor = None
        if data.get("proveedor_id"):
            proveedor = self.querys.get_own(ProveedorModel, data["proveedor_id"], "proveedor")
            if not proveedor.activo:
                raise CustomException(f"{proveedor.nombre} está inactivo.")
        forma = data.get("forma_pago") or (proveedor.forma_pago if proveedor else "contado")
        if forma not in FORMAS_PAGO_COMPRA:
            raise CustomException("La forma de pago debe ser contado, crédito o caja.")
        hoy = dia_actual(self.ctx)
        fecha = Impuesto.parse_date(data.get("fecha")) or hoy
        if fecha > fecha_local(self.ctx.get("zona_horaria")):
            raise CustomException("La fecha de la compra no puede ser futura.")
        return {
            "proveedor_id": proveedor.id if proveedor else None,
            "proveedor_nombre": proveedor.nombre if proveedor else (clean_text(data.get("proveedor_nombre")) or PLAZA),
            "fecha": fecha,
            "entrega_esperada": Impuesto.parse_date(data.get("entrega_esperada")),
            "forma_pago": forma,
            "notas": clean_text(data.get("notas")),
        }

    def clean_lines(self, lineas):
        if not lineas:
            raise CustomException("La compra necesita al menos un insumo.")
        if len(lineas) > MAX_LINEAS:
            raise CustomException(f"Máximo {MAX_LINEAS} insumos por compra.")
        result, vistos = [], set()
        for linea in lineas:
            insumo = self.querys.get_own(InsumoModel, linea["insumo_id"], "insumo")
            if not insumo.activo:
                raise CustomException(f"{insumo.nombre} está inactivo.")
            if insumo.es_preparacion:
                raise CustomException(f"{insumo.nombre} es una preparación: se produce, no se compra.")
            presentacion = None
            if linea.get("presentacion_id"):
                presentacion = self.db.get(InsumoPresentacionModel, int(linea["presentacion_id"]))
                if not presentacion or presentacion.insumo_id != insumo.id:
                    raise CustomException(f"La presentación no es de {insumo.nombre}.")
            clave = (insumo.id, presentacion.id if presentacion else None)
            if clave in vistos:
                raise CustomException(f"{insumo.nombre} está repetido en la compra.")
            vistos.add(clave)
            unidades = cantidad(linea["cantidad"], f"cantidad de {insumo.nombre}")
            # Se puede dar el precio por unidad de compra o el valor total pagado por la línea
            if linea.get("total") not in (None, ""):
                total = int(linea["total"])
                if total < 0:
                    raise CustomException(f"El valor de {insumo.nombre} no es válido.")
                precio = (dec(total) / unidades).quantize(Decimal("0.0001"))
            else:
                precio = dec(linea.get("precio_unitario") or 0)
                if precio < 0:
                    raise CustomException(f"El precio de {insumo.nombre} no es válido.")
                total = pesos(unidades * precio)
            impuesto = dec(linea.get("impuesto_porcentaje") or 0)
            if impuesto < 0 or impuesto > 100:
                raise CustomException("El porcentaje de impuesto no es válido.")
            result.append({
                "insumo_id": insumo.id, "presentacion_id": presentacion.id if presentacion else None,
                "presentacion_nombre": presentacion.nombre if presentacion else None,
                "factor": dec(presentacion.factor) if presentacion else Decimal(1),
                "cantidad": unidades, "precio_unitario": precio, "impuesto_porcentaje": impuesto, "total": total,
            })
        return result

    def insert(self, header: dict, lineas: list, estado: str, rapida=False):
        compra_id = self.querys.insert_data(CompraModel, {
            **header, "numero": self.querys.next_number(), "estado": estado, "es_rapida": rapida,
            "creado_por": self.ctx.get("usuario_id"), "solicitada_en": now() if estado == "solicitada" else None,
        }, commit=False)
        compra = self.db.get(CompraModel, compra_id)
        self.insert_lines(compra, lineas)
        self.recalc(compra)
        return compra

    def insert_lines(self, compra, lineas: list):
        for linea in lineas:
            self.querys.insert_data(CompraLineaModel, {**linea, "compra_id": compra.id}, commit=False)

    def recalc(self, compra):
        """ Totales en pesos; los impuestos se calculan sobre lo recibido cuando ya llegó algo """
        lineas = self.querys.lineas(compra.id)
        compra.total = sum(l.total for l in lineas)
        compra.valor_recibido = sum(pesos(dec(l.cantidad_recibida) * dec(l.precio_unitario)) for l in lineas)
        impuestos = 0
        for linea in lineas:
            valor = linea.total if not compra.valor_recibido else pesos(dec(linea.cantidad_recibida) * dec(linea.precio_unitario))
            porcentaje = dec(linea.impuesto_porcentaje)
            if porcentaje:
                impuestos += pesos(dec(valor) - dec(valor) / (1 + porcentaje / 100))
        compra.impuestos = impuestos

    def presentation_for(self, insumo, relacion):
        if relacion and relacion.presentacion_id:
            return self.db.get(InsumoPresentacionModel, relacion.presentacion_id)
        presentaciones = self.inventario.presentaciones(insumo.id)
        return presentaciones[-1] if presentaciones else None

    @staticmethod
    def join_notes(actual, nueva, limite=500):
        return (f"{actual} · {nueva}" if actual else nueva)[:limite]

    # ---- Formato ----

    def format_summary(self, compra):
        return {
            "id": compra.id, "numero": compra.numero, "proveedor_id": compra.proveedor_id, "proveedor": compra.proveedor_nombre,
            "estado": compra.estado, "estado_texto": ESTADOS_TEXTO[compra.estado], "es_rapida": compra.es_rapida,
            "fecha": compra.fecha, "entrega_esperada": compra.entrega_esperada, "forma_pago": compra.forma_pago,
            "forma_pago_texto": FORMAS_TEXTO[compra.forma_pago], "total": compra.total,
            "valor_recibido": compra.valor_recibido, "impuestos": compra.impuestos,
            "factura_proveedor": compra.factura_proveedor,
        }

    def format(self, compra):
        tz = self.ctx.get("zona_horaria")
        data = self.format_summary(compra)
        lineas = []
        for linea in self.querys.lineas(compra.id):
            insumo = self.db.get(InsumoModel, linea.insumo_id)
            pendiente = max(dec(linea.cantidad) - dec(linea.cantidad_recibida), Decimal(0))
            lineas.append({
                "id": linea.id, "insumo_id": insumo.id, "insumo": insumo.nombre, "unidad": insumo.unidad,
                "presentacion_id": linea.presentacion_id, "presentacion": linea.presentacion_nombre,
                "factor": float(linea.factor), "cantidad": float(linea.cantidad),
                "cantidad_recibida": float(linea.cantidad_recibida), "pendiente": float(pendiente),
                "precio_unitario": float(linea.precio_unitario),
                "costo_unitario": float(dec(linea.precio_unitario) / dec(linea.factor)),
                "impuesto_porcentaje": float(linea.impuesto_porcentaje), "total": linea.total, "novedad": linea.novedad,
            })
        caja = CajaQuerys(self.db, self.ctx)
        recepciones = [{
            "id": r.id, "fecha": r.creado_en, "hora_local": to_local(r.creado_en, tz), "valor": r.valor, "notas": r.notas,
            "usuario": caja.nombre_usuario(r.usuario_id), "pagado_de_caja": bool(r.movimiento_caja_id),
        } for r in self.querys.recepciones(compra.id)]
        proveedor = self.db.get(ProveedorModel, compra.proveedor_id) if compra.proveedor_id else None
        data.update({
            "lineas": lineas,
            "recepciones": recepciones,
            "notas": compra.notas,
            "creado_por": caja.nombre_usuario(compra.creado_por),
            "creado_en": compra.creado_en,
            "recibida_en": compra.recibida_en,
            "recibida_por": caja.nombre_usuario(compra.recibida_por),
            "cerrada_en": compra.cerrada_en,
            "anulada_en": compra.anulada_en,
            "anulada_por": caja.nombre_usuario(compra.anulada_por),
            "motivo_anulacion": compra.motivo_anulacion,
            "whatsapp": (proveedor.whatsapp or proveedor.telefono) if proveedor else None,
            "mensaje_proveedor": self.supplier_message(compra, proveedor, lineas),
            "puede_editar": compra.estado in ("borrador", "solicitada"),
            "puede_recibir": compra.estado in ("borrador", "solicitada", "parcial"),
            "puede_cerrar": compra.estado in ("recibida", "parcial"),
            "puede_anular": compra.estado != "anulada",
        })
        return data

    def supplier_message(self, compra, proveedor, lineas):
        """ Texto del pedido para enviarlo por WhatsApp al proveedor (doc 24, pregunta abierta; doc 31B) """
        restaurante = CajaQuerys(self.db, self.ctx).restaurante_actual()
        saludo = f"Hola {proveedor.contacto or proveedor.nombre}" if proveedor else "Hola"
        renglones = []
        for linea in lineas:
            medida = linea["presentacion"] or linea["unidad"]
            renglones.append(f"- {Inventario.fmt(linea['cantidad'])} {medida} de {linea['insumo']}")
        texto = f"{saludo}, le escribimos de {restaurante.nombre}. Pedido {compra.numero}:\n" + "\n".join(renglones)
        if compra.entrega_esperada:
            texto += f"\nEntrega: {compra.entrega_esperada.strftime('%d/%m/%Y')}."
        return texto + "\nGracias."
