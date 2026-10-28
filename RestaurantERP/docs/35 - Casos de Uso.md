# 35 - Casos de Uso

**Estado:** Borrador (parcial: cubre solo el flujo del corte vertical)

Cada caso describe **qué quiere lograr un actor** y cómo responde el sistema. Se amplían al escribir cada módulo. Los casos de caja, inventario, domicilios y propinas se agregarán en sus fases.

## Convención

`UC-nn` · **Actor** · **Precondición** · **Flujo principal** · **Alternativas / errores** · **Resultado**

---

## UC-01: Cliente pide por QR de mesa

- **Actor:** cliente.
- **Precondición:** la mesa y su QR están activos; la zona está abierta y el restaurante tiene contrato vigente con el módulo `pedidos`.
- **Flujo principal:**
  1. El cliente escanea el QR.
  2. El sistema resuelve el token y muestra la carta de la zona con mesa y zona visibles.
  3. El cliente agrega productos, modificadores y notas.
  4. Envía la orden.
  5. El sistema valida, calcula precios y guarda.
  6. Según el modo de la zona, la orden va a producción o queda pendiente de aprobación.
  7. El cliente ve el estado de su orden.
- **Alternativas:**
  - Token revocado o mesa desactivada: mensaje claro y sin carta.
  - Producto agotado: se indica y no se permite pedir.
  - Límite de órdenes excedido: se rechaza con mensaje.
  - Sin conexión al enviar: la orden no se envía y se informa.
- **Resultado:** orden creada en la sesión de la mesa.

## UC-02: Mesero aprueba o rechaza una orden de QR

- **Actor:** mesero.
- **Precondición:** zona en modo "con aprobación"; hay una orden `pendiente_aprobacion`.
- **Flujo principal:**
  1. La tablet muestra un aviso destacado con mesa y contenido.
  2. El mesero revisa y **acepta**.
  3. La orden pasa a `nuevo` y llega a producción.
- **Alternativas:** el mesero **rechaza** indicando motivo; el cliente ve el rechazo.
- **Resultado:** orden aprobada o cancelada, con auditoría.

## UC-03: Mesero toma una orden en la tablet

- **Actor:** mesero.
- **Precondición:** sesión iniciada, zona asignada.
- **Flujo principal:**
  1. Selecciona una mesa de su zona.
  2. Agrega ítems de la carta de la zona.
  3. Envía.
  4. Recibe confirmación con número de orden.
- **Alternativas:** sin conexión (no envía y guarda borrador), producto agotado, mesa sin sesión abierta (se abre una).
- **Resultado:** orden creada y comandas emitidas.

## UC-04: Cajero registra una orden de mostrador (mesa externa)

- **Actor:** cajero o encargado de externos.
- **Flujo principal:** elige mesa externa, agrega ítems, opcionalmente nombre y teléfono, envía.
- **Alternativas:** orden para llevar con pago inmediato; orden por WhatsApp con datos de domicilio (fase 1 manual).
- **Resultado:** orden externa con etiqueta clara en producción.

## UC-05: Producción procesa una comanda

- **Actor:** cocinero o bartender.
- **Flujo principal:**
  1. Ve la comanda nueva (azul claro) con aviso.
  2. Pulsa **Abrir**; pasa a amarillo y, si está configurado, se imprime la tirilla.
  3. Prepara.
  4. Pulsa **Despachar**; pasa a la pestaña Listos.
- **Alternativas:** ingrediente agotado (marca ítem agotado), impresora falla (queda en cola), reabrir por error.
- **Resultado:** ítems en `despachado`; aviso al mesero.

## UC-06: Mesero entrega y confirma

- **Actor:** mesero.
- **Flujo principal:** recibe aviso de ítems despachados, los entrega en la mesa y marca `entregado`.
- **Alternativas:** el cliente rechaza el plato (se registra devolución con motivo y permiso).
- **Resultado:** ítems en `entregado`; la orden puede quedar `entregada`.

## UC-07: Agregar ítems a una orden ya enviada

- **Actor:** mesero.
- **Flujo principal:** selecciona la orden abierta de la mesa, agrega ítems, envía.
- **Resultado:** **comanda adicional** con aviso de adición en producción.

## UC-08: Cancelar un ítem o una orden

- **Actor:** mesero (si `nuevo`), administrador o rol con permiso (si posterior).
- **Flujo principal:** selecciona ítem, indica motivo, confirma.
- **Alternativas:** si está `en_proceso`, producción recibe aviso y se registra pérdida.
- **Resultado:** estado `cancelado` (rojo), auditado.

## UC-09: Administrador configura la estructura del local

- **Actor:** administrador de restaurante.
- **Flujo principal:** crea zonas, mesas, puntos de producción, asigna cartas, genera y descarga los QR.
- **Resultado:** local listo para operar. (Detalle en `09`, `10`, `10A`, `19`.)

## UC-10: Administrador revoca un QR de mesa

- **Actor:** administrador.
- **Flujo principal:** selecciona la mesa, revoca el QR, genera uno nuevo y lo descarga.
- **Resultado:** el QR anterior deja de funcionar al instante.

## Pendientes de redactar (fases posteriores)

Cobro y cierre de caja, factura, domicilio completo, pago en línea, cupón, liquidación de propinas, compras e inventario.
