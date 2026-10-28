# 07 - Módulo Restaurantes

**Estado:** Propuesto

Un **restaurante** es un local o negocio concreto de una empresa. Es la unidad de operación: tiene zonas, personal, carta, caja y **contrato propio** (`02A`).

## 1. Datos del restaurante

| Campo | Descripción |
|---|---|
| Nombre y tipo | Restaurante, comida rápida, bar, panadería, cocina oculta, otro |
| Dirección y contacto | Para tirillas, carta digital y domicilios |
| Datos fiscales | Razón social, documento, régimen; pueden diferir de la empresa |
| Zona horaria | Por defecto la de la empresa (RG-08) |
| **Hora de inicio de jornada** | Define el "día" operativo (RG-09), por ejemplo 06:00 |
| Moneda | Por defecto la de la empresa |
| Horario de atención | Por día de la semana, con excepciones (festivos) |
| Estado | `activo`, `pausado`, `cerrado` temporal, `inactivo` |
| Contrato | Módulos activos y vigencia (`02A`) |

## 2. Configuración propia del restaurante

| Tema | Detalle |
|---|---|
| Impuestos aplicables | Tipos y tasas configurables con vigencia (`21A`) |
| Propina | Si se sugiere, valor sugerido, dónde se cobra (`26A`) |
| Canales activos | Tablet, QR de mesa, mostrador, QR rápido, WhatsApp, domicilio, plataformas |
| Modo de aceptación por defecto | Libre / con aprobación / mesa abierta (`10A`) |
| Pagos | Medios aceptados, pasarela (`20A`) |
| Impresión | Impresoras y puntos de producción asociados (`19A`) |
| Domicilios | Zonas de envío y tarifas (`15B`) |
| Textos | Mensajes de la carta, pie de tirilla, políticas |
| Branding básico | Logo y color principal para la carta digital |

## 3. Elementos que se crean automáticamente

Al crear un restaurante, el sistema genera:

- Una **mesa externa** (`10`), única por restaurante.
- Un **punto de producción** por defecto "Cocina" (`19`).
- Una **zona** inicial editable.
- Roles base (`29`).

## 4. Estados y efecto

| Estado | Efecto |
|---|---|
| **Activo** | Opera normal |
| **Pausado** | No acepta órdenes nuevas por QR, web ni WhatsApp (mensaje en la carta); las tablets pueden seguir cerrando cuentas |
| **Cerrado temporal** | Fuera de horario, sin órdenes nuevas |
| **Inactivo** | Sin operación; datos conservados |

La **pausa** es una función operativa importante: el administrador la activa cuando la cocina se satura o falta un insumo clave.

## 5. Varios restaurantes en una empresa

- Cada restaurante tiene **carta, zonas, personal asignado y caja propios**.
- Productos y categorías se pueden **copiar** entre restaurantes de la misma empresa (fase 2) para no cargar la carta varias veces.
- Los usuarios se asignan a uno o varios restaurantes.

## 6. Reglas

- **RN-RES-01.** Todo restaurante tiene contrato propio, aunque comparta empresa.
- **RN-RES-02.** Cada restaurante tiene exactamente una mesa externa activa (`RN-MES-02`).
- **RN-RES-03.** No se puede desactivar un restaurante con cuentas abiertas ni turnos de caja sin cerrar.
- **RN-RES-04.** La hora de inicio de jornada solo se puede cambiar entre jornadas, no durante una abierta.
- **RN-RES-05.** Cambios de impuestos solo aplican a órdenes nuevas desde su vigencia (RG-06).

## 7. Preguntas abiertas

- ¿Un restaurante puede tener cartas distintas por horario (desayuno, almuerzo, cena)? Ver `11`.
- ¿Varias razones sociales dentro de la misma empresa son un caso real en tu público objetivo?
