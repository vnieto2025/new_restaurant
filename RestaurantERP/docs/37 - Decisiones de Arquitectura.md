# 37 - Decisiones de Arquitectura (ADR)

**Estado:** Propuesto

Registro de decisiones importantes. Cada una tiene su contexto, alternativas y consecuencias. Una decisión **Aprobada** solo se cambia con un nuevo ADR que la reemplace.

**Estados posibles:** `Propuesta` (recomendada, falta confirmar) · `Aprobada` · `Pendiente` (falta investigar) · `Reemplazada`

## Índice

| ADR | Título | Estado |
|---|---|---|
| 001 | Monolito modular | Propuesta |
| 002 | Multi-tenencia: base compartida con `empresa_id` y RLS | Propuesta |
| 003 | PostgreSQL como base de datos | Propuesta |
| 004 | Tiempo real con WebSockets y Redis | Propuesta |
| 005 | Estrategia de impresión de tirillas | Pendiente |
| 006 | Estado por ítem de comanda; estado de orden derivado | Propuesta |
| 007 | POS de mostrador independiente de Órdenes | Propuesta |
| 008 | Vocabulario: "Orden" como término oficial | Propuesta |
| 009 | Nómina: no construir en el MVP | Propuesta |
| 010 | Precios con o sin impuesto incluido | Pendiente |
| 011 | Adaptadores para servicios externos | Propuesta |
| 012 | Modo de aceptación de órdenes por QR (por defecto: con aprobación en zonas de mesa) | Propuesta |
| 013 | Momento en que se descuenta el inventario (al pasar a `en_proceso`) | Propuesta |
| 014 | WhatsApp: enlace manual en fases 1 y 2 inicial; API oficial después | Propuesta |
| 015 | Propinas: individual, colectiva o mixta como configuración | Propuesta |
| 016 | Pagos en línea: cuenta propia de cada restaurante en la pasarela | Propuesta |
| 017 | Roles fijos en el MVP con permisos granulares por debajo | Propuesta |
| 018 | Estructura de código heredada de AppGym | Aprobada |
| 019 | Identificadores BigInteger internos y tokens opacos en lo público | Aprobada |
| 020 | Nombres de tablas y campos en español | Aprobada |
| 021 | Precio de carta con impuesto incluido, en pesos enteros | Aprobada (provisional) |
| 022 | Una sola aplicación Vue, sin librería de UI | Aprobada |
| 023 | Aislamiento por empresa en la capa Querys; RLS antes del piloto | Propuesta |
| 024 | El ítem de orden es también el ítem de comanda | Propuesta |
| 025 | Esquema con migraciones de Alembic | Aprobada |
| 026 | Tablet compartida con dispositivo autorizado y PIN | Aprobada |
| 027 | Una cuenta por sesión de mesa | Propuesta |
| 028 | Los pagos se registran en el turno abierto de la caja | Propuesta |
| 029 | Row Level Security con un rol de aplicación sin privilegios | Aprobada |
| 030 | Definición de venta para los reportes | Propuesta |

---

## ADR-001: Monolito modular

- **Contexto:** equipo muy pequeño, producto con muchos módulos, necesidad de venderlos por separado.
- **Opciones:** (a) microservicios; (b) monolito sin estructura; (c) monolito modular.
- **Decisión propuesta:** **monolito modular**, un solo despliegue con paquetes por módulo y fronteras explícitas.
- **Consecuencias:** operación simple y barata; la modularidad comercial se logra con licenciamiento (`02A`), no con servicios separados. Exige disciplina para no cruzar fronteras entre módulos (RG-26).
- **Cuándo revisar:** si un módulo necesita escalar de forma muy distinta (por ejemplo, integraciones con alto volumen).

## ADR-002: Multi-tenencia con base compartida y RLS

- **Contexto:** muchas empresas pequeñas, aislamiento obligatorio.
- **Opciones:** base compartida; esquema por empresa; base por empresa.
- **Decisión propuesta:** base compartida con `empresa_id` en todas las tablas + **Row Level Security** + pruebas automáticas de aislamiento. Ver `02A`.
- **Consecuencias:** operación simple; riesgo de fuga si hay errores, mitigado con RLS y pruebas. Migración futura a esquema por empresa posible para un cliente grande.

## ADR-003: PostgreSQL

- **Contexto:** dominio transaccional (órdenes, pagos, inventario) con relaciones fuertes.
- **Decisión propuesta:** PostgreSQL. Se descarta NoSQL como base principal.
- **Consecuencias:** transacciones ACID, RLS, JSONB para datos flexibles (configuración, modificadores).

## ADR-004: Tiempo real con WebSockets y Redis

- **Contexto:** tablet, cocina y caja deben enterarse de cambios en segundos.
- **Opciones:** polling; Server-Sent Events; WebSockets; PostgreSQL LISTEN/NOTIFY.
- **Decisión propuesta:** WebSockets para pantallas operativas; Redis pub/sub para distribuir eventos; la base de datos es siempre la fuente de verdad y el cliente re-sincroniza al reconectarse.
- **Consecuencias:** conexiones persistentes que gestionar; necesita reconexión robusta en tablets. Para el MVP con una sola instancia, se puede arrancar sin Redis y añadirlo después.

## ADR-005: Estrategia de impresión de tirillas

- **Estado:** **Pendiente**
- **Contexto:** una web app no puede imprimir en una impresora térmica con la misma facilidad que un programa nativo.
- **Opciones:** impresión del navegador; agente local; WebUSB/WebSerial; impresión por red o nube. Detalle en `04`, sección 6.
- **Decisión provisional:** diseñar una **cola de impresión en el backend** independiente del método de salida, y prototipar la impresión del navegador en el primer corte vertical.
- **Para decidir:** probar con las impresoras reales de restaurantes del público objetivo, y con las tablets que usarán.

## ADR-006: Estado por ítem; estado de la orden derivado

