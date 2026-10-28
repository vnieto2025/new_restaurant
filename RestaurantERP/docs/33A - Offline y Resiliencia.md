# 33A - Offline y Resiliencia

**Estado:** Propuesto (diseño en MVP; implementación completa en fase 2)

Qué pasa cuando **falla internet, un dispositivo o el servidor**. Un restaurante no puede detenerse porque se cayó la red. Este documento define qué se **garantiza**, qué se **degrada** y qué se **bloquea**.

## 1. Escenarios de falla

| # | Escenario | Frecuencia esperada | Impacto |
|---|---|---|---|
| 1 | Se cae internet en **todo el local** | Media | Alto: nadie ve ni envía órdenes |
| 2 | Falla **una tablet** o su Wi-Fi | Alta | Medio: un mesero sin herramienta |
| 3 | Se desconecta **la pantalla de cocina** | Media | Alto: comandas sin ver |
| 4 | Se cae **el servidor** o el proveedor de nube | Baja | Muy alto |
| 5 | Falla **un servicio externo** (pasarela, WhatsApp, facturación) | Media | Bajo a medio |
| 6 | Se cae **la impresora** | Alta | Medio (`19A`) |
| 7 | Conexión **lenta o intermitente** | Muy alta | Medio: duplicados, esperas |

## 2. Qué debe seguir funcionando según el escenario

| Escenario | Qué se garantiza | Qué se degrada |
|---|---|---|
| **1. Sin internet en el local** | Las pantallas **avisan claramente** que no hay conexión; lo ya cargado se mantiene visible | No se pueden **enviar** nuevas órdenes ni cobros con el servidor |
| **2. Una tablet falla** | Otra tablet o dispositivo de la zona puede tomar su lugar; el estado vive en el servidor | La tablet caída no ve cambios |
| **3. Cocina desconectada** | La tablet del mesero indica "sin confirmación de cocina" (`17`); la pantalla de cocina **no borra** lo que ya muestra y reconecta sola | Mientras tanto, órdenes nuevas no llegan |
| **4. Servidor caído** | Pantallas muestran "servicio no disponible"; **plan manual** (sección 5) | Todo se detiene |
| **5. Servicio externo caído** | **Nunca bloquea** la operación (`RN-FAC-06`, `RN-PAG-04`, `RN-NOT-01`) | Se difieren facturas, notificaciones; el cliente paga en caja |
| **6. Impresora caída** | La comanda sigue en pantalla; el trabajo de impresión queda en cola | Sin tirilla temporalmente |
| **7. Red lenta** | Acciones con **idempotencia**: reintentar no duplica (RG-20) | Más espera; botones bloqueados mientras se envía |

## 3. Qué se construye en cada fase

| Capacidad | MVP | Fase 2 | Fase 3 |
|---|:-:|:-:|:-:|
| Detección y aviso de falta de conexión | ✔ | ✔ | ✔ |
| Reconexión automática y re-sincronización del estado | ✔ | ✔ | ✔ |
| Idempotencia en creación de órdenes y pagos | ✔ | ✔ | ✔ |
| Borrador de orden **local** si no se pudo enviar | ✔ | ✔ | ✔ |
| Cola de envío automático al reconectar ("bandeja de salida") | — | ✔ | ✔ |
| Caché de carta y datos para abrir sin red | ✔ (lectura) | ✔ | ✔ |
| Operación local **sin servidor** (modo isla en el local) | — | — | Evaluar |
| Conmutación automática a otra región o respaldo caliente | — | — | Evaluar |

> **Decisión importante `[POR CONFIRMAR]`:** un **modo totalmente offline** (tomar y cobrar órdenes sin internet y sincronizar después) es **muy costoso** y propenso a conflictos. En el MVP se asume que **un restaurante necesita internet** para operar, se mide cuánto les afecta en el piloto, y se decide en fase 2 si vale la pena (por ejemplo, un nodo local).

## 4. Técnicas de resiliencia

| Técnica | Para qué |
|---|---|
| **Idempotency-Key** en creación | Reintentar sin duplicar |
| **Bandeja de salida (outbox)** en el cliente | Guardar acciones pendientes y enviarlas al reconectar (fase 2) |
| **Versión de entidad** | Detectar conflictos cuando dos dispositivos editan lo mismo |
| **Estado desde el servidor** | Eventos como aviso, y volver a pedir el estado al reconectar (`04`) |
| **Service worker / PWA** | Cargar la aplicación y la carta aunque la red esté mala |
| **Reintentos con espera creciente** | Evitar saturar al servidor al reconectar |
| **Degradación elegante** | Cada función externa es opcional para vender |
| **Colas en el backend** | Facturación, notificaciones e impresión no bloquean el cobro |
| **Pruebas de caos** (fase 2) | Cortar conexión a propósito y ver qué pasa |

## 5. Plan manual de contingencia (documentado para el restaurante)

Cuando **el sistema no está disponible**, el restaurante debe saber qué hacer:

1. **Comandas en papel** (talonario de respaldo) por zona.
2. Anotar **mesa, ítems, hora y mesero**.
3. Cobrar con los medios habituales.
4. Al volver el sistema, **registrar** lo ocurrido como **ventas manuales** con motivo "contingencia" (`20`).
5. Reportar el incidente al soporte.

Este plan se incluye en el **onboarding** (`41`) y se imprime como guía rápida.

## 6. Comunicación al usuario

- Banner claro y persistente: "Sin conexión. Las órdenes nuevas no se enviarán."
- Indicador por dispositivo: conectado, reconectando, sin conexión.
- Lo que **sí** se puede hacer sin red se indica.
- Al reconectar: "Conexión restablecida", con revisión automática de lo pendiente.

## 7. Indicadores a medir en el piloto

- Frecuencia y duración de caídas de internet en los locales reales.
- Órdenes que quedaron como borrador local y cuántas se reenviaron.
- Reintentos y duplicados evitados.
- Tiempo de reconexión de las pantallas de cocina.

## 8. Reglas

- **RN-OFF-01.** Ninguna orden se muestra como "enviada" hasta que el servidor la confirme.
- **RN-OFF-02.** Un reintento nunca duplica órdenes ni pagos.
- **RN-OFF-03.** Una pantalla desconectada nunca presenta datos viejos como actuales.
- **RN-OFF-04.** Las fallas de servicios externos no detienen ventas ni cocina.
- **RN-OFF-05.** Toda contingencia manual se registra después con motivo.

## 9. Preguntas abiertas

- ¿Qué tan estable es el internet en los locales del público objetivo?
- ¿Se ofrece como opcional un **router de respaldo con datos móviles**? (Es una recomendación al cliente, no del software.)
- ¿Qué tan crítico es el modo offline total para los primeros clientes?
