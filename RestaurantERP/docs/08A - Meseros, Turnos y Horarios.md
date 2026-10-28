# 08A - Meseros, Turnos y Horarios

**Estado:** Propuesto

Cubre tu requisito de que cada mesero tenga un usuario donde se registre **todo lo que hace en el día**, un **informe diario detallado**, y **horarios** de mesas, zonas y meseros.

## 1. Asignación de meseros a zonas

| Concepto | Descripción |
|---|---|
| **Asignación** | Relación mesero–zona; una zona puede tener uno o muchos meseros y un mesero puede cubrir varias zonas |
| **Asignación por turno** | Quién está a cargo hoy de qué zona (la que importa para la operación y el informe) |
| **Responsable de una mesa** | El mesero que abre la sesión de la mesa; puede transferirse con registro |

Cuando hay varios meseros en una zona, las órdenes se atribuyen al **mesero que las creó o aprobó**, y la mesa conserva al responsable de la sesión.

## 2. Turno del mesero

Un **turno** registra cuándo un mesero está activo en una jornada:

| Campo | Descripción |
|---|---|
| Inicio y fin | Marcado al identificarse (PIN) y al cerrar turno o por cierre de jornada |
| Zonas cubiertas | Zonas en las que trabajó |
| Estado | `abierto`, `cerrado` |

El turno alimenta el informe diario y, en fase 2, la **distribución de propinas** (`26A`). `[POR CONFIRMAR]`: no es un control de asistencia laboral ni reemplaza el registro legal de horas; es operativo.

## 3. Informe diario por mesero

Por **jornada operativa** y por mesero:

| Bloque | Contenido |
|---|---|
| **Atención** | Mesas atendidas, número de órdenes, ítems vendidos, tiempo promedio de entrega |
| **Ventas** | Total vendido, ticket promedio, ventas por zona |
| **Dinero manejado** | Total por mesa, formas de pago, descuentos otorgados |
| **Propinas** | Propina cobrada en sus cuentas (fase 2) |
| **Excepciones** | Cancelaciones, anulaciones, reaperturas, devoluciones, cuentas sin cobrar |
| **Detalle por mesa** | Hora de apertura y cierre, órdenes, total, medio de pago |

Debe poder **imprimirse** y **exportarse** (`26`). Quién lo ve: el administrador de restaurante y, opcionalmente, el propio mesero (solo el suyo).

> **Criterio de diseño:** el informe es una **herramienta de gestión**, no de vigilancia. Conviene que el restaurante lo comunique así a su personal. `[POR CONFIRMAR]`

## 4. Horarios

| Tipo | Qué controla |
|---|---|
| **Horario del restaurante** | Cuándo está abierto (`07`) |
| **Horario de zona** | Cuándo una zona acepta órdenes (por ejemplo el bar solo de noche) |
| **Horario de mesa** | Mesas que solo se habilitan en ciertos horarios (terraza, eventos) |
| **Horario de carta** | Cartas por franja (desayuno, almuerzo) (`11`) |
| **Horario del mesero** | Planificación opcional de quién trabaja qué día y zona |

**MVP:** horario de restaurante, de zona y de carta. El horario planificado de meseros y de mesas entra en fase 2.

Los horarios usan la zona horaria del restaurante y la jornada operativa (RG-08, RG-09), incluso cuando cruzan la medianoche.

## 5. Reglas

- **RN-MSR-01.** Toda orden creada desde una tablet se atribuye al mesero identificado con PIN.
- **RN-MSR-02.** Un mesero solo ve y opera las mesas de sus zonas asignadas.
- **RN-MSR-03.** Al cerrar la jornada, los turnos abiertos se cierran automáticamente y se marcan como tales.
- **RN-MSR-04.** No se puede cerrar el turno de un mesero con cuentas sin cobrar sin reasignarlas.
- **RN-MSR-05.** La transferencia de una mesa entre meseros queda registrada.

## 6. Preguntas abiertas

- ¿El mesero cobra en la mesa o solo caja cobra? Define quién "maneja dinero" en el informe.
- ¿Cómo se atribuye una orden de QR aprobada por otro mesero? (Recomiendo al responsable de la mesa.)
- ¿Se desea alerta al administrador cuando un mesero tiene muchas anulaciones?