- **Contexto:** una orden puede incluir platos de cocina y bebidas de bar que se despachan en tiempos distintos. Tus estados: azul claro (nuevo), amarillo (en proceso), verde (entregado), rojo (cancelado o perdido), y cocina maneja además "despachado".
- **Decisión propuesta:** el estado vive en el **ítem de comanda**; el de la **orden** se calcula a partir de sus ítems. Estados: `pendiente_aprobacion`, `nuevo`, `en_proceso`, `despachado`, `entregado`, `cancelado` (detalle y transiciones en `16`).
- **Consecuencias:** más flexible y fiel a la realidad; algo más de lógica. **`[POR CONFIRMAR]`** si "despachado" y "entregado" son estados distintos para ti. Recomiendo que sí, porque permite medir tiempo de producción y tiempo de entrega por separado.

## ADR-007: POS de mostrador independiente de Órdenes

- **Contexto:** se quiere vender un paquete "solo facturación e inventarios" sin el módulo de pedidos.
- **Decisión propuesta:** el módulo `caja` incluye un **POS de mostrador** que crea ventas directas sin depender de `pedidos`. Cuando `pedidos` está activo, sus cuentas alimentan a `caja`.
- **Consecuencias:** hay dos formas de originar una venta; la caja debe aceptar ambas con un modelo común (`cuenta`).

## ADR-008: "Orden" como término oficial

- **Decisión propuesta:** usar **Orden** en código, base de datos y documentación. "Pedido" queda para el lenguaje coloquial y textos al cliente final.
- **Consecuencias:** evita inconsistencias. Ver glosario (`01`).

## ADR-009: Nómina fuera del MVP

- **Contexto:** nómina es un dominio legal complejo y cambiante.
- **Decisión propuesta:** **no construir nómina completa**. Ofrecer liquidación de **propinas** y de pagos a **domiciliarios**, y evaluar exportación hacia software de nómina especializado.
- **Consecuencias:** menos riesgo legal y de mantenimiento. Debe validarse con contador o abogado qué obligaciones tiene el restaurante sobre propinas y domiciliarios.

## ADR-010: Precios con o sin impuesto incluido

- **Estado:** **Pendiente**
- **Contexto:** en restauración local suele mostrarse el precio al cliente con impuestos incluidos, pero el cálculo interno necesita la base gravable.
- **Opciones:** (a) guardar precio base y calcular impuesto; (b) guardar precio final con impuesto incluido y derivar la base.
- **Para decidir:** consultar con un contador del mercado objetivo y revisar cómo lo hacen el proveedor de facturación electrónica y los productos de la competencia.

## ADR-011: Adaptadores para servicios externos

- **Decisión propuesta:** cada servicio externo (facturación electrónica, pagos, WhatsApp, plataformas de domicilio) se usa mediante una **interfaz propia** con un adaptador por proveedor.
- **Consecuencias:** se puede cambiar de proveedor sin tocar la lógica de negocio; un poco más de trabajo inicial.

---

## ADR-012: Modo de aceptación de órdenes por QR

- **Contexto:** el QR de mesa es una puerta pública; cualquiera con una foto puede intentar crear órdenes (`10A`).
- **Opciones:** libre; con aprobación del mesero; mesa abierta por el mesero.
- **Decisión propuesta:** implementar **libre** y **con aprobación** en el MVP, con **con aprobación** como valor por defecto en zonas de mesa, configurable por zona.
- **Consecuencias:** nuevo estado `pendiente_aprobacion` (`16`); depende de que el mesero responda. Validar con restaurantes reales.

## ADR-013: Momento del descuento de inventario

- **Contexto:** descontar al crear la orden penaliza cancelaciones; hacerlo al pagar queda desfasado de la producción (`14`).
- **Decisión propuesta:** descontar al pasar a **`en_proceso`** y registrar como **merma** lo cancelado después.
- **Consecuencias:** refleja el consumo real; requiere lógica de merma. Validar con un contador y con restaurantes.

## ADR-014: WhatsApp por fases

- **Contexto:** la API oficial implica plantillas aprobadas y costo por mensaje; las vías no oficiales pueden bloquear el número (`31B`).
- **Decisión propuesta:** **enlace "click to chat" con mensaje prellenado** en el MVP y fase 1; **API oficial** en fase 2 si hay demanda y costos verificados; **nunca** automatización no oficial.
- **Consecuencias:** cero costo y riesgo al inicio, a cambio de que una persona pulse "enviar".

## ADR-015: Propinas como configuración

- **Contexto:** individual, colectiva o mixta; el tratamiento legal debe validarse (`26A`).
- **Decisión propuesta:** soportar los tres modelos como **configuración del restaurante**, con **colectiva** como valor sugerido.
- **Consecuencias:** más lógica de reparto; menos conflicto interno. Requiere validación legal.

## ADR-016: Pagos en línea con cuenta propia del restaurante

- **Contexto:** si el proveedor del software recauda y reparte el dinero, asume obligaciones financieras y legales (`20A`).
- **Decisión propuesta:** cada restaurante abre **su propia cuenta** en la pasarela; el proveedor solo integra.
- **Consecuencias:** menos riesgo regulatorio; mayor trámite para el restaurante. Validar con un asesor legal.

## ADR-017: Roles fijos con permisos granulares

- **Contexto:** los restaurantes pequeños necesitan simplicidad; a la vez, el sistema debe poder crecer (`29`).
- **Decisión propuesta:** **roles fijos** en el MVP, construidos sobre **permisos granulares**; roles personalizados en fase 2.
- **Consecuencias:** modelo listo para personalización sin rediseñar; un usuario puede tener varios roles.

---

---

## ADR-018: Estructura de código heredada de AppGym

- **Estado:** Aprobada (2026-10-24)
- **Contexto:** `04` propone `app/core` + `app/modules` y `31` propone rutas REST `/api/v1/...`. El equipo ya mantiene AppGym con otra estructura y quiere la misma en este proyecto.
- **Decisión:** el backend sigue el patrón de AppGym: `Router/<Modulo>.py` (endpoint POST con `@http_decorator` y `JWTBearer`) → `Class/<Modulo>.py` (lógica) → `Querys/<modulo>.py` (consultas) y `Rules/<modulo>.py` (validación de entrada por ruta). Querys y Rules van **divididos por módulo** y heredan de una base común (`Querys/base.py`). Todos los endpoints son `POST` con JSON, exigen el header `accept: application/json` y responden `{code, message, data}`. Rutas con forma `/<modulo>/<accion>` (ej. `/orden/create`), sin versión en la URL.
- **Consecuencias:** coherencia con lo que el equipo ya conoce. La protección por módulo contratado (RN-API-03) se declara en el `JWTBearer(permisos=..., modulo=...)` de cada ruta. Los errores de permiso o módulo responden 403 con `detail.codigo` (`permiso_insuficiente`, `modulo_no_contratado`). Si se publica una API para terceros (fase 3), se versionará aparte.

