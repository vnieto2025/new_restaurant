# 17A - Canales de Pedido

**Estado:** Propuesto

Cada canal es una forma distinta de **crear** una orden. Todos producen la misma entidad (`15`) y siguen el mismo flujo de producción (`17`). Este documento fija qué cambia entre canales.

> **Vocabulario:** el título del archivo conserva "Pedido" por el nombre original de la estructura; en el sistema y el resto de la documentación el término es **Orden** (`01`).

## 1. Matriz de canales

| Canal | Quién crea | Mesa | Datos del cliente | Aprobación | Pago | Fase |
|---|---|---|---|---|---|---|
| **Tablet de zona** | Mesero | Real | Ninguno | No | Al final, en caja | MVP |
| **QR de mesa** | Cliente | Real (por token) | Opcional | Configurable por zona (`10A`) | Al final, en caja | MVP |
| **Mostrador / mesa externa** | Cajero o encargado | Externa | Opcional | No | En el momento o al entregar | MVP |
| **QR de pedidos rápidos** | Cliente | Externa | Nombre y teléfono | Opcional | En línea o en mostrador | Fase 1 (cobro en mostrador) / Fase 2 (en línea) |
| **WhatsApp** | Encargado | Externa | Nombre, teléfono, dirección y zona de envío si hay domicilio | No | Contra entrega o en línea | Fase 1 (captura manual) / Fase 2 (notificaciones automáticas) |
| **Domicilio web / redes** | Cliente | Externa | Nombre completo, dirección, teléfono | Opcional | En línea o contra entrega | Fase 2 |
| **Plataformas (Rappi, Uber Eats...)** | Integración | Externa | Los que entregue la plataforma | Normalmente automática | La plataforma cobra | Fase 3 |

## 2. Detalle por canal

### 2.1 Tablet de zona
- Muestra solo las mesas de la zona del mesero.
- Usa la carta de la zona.
- Es el canal más rápido y con más control; sirve de referencia para los demás.

### 2.2 QR de mesa
- Contexto fijado por el token (`10A`).
- Respeta el modo de la zona: libre, con aprobación o mesa abierta.
- Las órdenes de varios clientes de la misma mesa se agrupan en la **sesión de mesa**.
- El cliente ve el estado de su orden.

### 2.3 Mostrador / mesa externa
- La **mesa externa** es una mesa estándar por restaurante, sin ubicación física.
- Permite ingresar una orden sin depender de una mesa.
- Se usa para personas que llegan, compran y se van.
- Al despachar, la tirilla indica claramente que es **orden externa** y el nombre o número de la persona.

### 2.4 QR de pedidos rápidos
- QR fijo en pared o mostrador.
- Abre una carta de "para llevar".
- Pide **nombre y teléfono** para avisar cuando esté lista.
- Entra como orden externa; la tirilla indica "externa".

### 2.5 WhatsApp
- **Fase 1:** una persona encargada recibe el mensaje por WhatsApp (en su propio celular o WhatsApp Web) y **crea la orden manualmente** en el sistema.
- Se capturan nombre, teléfono, dirección, productos y **zona de envío**.
- Según la zona de envío se calcula el costo de domicilio. Si el cliente recoge, no se cobra envío.
- **Fase 2:** al estar lista o al salir, el sistema notifica por WhatsApp (ver `31B`).

> **Advertencia importante:** automatizar mensajes por WhatsApp con la **API oficial** implica registro, plantillas aprobadas y costos por conversación. Alternativas no oficiales pueden provocar el **bloqueo del número** del restaurante. No decidir esto sin revisar `31B`. `[POR CONFIRMAR]`

### 2.6 Domicilio web / redes
- El cliente llega por un enlace o QR de domicilios.
- Ve la carta de domicilio (misma carta configurada).
- Al final, el sistema detecta que es externo y solicita: **nombre completo, dirección, teléfono** y zona de envío.
- La factura incluye valor, domicilio e impuestos.
- Cuando cocina despacha, queda disponible para el **domiciliario**.
- El sistema avisa al cliente por WhatsApp que su orden salió (fase 2).

### 2.7 Plataformas externas
- Fase 3. Recibir órdenes de Rappi, Uber Eats y similares, normalmente mediante un agregador o una integración propia.
- Requiere acuerdo con cada plataforma. **No se asume que existan APIs abiertas.** Ver `31A`.

## 3. Qué es común y qué no

| Aspecto | Igual en todos los canales | Cambia por canal |
|---|---|---|
| Estados y colores | Sí | — |
| División en comandas | Sí | — |
| Cálculo de precios en servidor | Sí | — |
| Auditoría | Sí | — |
| Datos del cliente | — | Sí |
| Modo de aprobación | — | Sí |
| Momento y forma de pago | — | Sí |
| Quién entrega | — | Sí (mesero, cajero o domiciliario) |
| Tirilla | Mismo formato base | Etiqueta de canal visible |

## 4. Tirilla según el canal

La tirilla de producción siempre muestra: **número de orden, canal, mesa o nombre/número del cliente externo, zona, hora e ítems con notas y modificadores**. Para externas se añade teléfono (no dirección completa en cocina) y marca **PARA LLEVAR** o **DOMICILIO**. Detalle en `19A`.

## 5. Riesgos por canal

| Canal | Riesgo | Mitigación |
|---|---|---|
| QR de mesa | Órdenes falsas | Aprobación y límites (`10A`) |
| QR rápido y domicilio web | Spam, datos falsos | Límites, validación de teléfono, aprobación opcional |
| WhatsApp manual | Errores de transcripción | Pantalla con confirmación y datos del cliente reutilizables |
| Domicilio | Dirección mal capturada | Validación de zona de envío y confirmación al cliente |
| Plataformas | Dependencia externa | Adaptadores (ADR-011) y modo manual de contingencia |

## 6. Preguntas abiertas

- ¿Quién atiende WhatsApp en un restaurante pequeño? ¿El mismo cajero?
- ¿Se desea que el cliente de domicilio web pueda registrarse y guardar sus direcciones? (Recomiendo sí, en fase 2.)
- ¿Cómo se maneja la hora de recogida programada? (Fuera del MVP.)
