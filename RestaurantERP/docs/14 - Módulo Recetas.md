# 14 - Módulo Recetas

**Estado:** Propuesto

Una **receta** dice qué insumos y en qué cantidad componen un producto. Conecta **ventas** con **inventario** y permite calcular el **costo** y el **margen** de cada plato. Es **opcional**: un restaurante puede vender "solo pedidos" sin recetas, y el módulo se activa con `inventario` (`02A`).

## 1. Conceptos

| Concepto | Descripción |
|---|---|
| **Insumo** | Materia prima o artículo comprado (`22`) |
| **Preparación (sub-receta)** | Algo que se elabora y a su vez se usa en otras recetas: salsa, masa, caldo |
| **Receta** | Lista de insumos y preparaciones con cantidades que produce un producto |
| **Rendimiento** | Cuántas porciones o cuánta cantidad produce una receta |
| **Merma técnica** | Pérdida normal del proceso (limpiar, cocinar, deshuesar) |

## 2. Datos de una receta

| Campo | Descripción |
|---|---|
| Producto o preparación | A qué pertenece |
| Ingredientes | Insumo o sub-receta + cantidad + unidad |
| Rendimiento | Porciones o cantidad resultante |
| Merma | Porcentaje opcional por ingrediente |
| Variantes | Receta distinta por tamaño (pizza personal vs. familiar) |
| Modificadores | Insumos que suma o resta cada modificador |
| Costo calculado | Suma del costo de los ingredientes con su costo actual (`22`) |

## 3. Costeo y margen

```
Costo del plato = Σ (cantidad de cada insumo × costo del insumo) / rendimiento
Margen = Precio de venta (sin impuesto) − Costo del plato
% de margen = Margen / Precio de venta (sin impuesto)
```

El costo se recalcula cuando cambia el **costo de un insumo** (por una compra, `23`). El sistema debe mostrar **qué platos pierden margen** cuando sube un insumo.

## 4. Cuándo se descuenta el inventario

Es una decisión con consecuencias contables. Opciones:

| Momento | Pros | Contras |
|---|---|---|
| **Al crear la orden** | Simple | Descuenta lo que se cancela |
| **Al pasar a `en_proceso`** | Refleja consumo real; las cancelaciones antes de abrirse no descuentan | Un poco más de lógica |
| **Al `despachar`** | Refleja lo producido | Si se cancela en proceso, el insumo ya se usó pero no se descuenta |
| **Al pagar** | Alineado con la venta | Desfasado respecto a la producción |

**Recomendación:** descontar al pasar a **`en_proceso`**, y registrar como **pérdida** (merma) lo cancelado después de ese punto. `[POR CONFIRMAR]` con un contador y con restaurantes.

## 5. Productos sin receta

Muchos productos no se fabrican (una gaseosa de botella). Pueden descontar inventario **directamente** como "producto de reventa" (`22`), sin pasar por una receta.

## 6. Carga de recetas: advertencia práctica

Cargar recetas es **trabajo pesado** para un restaurante pequeño. Si el módulo exige recetas completas para funcionar, **nadie lo adoptará**. Por eso:

- Todo funciona con recetas **parciales** (solo los insumos principales).
- El sistema muestra qué porcentaje de las ventas está cubierto por recetas.
- El onboarding (`41`) ofrece cargar recetas gradualmente.

## 7. Reglas

- **RN-REC-01.** Una receta nunca modifica el precio de venta; solo informa costo y margen.
- **RN-REC-02.** No se permiten recetas circulares (una preparación que se contiene a sí misma).
- **RN-REC-03.** Cambiar una receta afecta solo órdenes **futuras**.
- **RN-REC-04.** Las unidades se convierten con factores definidos en `22`; no se mezclan unidades incompatibles.
- **RN-REC-05.** Cuando falta la receta de un producto, no se descuenta inventario y se informa en el reporte de cobertura.

## 8. Preguntas abiertas

- ¿Se permite editar recetas con órdenes abiertas?
- ¿Cómo se registran platos del día con ingredientes variables? (Caso común de comida corriente.)
- ¿Descuento por unidad de producción (batch) o por porción?