## ADR-019: Identificadores BigInteger internos y tokens opacos en lo público

- **Estado:** Aprobada (2026-10-24). Ajusta RG-01.
- **Decisión:** las tablas usan `BigInteger` autoincremental como clave primaria (como AppGym). Lo que sale a URLs o pantallas públicas nunca usa ese id: el QR lleva un token aleatorio (`qr_acceso.token`) y el seguimiento del pedido otro (`orden.token_seguimiento`).
- **Consecuencias:** se cumple la intención de RG-01 (nada secuencial adivinable en lo público) con un modelo más simple. Los endpoints con sesión sí usan ids, siempre filtrados por empresa (ADR-023).

## ADR-020: Nombres de tablas y campos en español

- **Estado:** Aprobada (2026-10-24). Resuelve el `[POR CONFIRMAR]` de `05`, sección 1.
- **Decisión:** tablas, columnas y rutas en español, minúsculas y con guion bajo (`orden_item`, `punto_produccion`), consistentes con el glosario. El código de soporte heredado (decorador, validador) conserva sus nombres originales.

## ADR-021: Precio de carta con impuesto incluido, en pesos enteros

- **Estado:** Aprobada como **provisional** (2026-10-24). Resuelve por ahora ADR-010; **validar con contador** antes de la fase 2 (facturación).
- **Decisión:** `producto.precio` es el precio final que ve el cliente, con impuesto incluido, en pesos enteros (`BigInteger`, RG-03). La orden copia ese precio (RG-13). La base gravable se calculará al facturar.

## ADR-022: Una sola aplicación Vue, sin librería de UI

- **Estado:** Aprobada (2026-10-24). Resuelve "Librería de UI" de los ADR pendientes y ajusta `04`, sección 3.
- **Decisión:** un solo frontend Vue 3 + Pinia + Vue Router en JavaScript (como AppGym), con secciones por pantalla de trabajo: `/mesas` (tablet del mesero), `/produccion` (cocina y bar), `/mostrador`, `/admin`, `/plataforma` y la carta pública `/q/<token>`. CSS propio con tokens de diseño (`src/assets/main.css`), sin Tailwind ni librerías de componentes. Diseño táctil y adaptado a tablet y celular.
- **Consecuencias:** un solo despliegue y un solo cliente de API. La carta pública comparte el paquete con el resto; si su peso llegara a importar con mala señal, se separa más adelante.

## ADR-023: Aislamiento por empresa en la capa Querys; RLS antes del piloto

- **Estado:** Propuesta. Implementa por fases ADR-002.
- **Decisión (fase 0):** cada petición carga su contexto desde el token (empresa, restaurante, permisos, módulos, zonas y puntos). Ese contexto se recalcula en cada petición, por lo que un cambio de rol o una desactivación aplica de inmediato. `Querys/base.py` filtra **toda** lectura por `empresa_id` y `restaurante_id` del contexto, y fija esos campos en toda escritura ignorando lo que mande el cliente. Un registro de otra empresa responde igual que uno inexistente (404). Hay pruebas automáticas de aislamiento (`backend/tests/test_aislamiento.py`).
- **Pendiente:** Row Level Security de PostgreSQL como segunda capa, antes del piloto con datos reales.

## ADR-024: El ítem de orden es también el ítem de comanda

- **Estado:** Propuesta. Simplifica `05`.
- **Decisión:** no existe tabla `comanda_item`. Cada `orden_item` pertenece a lo sumo a una `comanda` (`orden_item.comanda_id`) y guarda su estado (ADR-006). Los ítems sin punto de producción no tienen comanda y quedan despachados al instante (doc 19, sección 3). Agregar ítems a una orden crea una comanda nueva marcada como adición.

## ADR-025: Esquema con migraciones de Alembic

- **Estado:** Aprobada (fase 1). En la fase 0 se usaba `create_all`.
- **Decisión:** el esquema lo definen las migraciones de `backend/migrations` (Alembic), que corren con el usuario dueño de las tablas. `seed.py` aplica las migraciones pendientes, configura RLS y carga el catálogo; `iniciar.bat` y el contenedor lo ejecutan antes de arrancar. Las pruebas siguen creando el esquema con `create_all` por velocidad.
- **Consecuencias:** cada cambio de modelo exige `alembic revision --autogenerate` y revisar la migración generada. `alembic check` debe salir limpio.

## ADR-026: Tablet compartida con dispositivo autorizado y PIN

- **Estado:** Aprobada (fase 1). En la fase 0 todo el personal entraba con usuario y clave.
- **Decisión:** el administrador autoriza cada tablet de zona o pantalla de producción con un código de 6 dígitos (15 minutos, un solo uso). El dispositivo guarda un secreto; en la base solo queda su huella. En un dispositivo autorizado cada persona entra con un PIN de 4 a 6 números, único en la empresa, que solo funciona ahí (RN-USR-03) y solo para quien atiende esa zona o punto. Desautorizar el dispositivo corta sus sesiones al instante. La tablet de zona vuelve al PIN tras 3 minutos sin uso; la pantalla de cocina no se bloquea.
- **Detalle técnico:** la huella del PIN es un HMAC con la clave del servidor, determinística para poder identificar a la persona solo con el PIN. Se limitan los intentos fallidos por dispositivo y se auditan.
- **Turno del mesero:** se abre al identificarse, no se cierra con mesas a su cargo (RN-MSR-04) y se cierra solo al cerrar la jornada (RN-MSR-03).

## ADR-027: Una cuenta por sesión de mesa

- **Estado:** Propuesta. Simplifica `05` (no hay tabla `cuenta_orden`).
- **Decisión:** la cuenta pertenece a la sesión de mesa y cobra todas sus órdenes no canceladas. Mientras está abierta, su subtotal sigue lo que se pide; al pagarse se congela. Los pedidos externos ya tienen una sesión por orden, así que tienen su propia cuenta. Trasladar una mesa mueve la sesión; unir mesas pasa las órdenes a la sesión principal.
- **Consecuencias:** al pagar el total la mesa queda libre aunque cocina siga preparando algo. Con el módulo caja contratado, una mesa con consumo no se libera sin cobrar; sin caja, se libera a mano como en la fase 0.

