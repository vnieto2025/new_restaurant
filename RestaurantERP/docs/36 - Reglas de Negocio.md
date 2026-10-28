# 36 - Reglas de Negocio

**Estado:** Borrador (parcial: cubre solo el flujo del corte vertical)

Reglas **por módulo**. Las reglas transversales (dinero, fechas, auditoría, aislamiento) viven en `02` con código `RG-nn`. Aquí cada regla tiene código `RN-<módulo>-nn`.

## Órdenes (`RN-ORD`)

- **RN-ORD-01.** El precio de cada ítem lo calcula siempre el servidor; el que envía el cliente se ignora.
- **RN-ORD-02.** Una orden debe tener al menos un ítem con cantidad mayor que cero.
- **RN-ORD-03.** Solo se pueden pedir productos que estén en la carta de la zona de la mesa y estén disponibles.
- **RN-ORD-04.** No se crean órdenes en mesas o zonas desactivadas, ni fuera del horario configurado, ni con contrato suspendido.
- **RN-ORD-05.** Una orden se crea con clave de idempotencia; reintentos con la misma clave devuelven la misma orden (RG-20).
- **RN-ORD-06.** El número de orden es consecutivo por restaurante y jornada operativa.
- **RN-ORD-07.** Nombre y precio del producto se copian al ítem al crearlo (RG-13).
- **RN-ORD-08.** Agregar ítems a una orden enviada crea una **comanda adicional**, no modifica la anterior.
- **RN-ORD-09.** Quitar un ítem en `nuevo` es libre con motivo; en `en_proceso` o posterior exige permiso y avisa a producción.
- **RN-ORD-10.** Toda cancelación requiere motivo, usuario y momento. Una orden nunca se borra.
- **RN-ORD-11.** Una orden pertenece a una sesión de mesa; varias órdenes de la sesión pueden cobrarse en una sola cuenta.
- **RN-ORD-12.** Una orden de domicilio exige nombre, teléfono, dirección y zona de envío válida.
- **RN-ORD-13.** Una orden para recoger no cobra domicilio.

## Estados (`RN-EST`)

- **RN-EST-01.** Solo se permiten las transiciones de `16`; las demás se rechazan.
- **RN-EST-02.** El estado de la orden se deriva de sus ítems; no se edita directamente.
- **RN-EST-03.** Cada cambio de estado guarda usuario, dispositivo, momento y motivo si aplica.
- **RN-EST-04.** Un ítem `entregado` solo se cancela con permiso elevado (devolución) y queda auditado.
- **RN-EST-05.** Reabrir un ítem despachado solo lo hace el punto de producción que lo despachó o un administrador.
- **RN-EST-06.** Los colores de estado son los mismos en todas las pantallas (RG-24); las alertas de tiempo usan otro indicador.

## Mesas y sesiones (`RN-MES`)

- **RN-MES-01.** Una mesa pertenece a una sola zona.
- **RN-MES-02.** Cada restaurante tiene exactamente una mesa externa activa.
- **RN-MES-03.** Una mesa con sesión abierta y cuenta sin pagar no puede desactivarse ni eliminarse.
- **RN-MES-04.** Las órdenes de una mesa solo se aceptan si hay una sesión abierta o se puede abrir una nueva.
- **RN-MES-05.** Al cerrar la cuenta, la sesión de la mesa se cierra; las nuevas órdenes crean otra sesión.

## QR (`RN-QR`)

- **RN-QR-01.** Un QR contiene solo una URL con token opaco; nunca identificadores en claro.
- **RN-QR-02.** El contexto (empresa, restaurante, zona, mesa) se resuelve **en el servidor** a partir del token.
- **RN-QR-03.** Un token revocado deja de funcionar de inmediato.
- **RN-QR-04.** Las órdenes de QR respetan el modo de aceptación de la zona (libre, con aprobación, mesa abierta).
- **RN-QR-05.** Existen límites de órdenes por token y por dispositivo en un periodo; al superarlos se bloquea temporalmente.
- **RN-QR-06.** Las órdenes de QR con aprobación no llegan a producción hasta ser aceptadas.

## Puntos de producción (`RN-PP`)

- **RN-PP-01.** Todo ítem queda asignado a un punto de producción o a despacho directo al crearse.
- **RN-PP-02.** La asignación se hace al crear el ítem y no cambia si luego se edita el producto.
- **RN-PP-03.** Un punto de producción solo ve y modifica sus ítems.
- **RN-PP-04.** Una orden con ítems de varios puntos genera una comanda por punto.
- **RN-PP-05.** No se puede desactivar un punto de producción con comandas abiertas.
- **RN-PP-06.** Los ítems de despacho directo pasan a `despachado` al crearse.

## Impresión (`RN-IMP`)

- **RN-IMP-01.** Las tirillas de comanda no muestran precios.
- **RN-IMP-02.** Toda reimpresión se marca visiblemente y se registra con usuario y motivo.
- **RN-IMP-03.** Un trabajo de impresión fallido permanece en cola y se muestra; no se pierde.
- **RN-IMP-04.** La falta de impresora nunca impide operar: la comanda sigue visible en pantalla.

## Permisos (referencia a `29`)

- **RN-PER-01.** Cada acción sensible (cancelar tras proceso, reabrir, revocar QR, reimprimir) requiere un permiso explícito por rol.
- **RN-PER-02.** Un usuario solo ve y opera dentro de su empresa y de los restaurantes asignados.

## Pendientes (se agregarán con sus módulos)

Caja, facturación, inventario, clientes, cupones, domicilios, propinas.
