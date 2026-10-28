# 15A - Pedidos Externos y Para Llevar

**Estado:** Propuesto

Cubre las órdenes que **no se sirven en una mesa**: para llevar, mostrador, WhatsApp, domicilio y, más adelante, plataformas. Todas usan la **mesa externa** (`10`) y siguen el flujo normal de producción (`17`). Los canales están en `17A`; los domicilios en `15B`.

> **Vocabulario:** el título conserva "Pedidos" del nombre original; el término oficial es **Orden** (`01`).

## 1. Tipos de orden externa

| Tipo | Quién la crea | Entrega | Cobro |
|---|---|---|---|
| **Para llevar en el local** | Cajero o cliente por QR rápido | El cliente recoge en mostrador | En el momento |
| **Mostrador (compra y se va)** | Cajero | Inmediata | En el momento |
| **Para recoger (pedida a distancia)** | Encargado o cliente | El cliente pasa al local | Al recoger o en línea |
| **Domicilio** | Encargado o cliente | Domiciliario | Contra entrega o en línea |

## 2. Datos mínimos por tipo

| Tipo | Obligatorios | Opcionales |
|---|---|---|
| Mostrador | Ítems | Nombre o número de turno |
| Para llevar | Ítems, nombre | Teléfono |
| Para recoger | Ítems, nombre, **teléfono** | Hora de recogida |
| Domicilio | Ítems, nombre completo, **teléfono, dirección, zona de envío** | Indicaciones, referencia |

## 3. Captura de una orden por WhatsApp (fase 1, manual)

1. La persona encargada recibe el mensaje en su WhatsApp.
2. En el sistema elige **Nueva orden externa**.
3. Busca al cliente por teléfono; si existe, **se autocompletan** nombre y dirección guardada (`25`).
4. Selecciona productos, modificadores y notas.
5. Indica si es **domicilio** o **recoger**; si es domicilio elige la **zona de envío** y el sistema suma el costo.
6. Confirma; la orden entra a producción.
7. Al estar lista, la encargada **avisa al cliente**. En fase 1 se facilita con un botón que abre WhatsApp con un **mensaje prellenado** (`31B`), sin automatizar nada.

## 4. Identificación en producción

La tirilla y la tarjeta de cocina muestran, de forma destacada:

- **PARA LLEVAR**, **MOSTRADOR**, **RECOGER** o **DOMICILIO**.
- Número de orden y **nombre o número de turno** del cliente.
- Teléfono (no la dirección completa en cocina).

## 5. Estados y entrega

Estados según `16`. Particularidades:

- `entregado` lo marca el **cajero** (recoger/mostrador) o el **domiciliario** (domicilio).
- Para domicilio, al despachar la cocina la orden aparece en la lista de **entregas pendientes** (`15B`).
- Una orden para recoger que no se retira en un tiempo definido genera alerta; el destino (descartar, pérdida) lo decide el administrador.

## 6. Pago

| Momento | Cómo |
|---|---|
| **En el momento** | Cobro en caja antes o al entregar |
| **Contra entrega** | El domiciliario recibe el dinero y lo rinde al cajero (`15B`, `20`) |
| **En línea** | Fase 2 (`20A`); la orden puede quedar "pendiente de pago" antes de pasar a producción |

## 7. Reglas

- **RN-EXT-01.** Una orden externa siempre se asocia a la mesa externa del restaurante.
- **RN-EXT-02.** Cada orden externa tiene su propia sesión (`10`).
- **RN-EXT-03.** Una orden de domicilio no se acepta sin zona de envío válida (`RN-ORD-12`).
- **RN-EXT-04.** Una orden para recoger no cobra envío (`RN-ORD-13`).
- **RN-EXT-05.** Los datos de contacto del cliente se usan solo para la gestión de esa orden y las notificaciones permitidas (`32A`).

## 8. Preguntas abiertas

- ¿Se permiten órdenes programadas para una hora futura? (Fuera del MVP.)
- ¿Hay un límite de órdenes externas simultáneas para no saturar la cocina?
- ¿Qué hacer con órdenes por recoger que no se retiran?