## ADR-028: Los pagos se registran en el turno abierto de la caja

- **Estado:** Propuesta. Responde la pregunta abierta de `20` sobre cajas: una por restaurante, preparada para varias.
- **Decisión:** todo pago queda en el turno abierto de la caja (RN-CAJ-01), lo haga el cajero o un administrador. Un solo turno abierto por caja (RN-CAJ-02). El mesero no cobra (matriz de `29`); pide la cuenta e imprime la precuenta.
- **Propina:** se sugiere un porcentaje configurable (10 % por defecto, 0 para no sugerir) y se guarda aparte de la venta. La liquidación de propinas sigue en la fase 2 (`26A`).

## ADR-029: Row Level Security con un rol de aplicación sin privilegios

- **Estado:** Aprobada (fase 1). Completa ADR-002 y ADR-023.
- **Contexto:** un superusuario de PostgreSQL se salta RLS, y el usuario de desarrollo (`postgres`) lo es.
- **Decisión:** el backend se conecta con un rol propio sin privilegios ni `BYPASSRLS` (`DB_APP_USER`), que `seed.py` crea y al que da permisos de lectura y escritura. Toda tabla con `empresa_id` tiene la política `aislamiento_empresa` con `FORCE ROW LEVEL SECURITY`. En cada transacción de una petición de empresa se fija `app.empresa_id`, y la base rechaza leer o escribir filas de otra empresa aunque una consulta olvide filtrar.
- **Consecuencias:** sin `app.empresa_id` la política no restringe. Eso ocurre solo en el ingreso, en la consola de plataforma y al resolver el token de un QR, que necesitan buscar en toda la base. Hay pruebas que verifican que la aplicación no es superusuario y que la base bloquea lecturas y escrituras ajenas.

## ADR-030: Definición de venta para los reportes

- **Estado:** Propuesta. Resuelve el `[POR CONFIRMAR]` de `26`, sección 2.
- **Decisión:** con caja contratada, **venta** = cuentas pagadas de la jornada (por jornada de pago), menos descuentos y sin propinas; las cifras cuadran con lo cobrado (RN-REP-01). Sin caja, venta = ítems no cancelados de las órdenes de la jornada. Los desgloses por producto, zona, canal y mesero usan el valor de los ítems, antes de descuentos de la cuenta. Cada cifra se compara con el periodo anterior y, si es un solo día, con el mismo día de la semana pasada.

## ADR-031: Facturación electrónica con adaptador, proveedor simulado y cola en el mismo proceso

- **Estado:** Aprobada (fase 2). Completa ADR-011. El proveedor real sigue **pendiente**.
- **Contexto:** aún no se elige proveedor tecnológico, y cobrar nunca debe esperar al proveedor (RN-FAC-06).
- **Decisión:**
  - **Generación y numeración:** el documento de venta se genera dentro de la transacción del cobro. El número se toma con un `UPDATE ... RETURNING` atómico sobre la resolución, así que un cobro fallido no consume número.
  - **Envío:** una cola en segundo plano dentro del mismo proceso de FastAPI envía los documentos pendientes. Los reintentos esperan 1, 5 y 15 minutos y luego cada hora. Usa la conexión administrativa solo para listar qué restaurantes tienen pendientes, y envía cada documento con la sesión de su empresa, bajo RLS.
  - **Proveedor:** el proveedor se elige por configuración (`Utils/proveedores_factura.py`). Mientras tanto se usa uno simulado que acepta, rechaza o no responde.
  - **Credenciales:** se guardan cifradas con Fernet (`CREDENCIALES_KEY`).
  - **Notas crédito:** una nota crédito se envía solo después de que el documento que corrige fue aceptado.
- **Consecuencias:**
  - Integrar un proveedor es escribir una clase con `emitir()`.
  - Si se corren varios procesos del backend, cada uno tiene su cola. `SKIP LOCKED` evita envíos dobles, pero conviene llevar la cola a un trabajador aparte (ADR pendiente de cola de tareas).
  - Las tasas y los textos legales son datos que cada restaurante valida con su contador.
- **Cuándo revisar:** al elegir el proveedor real, o al pasar a varios procesos del backend.

## ADR-032: Inventario por movimientos, descuento al entrar a producción

- **Estado:** Aprobada (fase 2). Implementa ADR-013; el momento del descuento sigue `[POR CONFIRMAR]` con un contador.
- **Decisión:**
  - **Movimientos:**
    - Todo cambio de stock es un movimiento (`movimiento_inventario`) con signo, costo y stock resultante.
    - El insumo guarda el stock como total acumulado, actualizado en la misma transacción y con el insumo bloqueado. Las pruebas verifican que coincide con la suma de los movimientos.
    - Las cantidades van siempre en la unidad base (g, ml o und). Las presentaciones de compra tienen un factor explícito.
  - **Costo:** promedio ponderado; solo lo recalculan las entradas con costo (entrada, compra, producción).
  - **Descuento por venta:**
    - El ítem descuenta su receta y lo que suman o restan sus modificadores la primera vez que pasa a `en_proceso` (o se despacha directo). Queda marcado con `inventario_descontado`.
    - Si se cancela después, el consumo se reversa y se registra como merma con el motivo. El stock no cambia, pero la pérdida queda visible.
  - **Productos de reventa:** son una receta de un solo insumo, sin un mecanismo aparte.
  - **Preparaciones:** son insumos con su propia receta; al producirlas se descuentan sus ingredientes y entran al costo de lo usado. Para costear platos se usa el costo teórico de su receta, así una subida de un insumo se ve en el margen.
- **Consecuencias:**
  - Sin receta no se descuenta nada (RN-REC-05). La pantalla de costos muestra qué porcentaje de las ventas tiene receta.
  - El stock negativo se permite y se alerta (RN-INV-05).
- **Cuándo revisar:** si un cliente necesita PEPS, lotes o varias bodegas por restaurante.

