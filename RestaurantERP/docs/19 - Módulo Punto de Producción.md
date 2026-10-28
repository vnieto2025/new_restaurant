# 19 - Módulo Punto de Producción

**Estado:** Propuesto

Un **punto de producción** es cualquier lugar donde se preparan ítems: cocina, bar, parrilla, postres, panadería, barra de jugos. La pantalla de cocina (`18`) es la interfaz de un punto de producción. Este documento define **cómo se configuran y cómo se enrutan los ítems** hacia ellos.

## 1. Por qué existe como concepto aparte

Tu requisito incluye zonas de bar con solo bebidas, zonas de comida rápida, cocina y bar con pantallas separadas. Si "cocina" fuera un único lugar fijo, no se podría:

- Mandar la cerveza al bar y la hamburguesa a cocina en la misma orden.
- Tener varias cocinas (por ejemplo cocina caliente y cocina fría).
- Vender el sistema a una cocina oculta con un solo punto de producción, o a una panadería con otro tipo de flujo.

## 2. Configuración de un punto de producción

| Campo | Descripción |
|---|---|
| Nombre | "Cocina", "Bar", "Parrilla", "Postres" |
| Restaurante | A cuál pertenece |
| Tipo | Cocina, bar, otro (informativo) |
| Pantallas | Una o varias pantallas KDS vinculadas |
| Impresora | Impresora asignada para tirillas (`19A`) |
| Imprime al abrir | Sí o no |
| Salta "en proceso" | Si es sí, pasa de `nuevo` a `despachado` directamente (bebidas simples) |
| Sonido y alertas | Configuración de avisos |
| Tiempo objetivo | Opcional, para alertas de demora |
| Activo | Sí o no |

## 3. Cómo se decide a dónde va cada ítem

Orden de prioridad:

1. **Producto → punto de producción** (configurado en `12`). Cada producto tiene un punto de producción principal.
2. Si el producto no tiene uno, se usa el **punto de producción por defecto de su categoría** (`13`).
3. Si tampoco, se usa el **punto de producción por defecto de la zona** (`09`).
4. Si no hay ninguno, el ítem se considera de **despacho directo**: no pasa por producción y se marca despachado de inmediato (por ejemplo una gaseosa de nevera). Esto evita bloquear la orden esperando algo que nadie prepara.

El servidor resuelve el destino **al crear el ítem** y lo guarda en el ítem. Si luego se cambia la configuración del producto, **las órdenes en curso no cambian**.

## 4. División en comandas

Una orden con ítems de varios puntos de producción se divide en **una comanda por punto de producción**:

- Cada comanda tiene sus propios ítems y su propio estado (los estados viven en el ítem, `16`).
- La orden no queda `lista` hasta que **todas** sus comandas lo estén.
- El mesero ve en su tablet el avance de cada comanda por separado.

**Ejemplo:** una orden con hamburguesa (cocina) y cerveza (bar) genera dos comandas. El bar puede despachar la cerveza antes de que cocina termine la hamburguesa.

## 5. Zonas y puntos de producción

- Una zona tiene un punto de producción **por defecto**, pero eso **no** impide que sus productos vayan a otros.
- Un punto de producción puede atender **varias zonas** (la cocina atiende comida corriente y comida rápida).
- Una zona de **bar** puede usar solo el punto de producción "Bar".

## 6. Casos especiales

| Caso | Tratamiento propuesto |
|---|---|
| Producto sin preparación (bebida embotellada) | Despacho directo (sección 3) |
| Producto preparado en dos lugares (pizza en cocina + postre en postres) | Son dos ítems distintos; no se divide un ítem |
| Combo con ítems de varios puntos | Cada componente se enruta por su producto |
| Cocina cerrada fuera de horario | Las órdenes de ese punto no se aceptan o se avisan; configurable por horario |
| Punto de producción desconectado | Las comandas se acumulan; la tablet del mesero avisa que no hay confirmación (`17`) |

## 7. Tirilla y punto de producción

Cada punto de producción tiene su **impresora** propia (o comparte una). La tirilla de comanda se imprime en la impresora del punto donde se prepara. Detalle en `19A`.

## 8. Reglas importantes (resumen)

Detalle en `36`.

- Todo ítem queda asignado a un punto de producción o a despacho directo.
- Un punto de producción solo ve y modifica los ítems que le pertenecen.
- No se puede desactivar un punto de producción con comandas abiertas sin resolverlas.

## 9. Preguntas abiertas

- ¿Un mismo producto puede ir a **distintos** puntos según la zona o la hora? (Recomiendo no en el MVP.)
- ¿Los modificadores pueden cambiar el destino (por ejemplo "con alcohol" va al bar)? (Recomiendo no en el MVP.)
- ¿Se necesita un puesto que **reciba y reparta** todo (un "pase")? (Fuera del MVP.)
