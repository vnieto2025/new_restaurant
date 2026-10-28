# 23 - Módulo Compras

**Estado:** Propuesto

Registra **lo que el restaurante compra**: órdenes de compra, recepción de mercancía y costos. Es la fuente principal de entradas al inventario (`22`).

## 1. Dos formas de comprar (y por qué importa)

| Forma | Descripción | Frecuencia en negocios pequeños |
|---|---|---|
| **Compra formal** | Orden de compra al proveedor, recepción, factura del proveedor | Media |
| **Compra rápida** | Se compra en plaza o tienda y se registra después | **Muy alta** |

Si el sistema solo soporta compras formales, el restaurante **no lo usará**. Debe haber un flujo de **compra rápida** de pocos pasos.

## 2. Estados de una compra

| Estado | Significado |
|---|---|
| `borrador` | En preparación |
| `solicitada` | Orden enviada al proveedor |
| `recibida` | Mercancía recibida (total o parcial); genera entradas de inventario |
| `cerrada` | Conciliada con la factura del proveedor |
| `anulada` | Cancelada con motivo |

La compra rápida pasa directamente a `recibida` o `cerrada`.

## 3. Datos de una compra

| Campo | Descripción |
|---|---|
| Proveedor | Referencia a `24`, o "compra de plaza" sin proveedor fijo |
| Fecha y usuario | Quién y cuándo |
| Ítems | Insumo, cantidad, unidad de compra, **costo unitario** |
| Impuestos | Si el proveedor los discrimina |
| Total | Calculado |
| Soporte | Foto o referencia de la factura o recibo |
| Forma de pago | Contado, crédito (cuenta por pagar, fase 3), pagado de caja (`20`) |
| Notas | Observaciones de calidad, diferencias |

## 4. Recepción de mercancía

1. Seleccionar la compra o crear una rápida.
2. Confirmar **cantidades recibidas** (pueden diferir de lo pedido).
3. Registrar diferencias y novedades (producto dañado, faltante).
4. Al confirmar, el sistema **crea las entradas de inventario** y **recalcula el costo** de cada insumo (`22`).

## 5. Impacto en costos y márgenes

Cada compra actualiza el **costo promedio** de los insumos, lo que cambia el **costo de los platos** (`14`). El sistema debe informar al administrador cuando una compra encarece platos de forma importante.

## 6. Compras pagadas desde la caja

Cuando se paga de contado con dinero de caja (por ejemplo, ir a la plaza), debe poder registrarse como **gasto de caja** ligado a la compra (`20`), evitando doble digitación.

## 7. Cuentas por pagar (fase 3)

Compras a crédito con vencimiento, abonos y estado de cuenta por proveedor. Fuera del MVP.

## 8. Reglas

- **RN-COM-01.** Una compra recibida no se edita; se corrige con un ajuste de inventario o una devolución.
- **RN-COM-02.** Una recepción parcial deja el saldo pendiente en la compra.
- **RN-COM-03.** Toda compra tiene usuario y fecha de recepción.
- **RN-COM-04.** El costo unitario se expresa en la unidad de compra y se convierte a la unidad base con el factor del insumo.
- **RN-COM-05.** Una compra anulada después de recibirse revierte sus entradas con movimientos compensatorios.

## 9. Preguntas abiertas

- ¿Se usa lectura de factura del proveedor con foto o escaneo? (Fase 3, complejo y costoso.)
- ¿Se necesita aprobación de compras por montos?
- ¿Se manejan listas de compras sugeridas a partir del stock mínimo? (Valioso, fase 2.)