## ADR-033: Compras y proveedores sobre los movimientos de inventario

- **Estado:** Aprobada (fase 2). Implementa los docs 23 y 24 dentro del módulo contratable `inventario` (doc 02A).
- **Decisión:**
  - **Proveedor:** es por restaurante, como el insumo. Responde la pregunta abierta del doc 24: no se comparte entre restaurantes de la misma empresa. Con compras no se borra, se inactiva.
  - **Relación proveedor–insumo:** guarda la presentación habitual, si es el preferido (uno por insumo) y el último precio. El histórico de precios no tiene tabla propia: sale de las líneas de compra recibidas, que no se editan (RN-PRV-02). El primer proveedor que surte un insumo queda como preferido.
  - **Estados:** `borrador`, `solicitada`, `parcial`, `recibida`, `cerrada`, `anulada`. Se agrega `parcial` a la tabla del doc 23 para distinguir la recepción incompleta. La compra rápida se registra recibida y cerrada en un paso.
  - **Recepción:**
    - Cada recepción (`compra_recepcion`) entra al inventario con `InventarioQuerys.mover` tipo `compra`, al costo por unidad base (precio de la presentación ÷ factor). Así recalcula el promedio ponderado.
    - Una línea recibida no cambia de precio. Lo que falta queda pendiente, y cerrar con faltante pide confirmación.
  - **Impuestos de compra:** el precio se registra con impuestos incluidos y todo es costo. Se asume que el IVA de compras de un restaurante en régimen de impuesto al consumo no es descontable. El porcentaje por línea es solo informativo.
  - **Pagada de caja:**
    - Cada recepción crea un gasto en el turno abierto, ligado a la recepción. Exige el módulo de caja, el permiso `caja.movimientos` y efectivo suficiente.
    - Al anular se puede reintegrar el dinero como aporte.
  - **Anulación:**
    - Revierte cada entrada con un movimiento `anulacion_compra` al mismo costo, que también saca ese valor del promedio (RN-COM-05).
    - Si ya se consumió, la existencia puede quedar negativa y se advierte.
  - **Alertas:** al recibir se avisa si el proveedor subió el precio 5 % o más frente a su último precio, y qué platos subieron de costo 5 % o más.
  - **Lista sugerida:** insumos en su mínimo o por debajo, para llevarlos al doble del mínimo, descontando lo que ya viene en compras pendientes y agrupados por proveedor preferido.
  - **WhatsApp:** el mensaje del pedido se arma en el servidor y se abre con un enlace `wa.me` prellenado. No se envía nada automáticamente (doc 31B).
- **Consecuencias:**
  - Cocina puede recibir mercancía desde su tablet (`compras.recibir`) sin poder registrar ni anular compras.
  - Cuentas por pagar, devoluciones parciales al proveedor y lectura de facturas por foto quedan para la fase 3.
- **Cuándo revisar:**
  - Si un restaurante descuenta IVA de compras.
  - Si una empresa con varias sedes quiere compartir proveedores.
  - Si el doble del mínimo no sirve como meta de reposición (agregar existencia máxima).

## ADR-034: Domicilios con zonas de tarifa fija y cobro contra entrega al rendir

- **Estado:** Aprobada (fase 2). Implementa el doc 15B dentro del módulo contratable `domicilios`.
- **Decisión:**
  - **Zonas de envío:** lista de zonas con tarifa fija, pago al domiciliario y pedido mínimo, sin mapas (recomendación del doc 15B). Cada zona guarda sus barrios para sugerirla al escribir el barrio.
  - **Entrega:**
    - Es una entidad ligada a la orden (`entrega`); no reemplaza los estados de los ítems.
    - La orden de domicilio usa la mesa externa con canal `domicilio`.
    - Copia dirección, teléfono, zona, tarifa y pago al domiciliario al pedir, así un cambio de tarifa no altera los pedidos ya tomados.
    - Estados: `pendiente_asignacion`, `asignada`, `en_camino`, `entregada`, `fallida`. Solo sale cuando todos sus ítems están despachados, y al entregarla los ítems pasan a `entregado`.
  - **Tarifa:**
    - Va en la cuenta (`cuenta.envio`) como concepto aparte. El descuento manual aplica solo a los ítems.
    - En el documento de venta es una línea "Domicilio" con el impuesto por defecto del restaurante, fijado al pedir `[POR CONFIRMAR con contador]`.
  - **Contra entrega:**
    - Al salir se guarda el saldo que debe cobrar el domiciliario.
    - La cuenta se paga en efectivo cuando el domiciliario rinde en caja (`rendicion`), en el turno abierto y con su documento de venta.
    - La diferencia queda con usuario (RN-DOM-03). Un faltante queda a cargo del domiciliario y se resta del efectivo esperado del turno, así el arqueo cuadra.
    - Si la cuenta se pagó antes de salir, no hay nada que cobrar.
  - **Fallo (RN-DOM-04):** exige motivo y decisión.
    - Reintento: vuelve a la lista sin domiciliario.
    - Cancelación o pérdida: cancela lo pendiente (queda como merma si ya se produjo) y no cobra el domicilio.
    - El domiciliario solo puede pedir reintento.
  - **Domiciliario:** tiene código y, opcionalmente, un usuario con el rol `domiciliario`, que solo ve y actualiza sus entregas desde el celular. No se desactiva con entregas en camino (RN-DOM-02). Lleva varias órdenes a la vez si se le asignan.
- **Consecuencias:**
  - La liquidación del pago a domiciliarios usa el pago por zona guardado en cada entrega y los faltantes de las rendiciones. Se implementa en el paso de propinas y liquidaciones (doc 26A).
  - El aviso "salió a domicilio" por WhatsApp queda para el paso de WhatsApp (doc 31B).
  - El pedido de domicilio hecho por el propio cliente desde la web queda pendiente.
- **Cuándo revisar:** si se necesita tarifa por distancia o polígonos, seguimiento en mapa, o pagos con datáfono contra entrega.

## ADR-035: Avisos por WhatsApp manuales por defecto, automáticos con adaptador

