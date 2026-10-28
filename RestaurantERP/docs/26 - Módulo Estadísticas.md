# 26 - Módulo Estadísticas

**Estado:** Propuesto

Responde a tu requisito de **información completa, con estadísticas no muy complejas pero bien informativas**, comparativos entre días y periodos, y **reportes gráficos e impresos**. La vista rápida para el dueño está en `27 - Dashboard`.

## 1. Principio

Pocas métricas, **bien definidas y bien comparadas**, valen más que muchas sin contexto. Cada número debe responder: *¿es bueno o malo?* Para eso siempre se acompaña de un **comparativo** (ayer, mismo día de la semana pasada, periodo anterior).

## 2. Definiciones (para que todos hablen de lo mismo)

| Métrica | Definición propuesta |
|---|---|
| **Venta** | Valor de las cuentas **pagadas** de la jornada, sin propina |
| **Venta neta** | Venta menos descuentos y devoluciones, antes de impuestos |
| **Ticket promedio** | Venta ÷ número de cuentas pagadas |
| **Órdenes** | Número de órdenes no canceladas |
| **Comensales** | Solo si se captura (opcional) |
| **Rotación de mesa** | Cuentas por mesa en una jornada |
| **Tiempo de preparación** | De `nuevo` a `despachado` (`16`) |
| **Tiempo de entrega** | De `despachado` a `entregado` |
| **Cancelaciones** | Ítems u órdenes cancelados sobre el total |
| **Margen** | Venta neta menos costo según recetas (`14`), cuando existen |

> Los reportes se agrupan por **jornada operativa**, no por día calendario (RG-09). `[POR CONFIRMAR]` si "venta" se mide al pagar la cuenta o al entregar la orden; recomiendo al pagar.

## 3. Dimensiones de análisis

Cada métrica se puede ver por: **restaurante, zona, mesa, canal, mesero, cajero, producto, categoría, hora del día, día de la semana, medio de pago, cupón, domiciliario**.

## 4. Reportes del MVP

| Reporte | Contenido | Quién lo usa |
|---|---|---|
| **Ventas del día / periodo** | Total y evolución, con comparativo | Dueño, administrador |
| **Productos más y menos vendidos** | Unidades y valor | Administrador |
| **Ventas por zona y por canal** | Dónde y cómo se vende | Administrador |
| **Informe por mesero** | Ver `08A` | Administrador, mesero (el suyo) |
| **Cierre de caja** | Por turno y por jornada (`20`) | Cajero, administrador |
| **Cancelaciones y anulaciones** | Quién, cuándo, por qué | Administrador |

## 5. Reportes de fases posteriores

| Reporte | Fase |
|---|---|
| Horas pico y mapa de calor de ventas | 2 |
| Tiempos de preparación y de entrega por punto de producción | 2 |
| Margen por plato y por categoría | 2 (con recetas) |
| Rentabilidad de cupones | 2 |
| Clientes: frecuentes, nuevos, inactivos | 2 |
| Rendimiento de domiciliarios | 2 |
| Comparativo entre restaurantes de una empresa | 2 |
| Inventario: stock crítico, mermas, variación de costos | 2 |
| Proyecciones y predicción | 3 (con cautela) |

## 6. Comparativos

- **Hoy vs. ayer** y **hoy vs. mismo día de la semana anterior** (el segundo es más justo).
- **Semana vs. semana anterior**, **mes vs. mes anterior**, **mes vs. mismo mes del año anterior**.
- **Rango personalizado** contra otro rango.
- Siempre con **porcentaje de variación** y marca clara cuando el periodo aún no termina.

## 7. Visualización

- Gráficos simples: **barras, líneas, tortas con pocos segmentos**, sin adornos.
- Tablas con **totales visibles** y ordenables.
- Un reporte debe poder verse en tablet y celular.
- Colores de estado reservados a estados de órdenes (`33`, `34`); los gráficos usan otra paleta.

## 8. Impresión y exportación

| Formato | Uso |
|---|---|
| **Impresión** | Informe diario y de turno, en hoja y, cuando aplique, en tirilla (`19A`) |
| **PDF** | Para enviar al dueño o al contador |
| **Excel / CSV** | Para análisis propio |

## 9. Consideraciones técnicas

- Los reportes consultan datos ya cerrados (**jornada cerrada**) con tablas de **resumen precalculadas** para ser rápidos; la jornada en curso se calcula en vivo.
- Los reportes pesados se generan como **tarea en segundo plano** y se notifican al terminar.
- Un reporte solo incluye **módulos contratados** y respeta los permisos del usuario (`29`).
- Las cifras de un reporte deben **cuadrar con caja** (`20`): una diferencia es un error del sistema.

## 10. Reglas

- **RN-REP-01.** Toda cifra de ventas de un reporte se reconcilia con las cuentas pagadas.
- **RN-REP-02.** Los reportes de jornadas cerradas no cambian; las correcciones se registran como ajustes.
- **RN-REP-03.** Un usuario ve solo los reportes de los restaurantes y módulos a los que tiene acceso.
- **RN-REP-04.** Todo comparativo indica los periodos comparados.

## 11. Preguntas abiertas

- ¿Qué reporte mira el dueño cada día? Preguntar en las entrevistas (`38`).
- ¿Se necesita enviar un resumen diario por WhatsApp o correo? (Valioso y simple, fase 2.)
- ¿Cuánto histórico se conserva en línea?
