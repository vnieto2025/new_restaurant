# 27 - Dashboard

**Estado:** Propuesto

El **dashboard** es la primera pantalla del administrador y del dueño: una vista rápida de **cómo va el negocio hoy**. Los reportes detallados están en `26`.

## 1. Principios

- **Responde en cinco segundos** si el día va bien o mal.
- Cada número va **acompañado de su comparativo** (`26`).
- **Una pantalla por rol**: cada uno ve lo que necesita para decidir.
- Solo muestra **módulos contratados** (`02A`).
- Se actualiza **en vivo** durante la jornada.

## 2. Dashboard del administrador de restaurante

| Bloque | Contenido |
|---|---|
| **Ventas de hoy** | Total, órdenes, ticket promedio; comparativo con el mismo día de la semana pasada |
| **Operación en vivo** | Órdenes activas por estado (nuevo, en proceso, listas), mesas ocupadas |
| **Tiempos** | Tiempo promedio de preparación y de entrega de hoy |
| **Por canal** | Participación de mesa, mostrador, domicilio, WhatsApp |
| **Productos del día** | Los más vendidos y los agotados |
| **Alertas** | Stock bajo, comandas demoradas, cancelaciones altas, diferencias de caja, mesas con cuenta abierta mucho tiempo |
| **Caja** | Turno abierto, efectivo esperado, diferencias pendientes |
| **Atajos** | Pausar restaurante, marcar agotado, ver informe del día |

## 3. Dashboard del administrador de empresa

| Bloque | Contenido |
|---|---|
| **Ventas consolidadas** | Total de hoy y del periodo, por restaurante |
| **Comparativo entre restaurantes** | Ranking y variación |
| **Alertas por restaurante** | Cuál necesita atención |
| **Estado de contratos** | Vigencia y módulos por restaurante |

## 4. Dashboard del cajero y del encargado de externos

- Turno actual, efectivo, cuentas pendientes de cobro.
- Órdenes externas activas y entregas pendientes.
- Accesos directos a nueva orden y a cobro.

## 5. Dashboard del mesero

Su vista de trabajo es la **tablet de zona** (`33`). Opcionalmente, un resumen de **su jornada**: mesas atendidas, ventas, propinas acumuladas.

## 6. Dashboard del superadministrador de plataforma (interno)

Empresas activas, restaurantes, módulos, estado de salud del sistema, errores, uso. No expone datos operativos de los clientes.

## 7. Reglas

- **RN-DAS-01.** Un dashboard nunca muestra datos de restaurantes o módulos a los que el usuario no tiene acceso.
- **RN-DAS-02.** Los números de un dashboard coinciden con los reportes de `26` del mismo periodo.
- **RN-DAS-03.** Las alertas tienen umbrales configurables y pueden silenciarse.
- **RN-DAS-04.** Si no hay conexión con el servidor, el dashboard lo indica y no muestra datos viejos como actuales.

## 8. Preguntas abiertas

- ¿Qué tres números mira primero un dueño al abrir? Preguntar en entrevistas.
- ¿Se envía un resumen diario por WhatsApp o correo? (Fase 2.)
- ¿Los umbrales de alerta tienen valores sugeridos por defecto?