- **Estado:** Aprobada (fase 2). Implementa el doc 31B. El proveedor de la API oficial y su costo por mensaje siguen `[POR CONFIRMAR]`.
- **Decisión:**
  - **Dos modos por restaurante:**
    - **Manual (opción B), por defecto:** el aviso queda "por enviar" y en mostrador y domicilios aparece «Enviar por WhatsApp» con el enlace `wa.me` y el mensaje escrito. Al tocarlo queda registrado como enviado y por quién.
    - **Automático (opción A):** una cola en segundo plano, como la de emisión, lo envía por un adaptador de proveedor (`Utils/proveedores_mensaje`), con un proveedor simulado mientras no se elija uno. Las credenciales se guardan cifradas y nunca se devuelven.
    - Nunca la opción C.
  - **Eventos:** confirmación de orden (apagado por defecto), lista para recoger (solo mostrador y QR para llevar, cuando todo lo despachado está listo), salió a domicilio y entrega fallida. Cada uno se activa por restaurante (RN-NOT-04) y su texto es editable con las variables `{nombre}`, `{numero}`, `{restaurante}` y `{direccion}`.
  - **Registro y repeticiones:** todo aviso queda en `notificacion` con teléfono, mensaje, modo, estado, intentos y error (RN-NOT-03). Un mismo evento de una orden se avisa una sola vez.
  - **Avisos que no se envían:** quedan como omitidos, con el motivo:
    - sin teléfono válido (RN-NOT-05, mismo formato de clientes);
    - el cliente pidió no recibir avisos (`cliente.acepta_avisos`);
    - se superó el límite diario por teléfono.
  - **Nunca frenan la orden (RN-NOT-01):**
    - El aviso se registra en un punto de guardado propio y sin `insert_data`, cuyo rollback deshace toda la transacción.
    - Si el proveedor no responde, se reintenta a los 1, 5 y 15 minutos. Si sigue fallando o lo rechaza, pasa a "no se pudo enviar" y aparece para avisar a mano.
  - **Módulo:** los avisos van con `pedidos` y no con `domicilios` como decía el doc 02A, porque "lista para recoger" sirve sin domicilios. El costo por mensaje del modo automático se cobra aparte (doc 42).
- **Consecuencias:**
  - Los mensajes comerciales (cupones) no usan este flujo: requieren consentimiento comercial y van con el paso de cupones (RN-NOT-02).
  - En modo automático los textos deben coincidir con plantillas aprobadas por Meta; la pantalla lo advierte.
- **Cuándo revisar:** al elegir el proveedor oficial (tarifas, plantillas, webhook de estado de entrega) o si se quieren respuestas automáticas a mensajes entrantes.

## ADR-036: Pagos en línea con adaptador de pasarela y webhook firmado

- **Estado:** Aprobada (fase 2). Implementa el doc 20A en el módulo contratable `pagos_linea` (depende de caja). La pasarela real (Wompi, PayU, ePayco…), sus comisiones y el modelo de cuenta siguen `[POR CONFIRMAR]`.
- **Decisión:**
  - **Cuenta en la pasarela:** cada restaurante tiene la suya. El software integra y no recauda dinero de terceros (doc 20A, sección 6). Las credenciales y el secreto de firma se guardan cifrados.
  - **Adaptador (`Utils/pasarelas`):** crear sesión, verificar firma, interpretar el aviso y reembolsar.
    - Mientras no se elija una real se usa la pasarela simulada, solo en ambiente de pruebas.
    - Su "página segura" es una pantalla propia (`/pasarela-simulada/:referencia`) que, como una real, avisa el resultado con un webhook firmado (HMAC-SHA256).
  - **El cliente paga desde el celular:**
    - Con el QR de su mesa («Pagar la cuenta» en la carta).
    - Con el enlace de seguimiento de su pedido, que caja envía por WhatsApp para pedidos para llevar y domicilios.
    - Ningún dato de tarjeta pasa por el sistema (RG-19).
  - **Intento de pago:**
    - Tiene monto fijo: el saldo de la cuenta más la propina que elige el cliente (RN-PAG-02).
    - Es idempotente por clave y expira según la configuración.
    - La pantalla del cliente solo consulta el estado; nunca decide si se pagó.
  - **Webhook (`/webhook/pagos/{pasarela}`):**
    - No requiere sesión ni el encabezado `accept`.
    - Se ubica el intento por su referencia, se guarda crudo (`webhook_pago`) y solo se procesa con firma válida y monto igual al del intento (RN-PAG-01, RN-API-06).
    - Los avisos repetidos o fuera de orden no cambian un estado final.
  - **Al aprobarse:**
    - Se abona a la cuenta con el medio del sistema "Pago en línea", que el cajero no puede elegir ni editar.
    - Va en el turno abierto si lo hay; si no, sin turno, porque no es efectivo del cajón.
    - Si cubre el total, la cuenta queda pagada con su documento de venta.
    - Si la cuenta cambió, se abona hasta el saldo y el resto lo cobra caja. Si ya estaba pagada o anulada, todo queda por reembolsar.
  - **Reembolso:**
    - Con permiso y motivo, por la pasarela (RN-PAG-03).
    - Solo lo que no está abonado a una cuenta vigente: si el pago está aplicado, primero se anula en caja.
  - **Conciliación:** monto, comisión (la que envía la pasarela o la del extracto), neto y fecha de abono por pago.
  - **Falla de la pasarela:** el cliente puede pagar en caja; nada se bloquea (RN-PAG-04).
- **Consecuencias:**
  - Un pedido para llevar por QR no espera el pago para ir a producción: se paga después con el enlace de seguimiento. Retener pedidos "pendientes de pago" queda para cuando exista el domicilio web.
  - Pagar solo una parte de la cuenta en línea no está habilitado: el intento cubre todo el saldo.
- **Cuándo revisar:** al elegir la pasarela real (formato del webhook, consulta de estado si se pierde un aviso, reembolsos y reportes de liquidación).

## ADR-037: Cupones con redención registrada y cupón automático para la próxima visita

- **Estado:** Aprobada (paso 8 de la fase 2).
- **Contexto:** el doc 25A pide cupones con reglas, validados en el servidor, que no dejen la cuenta en negativo y que solo se reviertan anulando la cuenta. Deja abiertas tres preguntas:
  - si el cupón va antes o después de la propina y los impuestos;
  - quién autoriza los cupones de monto alto;
  - si aplican a plataformas externas.
