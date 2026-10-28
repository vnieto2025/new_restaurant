# 12 - Módulo Productos

**Estado:** Propuesto

Un **producto** es lo que se vende: un plato, una bebida, un combo. Los productos viven en el restaurante (o en la empresa, si se comparten, fase 2) y se publican en una o varias **cartas** (`11`).

## 1. Tipos de producto

| Tipo | Descripción | Ejemplo |
|---|---|---|
| **Simple** | Un precio, sin opciones | Gaseosa 350 ml |
| **Con variantes** | Mismo producto con tamaños o presentaciones y precio distinto | Pizza personal / mediana / familiar |
| **Con modificadores** | Opciones adicionales o a quitar | Hamburguesa: sin cebolla, queso extra |
| **Combo** | Varios productos a un precio | Hamburguesa + papas + bebida |

## 2. Datos de un producto

| Campo | Descripción |
|---|---|
| Nombre y descripción | Para la carta y las tirillas (nombre corto para tirilla) |
| Código | Opcional, útil para búsquedas e importación |
| Categoría | Ver `13` |
| Precio base | Con las reglas de impuesto de ADR-010 |
| Impuesto | Tipo aplicable (`21A`) |
| **Punto de producción** | A dónde va la comanda (`19`) o despacho directo |
| Imagen | Opcional |
| Variantes | Lista con su precio |
| Grupos de modificadores | Ver sección 3 |
| Disponibilidad | `disponible`, `agotado` (manual) |
| Visibilidad | Qué cartas y zonas lo muestran |
| Receta | Opcional (`14`) |
| Restricción | Por ejemplo "licor, mayores de edad" |
| Estado | `activo`, `inactivo` |

## 3. Modificadores

Un **grupo de modificadores** reúne opciones relacionadas con reglas simples:

| Campo del grupo | Descripción |
|---|---|
| Nombre | "Adicionales", "Punto de cocción", "Quitar ingredientes" |
| Mínimo / máximo de opciones | Si es obligatorio elegir una (punto de cocción) o varias |
| Opciones | Cada una con **precio adicional** (puede ser 0) |

Un grupo se puede **reutilizar** en varios productos. Los modificadores no cambian el punto de producción en el MVP (`19`).

## 4. Combos

Un combo define **componentes**, cada uno con la posibilidad de elegir entre varios productos ("bebida a elección"). Cada componente se enruta por su propio producto al crear la orden (`19`). `[POR CONFIRMAR]`: si el combo es MVP o fase 2. Recomiendo **fase 2**; en el MVP se puede simular con un producto simple.

## 5. Disponibilidad y agotados

- El administrador, el cajero o **producción** puede marcar un producto como **agotado** de inmediato.
- Al agotarse, desaparece o se muestra bloqueado en todas las cartas y tablets en tiempo real.
- Un agotado manual **se reinicia** al comenzar la siguiente jornada, configurable.
- Si hay **inventario con receta** (`22`), el sistema podrá sugerir el agotado cuando el stock llegue a cero (fase 2).

## 6. Precios e historial

- Cada cambio de precio se **audita** con fecha y usuario (RG-14).
- Los cambios aplican a órdenes **nuevas**; las existentes conservan su precio (RG-13).
- Precios diferentes por carta o canal: se resuelven en la **relación carta–producto** (`11`), no duplicando el producto.

## 7. Carga y mantenimiento

- Crear manualmente en la interfaz.
- **Importación masiva** desde una hoja de cálculo (CSV o Excel) para el onboarding (`41`).
- Duplicar un producto para crear variantes similares.
- Copiar productos entre restaurantes de la empresa (fase 2).

## 8. Reglas

- **RN-PRO-01.** Todo producto tiene nombre, precio, categoría y destino de producción (o despacho directo).
- **RN-PRO-02.** Un producto con historial no se elimina; se inactiva (RG-11).
- **RN-PRO-03.** Un grupo de modificadores con mínimo mayor que cero debe satisfacerse para poder agregar el producto al carrito.
- **RN-PRO-04.** El precio de un modificador es aditivo y puede ser cero, nunca negativo en el MVP.
- **RN-PRO-05.** Un producto marcado agotado no puede agregarse a una orden nueva por ningún canal.

## 9. Preguntas abiertas

- ¿Se manejan precios con impuesto incluido o sin él? Pendiente en ADR-010.
- ¿Se necesitan productos de "precio abierto" (el cajero digita el valor)? Es común en mostrador.
- ¿Productos por peso (por ejemplo panadería o carnes)? Fuera del MVP.
