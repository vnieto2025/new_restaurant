# 24 - Módulo Proveedores

**Estado:** Propuesto

Directorio de quienes suministran insumos y artículos, con su historial de precios y compras.

## 1. Datos de un proveedor

| Campo | Descripción |
|---|---|
| Nombre comercial y razón social | Identificación |
| Documento fiscal | Opcional pero recomendable |
| Contacto | Persona, teléfono, correo, WhatsApp |
| Dirección | Opcional |
| Condiciones | Forma de pago habitual, plazo, días de entrega, pedido mínimo |
| Insumos que suministra | Relación con `22` |
| Notas | Observaciones de calidad y trato |
| Estado | `activo`, `inactivo` |

## 2. Relación proveedor–insumo

Para cada insumo que un proveedor suministra se guarda:

- **Presentación** (bulto de 25 kg, caja de 24) y su factor de conversión.
- **Último precio** y **histórico de precios**.
- Si es el proveedor **preferido** del insumo.

Así el sistema puede **sugerir a quién comprar** y **mostrar si un proveedor subió precios**.

## 3. Historial

- Compras realizadas (`23`).
- Evolución de precios por insumo.
- Incidencias (entregas tardías, devoluciones).
- Totales comprados por periodo.

## 4. Comparación (fase 2)

Para un mismo insumo, comparar proveedores por precio, plazo y cumplimiento. Útil para negociar; **no es necesario en el MVP**.

## 5. Reglas

- **RN-PRV-01.** Un proveedor con compras no se elimina; se inactiva (RG-11).
- **RN-PRV-02.** Los precios históricos no se sobrescriben; se agregan nuevos registros con fecha.
- **RN-PRV-03.** Los datos de contacto del proveedor son de la empresa y no se comparten entre empresas (RG-16).

## 6. Preguntas abiertas

- ¿Un proveedor se comparte entre restaurantes de la misma empresa?
- ¿Se envían órdenes de compra por WhatsApp al proveedor desde el sistema? (Posible con el mensaje prellenado, `31B`.)