- **Decisión:**
  - **Módulo `fidelizacion`:** depende de caja. Sus permisos son `cupones.gestionar` (administrador), `cupones.aplicar` (administrador, cajero y encargado de externos, según doc 29) y `cupones.ver` (resultados). Los puntos quedan para la fase 3.
  - **Cupón por restaurante:** el código es único en el restaurante, en mayúsculas.
    - Tipos: porcentaje (con tope opcional), valor fijo, producto (porcentaje sobre una unidad, 100 = gratis) y envío gratis.
    - Reglas: vigencia, canales (mesa, para llevar, domicilio), zonas, días, horario, categorías, compra mínima, usos totales, usos por cliente, cliente asignado y acumulable (no por defecto).
    - Estado guardado: activo, pausado o anulado. "Vencido", "agotado" y "programado" se calculan.
  - **Redención (`cupon_redencion`):**
    - Queda "aplicada" desde que se aplica en una cuenta abierta y ya cuenta como uso; el cupón se bloquea mientras se cuentan sus usos.
    - Al pagar pasa a "redimida" con la venta neta atribuida. Si se quita antes de pagar queda "quitada".
    - Anular la cuenta la deja "revertida" (RN-CUP-03).
  - **Recálculo:** mientras la cuenta está abierta, el cupón se recalcula con lo pedido. Si deja de cumplir (compra mínima, producto) no descuenta y muestra el motivo. Si al pagar no descuenta, queda quitado.
  - **Antes de la propina y con impuestos incluidos:** los precios ya incluyen IVA. El cupón descuenta sobre el subtotal; la propina sugerida se calcula después. En el documento el descuento se reparte entre las líneas, así baja la base y el impuesto. El descuento manual va primero y el cupón descuenta sobre lo que queda (RN-CUP-02).
  - **Cuenta:** nuevas columnas `descuento_cupon` (ítems), `descuento_envio` y `cliente_id`. Con envío gratis completo, la línea de domicilio no se factura.
  - **Cliente identificado:** caja puede identificar al cliente en la cuenta. Es obligatorio para cupones personales y para los que tienen límite por cliente (RN-CUP-04). Si cambia el cliente, sale el cupón personal de la otra persona.
  - **Cupón para la próxima visita:** una plantilla define la compra mínima que lo dispara y los días de validez. Al pagar con cliente identificado se emite un cupón personal de un solo uso.
    - Se emite uno por cuenta, y no se emite si el cliente ya tiene uno sin usar de esa plantilla.
    - Sale en el comprobante. Si se anula la cuenta que lo emitió y no se ha usado, se anula.
  - **Desde el celular:** en la pantalla de pago el cliente escribe el código y la validación es la misma de caja. Hay un límite de 8 intentos cada 10 minutos por dispositivo para que adivinar códigos no sea práctico. Con un pago en línea en curso no se cambia la cuenta.
  - **WhatsApp:** solo para cupones personales de clientes con consentimiento comercial (RN-CLI-04, RN-NOT-02), con el enlace de WhatsApp. No pasa por la cola de avisos de órdenes.
  - **Monto alto:** lo controla quien crea el cupón (solo administración), con auditoría de creación, cambios, aplicaciones y retiros. No hay una autorización adicional al aplicarlo.
  - **Plataformas externas:** no aplican; no hay órdenes de plataformas todavía.
- **Consecuencias:**
  - Los reportes de ventas restan los descuentos de cupones. El cierre de turno informa "cupones" aparte.
  - Resultados por cupón (las plantillas agrupan lo que emitieron), canal y usuario: descuento, ventas atribuidas, costo del descuento, ticket con y sin cupón, y clientes nuevos (su primera orden fue con el cupón, o se registró ese día).
  - Un cupón vence o se pausa sin afectar lo ya aplicado en cuentas abiertas: se respeta lo revisado al aplicarlo.
- **Cuándo revisar:** al construir los puntos de fidelización (fase 3), el 2x1, los cupones por empresa (hoy son por restaurante) o el envío automático de promociones por un proveedor de WhatsApp.

## ADR-038: Liquidaciones de propinas y domiciliarios con marca de lo liquidado

- **Estado:** Aprobada (paso 9 de la fase 2). **El tratamiento legal y fiscal sigue `[POR CONFIRMAR]`** con abogado laboral y contador (doc 26A).
- **Contexto:** el doc 26A pide reparto individual, colectivo o mixto, liquidación por periodo (abierta, calculada, aprobada, pagada) y el pago a domiciliarios. Una propina nunca se debe liquidar dos veces ni perderse.
- **Decisión:**
  - **Reglas por restaurante (`liquidacion_config`):**
    - Periodo: semana de lunes a domingo, quincena (1-15 y 16-fin) o mes.
    - Modelo: individual, colectivo (valor por defecto) o mixto, con un porcentaje para el mesero.
    - El pozo se reparte por horas, por puntos del rol o por horas × puntos (por defecto), y puede repartirse por zona.
    - Puntos sugeridos: mesero 1, cocina 0,8, cajero y encargado de externos 0,5, administrador 0 (0 = no participa).
    - Retención opcional, con tope del 50 % y advertencia legal.
    - Propinas de domicilios: van al pozo o al domiciliario.
    - Pago a domiciliarios: la tarifa de la zona (`pago_domiciliario`), un porcentaje del envío, o una base más un porcentaje.
  - **Versionado (RN-PRP-02):** cada liquidación guarda una copia de las reglas con que se calculó. Cambiar una regla aplica a las siguientes.
  - **Reparto puro (`repartir_propinas`):**
    - La propina con mesero aporta su parte individual; la que no tiene mesero (mostrador, domicilio, QR para llevar) va toda al pozo.
    - La retención sale antes del reparto.
    - El reparto es en pesos enteros, y lo que no se puede repartir (nadie con horas o puntos) queda "sin repartir" y a la vista.
  - **Horas:** salen de los turnos cerrados de los meseros (doc 08A). Quien no marca turno (cocina, caja) recibe sus horas a mano en el borrador; quedan marcadas como editadas y se auditan.
  - **Periodo abierto:** es una vista previa que no se guarda.
  - **Borrador ("calculada"):**
    - Se pueden editar las horas y quién participa (reparte de nuevo con las mismas propinas) y agregar ajustes con motivo (RN-PRP-04).
    - Recalcular conserva lo editado y los ajustes. Solo hay un borrador a la vez por tipo; se puede descartar.
  - **Nada se liquida dos veces (RN-PRP-06):** el borrador guarda los ids de las cuentas, entregas y rendiciones que incluye. Al aprobar se marcan (`cuenta.liquidacion_propina_id`, `entrega.liquidacion_id`, `rendicion.liquidacion_id`).
    - Lo que no está marcado entra en la siguiente liquidación, aunque sea de un periodo anterior; así las propinas que llegan tarde no se pierden.
  - **Aprobada no se modifica (RN-PRP-03):** un ajuste sobre ella queda pendiente y entra en la siguiente. Un saldo en contra (faltantes mayores que lo ganado) también pasa al siguiente periodo.
  - **Domiciliarios:** suman sus entregas del periodo y las propinas (si van a ellos), y se les restan los faltantes de sus rendiciones. Los sobrantes quedan para el restaurante. Con efectivo por rendir no se aprueba.
  - **Pago:** se registra por persona (medio y referencia) con comprobante para firmar. La liquidación queda "pagada" cuando se le paga a todos. El sistema no mueve dinero.
  - **Permisos:**
    - `liquidaciones.gestionar` (módulo propinas) y `domicilios.liquidar` (módulo domicilios), para el administrador.
    - `liquidaciones.ver_propia` (módulo base): cada persona ve solo lo suyo en "Mis propinas y pagos" (RN-PRP-05).
