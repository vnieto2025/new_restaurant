# 33 - UX General

**Estado:** Propuesto

Principios de experiencia de uso para **todas** las aplicaciones. Los componentes concretos están en `34`. El público: personal de restaurante con poca formación técnica, trabajando de pie, con prisa y a veces con las manos ocupadas.

## 1. Principios

1. **Pocos toques.** Tomar una orden de una mesa debe poder hacerse en pocos toques; las acciones frecuentes siempre a un toque.
2. **Táctil primero.** Objetivos grandes, separados y con buen contraste; nada que dependa de pasar el cursor.
3. **Lo importante, grande.** Número de orden, mesa y estado deben leerse a un metro de distancia.
4. **El color significa algo y siempre lo mismo** (RG-24); además se acompaña de **texto o ícono**, nunca solo color (accesibilidad).
5. **Confirmaciones solo donde cuesta.** Cancelar o anular pide confirmación; añadir un producto, no.
6. **Errores que ayudan.** Decir qué pasó y qué hacer, sin tecnicismos.
7. **Siempre visible el estado de conexión.**
8. **Lo mismo en cualquier dispositivo del rol.** Una tablet o una pantalla de cocina se usan igual en cualquier local.
9. **Sin sorpresas durante el servicio.** Nada se mueve de sitio ni cambia de repente mientras alguien está tocando.
10. **Aprender haciendo.** Estados vacíos con guía, ayudas contextuales cortas, sin manuales largos.

## 2. Experiencias por aplicación

| Aplicación | Prioridad de diseño |
|---|---|
| **Tablet de mesero** | Velocidad; mesas legibles; cambio de mesero con PIN en segundos; ítems frecuentes accesibles |
| **Cocina / bar (KDS)** | Legibilidad a distancia; mínimo de toques; tema oscuro disponible; sonido de alerta (`18`) |
| **Caja / mostrador** | Teclado numérico claro; cobro rápido; división de cuenta fácil; resumen del turno |
| **Administración** | Claridad y orden; formularios cortos; vistas previas; importación masiva |
| **Carta digital** | Ligera, rápida y simple; **cero registro** para pedir en mesa; funciona con mala señal (`11`) |
| **Domiciliario (fase 2)** | Una mano, letra grande, solo lo necesario |

## 3. Patrones comunes

- **Navegación:** pocas secciones principales por rol; barra inferior en móvil y tablet, lateral en administración.
- **Búsqueda:** siempre presente en listas largas (productos, clientes).
- **Selección rápida:** favoritos, recientes y atajos para productos más pedidos.
- **Formularios:** pocos campos, valores por defecto, teclado adecuado por tipo de campo.
- **Listas y tablas:** orden, filtros y totales visibles; en móvil, tarjetas.
- **Carga y espera:** indicadores claros; nunca una pantalla vacía sin explicación.
- **Deshacer:** donde sea posible, en lugar de preguntar antes.

## 4. Color y estados

| Estado | Color | Texto o ícono |
|---|---|---|
| Pendiente de aprobación | Gris | "Por aprobar" |
| Nuevo | Azul claro | "Nuevo" |
| En proceso | Amarillo | "En proceso" |
| Despachado | Verde claro | "Listo" |
| Entregado | Verde | "Entregado" |
| Cancelado / perdido | Rojo | "Cancelado" |

- Las **alertas de tiempo** usan otro lenguaje visual (contador, borde, parpadeo suave), no estos colores.
- Se garantiza **contraste suficiente**; valores exactos de la paleta en `34`.

## 5. Conexión y errores

| Situación | Qué ve el usuario |
|---|---|
| Sin conexión | Banner persistente "Sin conexión" y botones críticos desactivados o con aviso (`33A`) |
| Acción en curso | Estado "enviando..." con el botón bloqueado para evitar doble toque |
| Error al enviar | Mensaje claro, **sin perder lo escrito**, con opción de reintentar |
| Conflicto (otro mesero cambió la orden) | Aviso y opción de ver lo cambiado |
| Permiso insuficiente | Mensaje claro que indica qué rol puede hacerlo |

## 6. Accesibilidad

- Contraste de texto suficiente y tamaños de letra generosos.
- Información nunca solo por color.
- Objetivos táctiles amplios (`34`).
- Texto alternativo en imágenes de productos.
- Soporte de zoom y de lectores de pantalla en la carta digital y en la administración.
- Lenguaje sencillo, en español neutro y sin tecnicismos.

## 7. Idioma y tono

- Español por defecto (RG-23), **tuteo** y frases cortas.
- Etiquetas con verbos concretos ("Enviar a cocina", no "Procesar").
- Mismo término para cada concepto (`01`): **Orden**, **Comanda**, **Cuenta**, **Mesa**, **Zona**.
- Textos de cara al cliente final pueden usar "pedido" si resulta más natural (ADR-008).

## 8. Primeros pasos y ayuda

- **Asistente inicial** para configurar un restaurante (`28`, `41`).
- Estados vacíos con una acción clara ("Aún no tienes mesas. Crear mesas").
- Ayuda contextual breve y enlaces a guías cortas.
- Modo de **práctica** o datos de ejemplo para entrenar al personal sin afectar la operación (fase 2).

## 9. Rendimiento percibido

- Interfaz **responde de inmediato** al toque (confirmación visual en milisegundos), aunque la operación termine después.
- Datos esenciales en caché local para abrir rápido.
- Imágenes optimizadas, listas virtualizadas en catálogos largos.
- Tiempos objetivo (hipótesis a validar): abrir la tablet y ver mesas en pocos segundos; enviar una orden con confirmación en un par de segundos en una red normal.

## 10. Pruebas de usabilidad

- Probar con **personal real** de restaurantes (meseros, cocineros, cajeros), no solo con desarrolladores.
- Observar una jornada completa en un local durante el piloto.
- Medir: toques por orden, errores, tiempo de aprendizaje.
- Ajustar antes de añadir funciones.

## 11. Preguntas abiertas

- ¿Qué nivel de personalización visual (logo y colores del restaurante) se permite en la carta digital?
- ¿Se necesita modo claro/oscuro en todas las apps o solo cocina?
- ¿Se ofrece interfaz en otros idiomas desde el inicio? (Recomiendo no.)