- **Consecuencias:**
  - Si se anula una cuenta cuya propina ya se liquidó, caja recibe el aviso y se corrige con un ajuste manual.
  - La propina en efectivo dada directo al mesero no pasa por el sistema.
- **Cuándo revisar:**
  - Respuestas a las preguntas abiertas del doc 26A: si la cocina y la caja participan, y cómo tratar la propina de un domicilio pagado en línea.
  - Validación legal de la retención y del vínculo de los domiciliarios.
  - Cuando exista registro de horas para cocina y caja.

## ADR-039: POS de mostrador sin pedidos y planes comerciales con cobro manual

- **Estado:** Aprobada (paso 10 de la fase 2). Cierra el ADR-007. Los paquetes y precios siguen siendo hipótesis (doc 42).
- **Contexto:**
  - El paquete Gestión (caja e inventario) necesita vender sin el módulo de pedidos (doc 20, sección 9).
  - Los planes del doc 42 tienen que verse en el contrato.
  - El doc 42 dice que el cobro del servicio en el MVP puede ser manual.
- **Decisión:**
  - **Venta directa (`/pos/*`, módulo caja):** crea una orden con canal `pos` en la mesa externa, con los ítems ya en `entregado` y sin comandas ni cocina, y abre su cuenta.
    - El cobro usa el mismo panel que las mesas (pago mixto, cupón, factura, propina), así que facturación, inventario, cupones, liquidaciones y reportes funcionan sin cambios (ADR-007: un modelo común de cuenta).
    - Es idempotente por clave.
    - Exige turno abierto y jornada sin cerrar. Con pedidos activos también está disponible, como una pestaña más de caja.
  - **Inventario en la venta directa:** se descuenta al registrar la venta. Si se cancela sin cobrar, se reversa sin merma, porque el producto no salió. Con pagos, primero se anulan en caja.
  - **Pantallas sin pedidos:**
    - La caja entra directo a "Venta directa".
    - El canal de tiempo real general queda disponible para caja aunque no haya pedidos.
    - Las pantallas de administración no piden zonas ni puntos de producción cuando el módulo no está.
  - **Planes:**
    - Paquetes: Pedidos (`pedidos`), Gestión (`caja` + `inventario`) y Completo (`pedidos` + `caja` + `inventario` + `facturacion` + `propinas`).
    - Complementos: facturación electrónica, domicilios, pagos en línea y cupones.
    - El plan **no se guarda**: se deduce de los módulos del contrato (`plan_de`), que siguen siendo la fuente de verdad, y lo que no calza es "Personalizado". Las dependencias se siguen validando al guardar.
  - **Cobro del servicio:**
    - El contrato tiene mensualidad, próximo vencimiento y notas comerciales.
    - Soporte registra cada pago a mano (valor, meses, medio, referencia y número de factura emitida por fuera) y el vencimiento avanza por los meses pagados.
  - **Estado de la cuenta:** se calcula, no se guarda: prueba, al día, por vencer (5 días), en mora o cancelado.
    - Pasados 10 días de gracia, la consola marca "pasó el periodo de gracia". **Suspender nunca es automático** (doc 02A).
    - El administrador del restaurante ve "Mi plan" (módulos, complementos que puede agregar, cuenta y pagos) y un aviso de mora o de prueba por terminar.
- **Consecuencias:**
  - Los cambios de módulos aplican de inmediato; el doc 42 los propone desde el siguiente periodo, y eso queda como política comercial manual.
  - "Suspendido" deja solo el módulo base (comportamiento existente); no es una vista de solo lectura de todo.
  - No hay cobro recurrente automático ni facturación electrónica del servicio.
- **Cuándo revisar:**
  - Al validar paquetes y precios con los primeros clientes (doc 42, sección 10).
  - Al automatizar el cobro de suscripciones con una pasarela recurrente.
  - Si se necesita cuenta por cobrar (fiado, doc 20 sección 10).

## ADR-005 (avance): impresión desde el navegador

En la fase 0 se implementó la opción A: tirilla de comanda sin precios (80 mm), tirilla de orden con precios y hoja de QR por mesa, todas con `window.print` y estilos de impresión. La decisión definitiva sigue **pendiente** de las pruebas con impresoras reales.

## ADR pendientes por abrir

- Cola de tareas en segundo plano.
- Proveedor de facturación electrónica.
- Pasarela de pagos.
- Estrategia offline del MVP.
- Hosting y proveedor de infraestructura.

## Plantilla para nuevos ADR

```
## ADR-0XX: Título
- Estado: Propuesta | Aprobada | Pendiente | Reemplazada
- Contexto:
- Opciones evaluadas:
- Decisión:
- Consecuencias:
- Cuándo revisar:
```
