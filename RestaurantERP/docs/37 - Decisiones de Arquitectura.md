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
  - El pedido de domicilio hecho por el propio cliente desde la web quedó pendiente; se resolvió en el ADR-040.
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

## ADR-040: Domicilio pedido por el cliente en la web

- **Estado:** Aprobada (2026-10-28). Cierra el pendiente de domicilios del ADR-034 y el de "retener pedidos pendientes de pago" del ADR-036.
- **Contexto:**
  - El doc 17A (sección 2.6) pide que el cliente llegue por un enlace o QR de domicilios, vea la carta y deje nombre, dirección, teléfono y zona de envío.
  - El canal tiene riesgo de spam y datos falsos (doc 17A, sección 5): límites, validación de teléfono y aprobación opcional.
  - No hay proveedor de SMS para verificar el celular.
- **Opciones evaluadas:**
  - A) Un sitio de domicilios aparte con su propia carta y registro de clientes.
  - B) Reutilizar la carta pública (`/q/<token>`) con un QR de tipo "domicilio" sobre la mesa externa.
- **Decisión: B.**
  - **Enlace:** un `qr_acceso` de tipo `domicilio` en la mesa externa, junto al de "para llevar". Los listados y la regeneración de QR de mesas no lo tocan; se administra en Domicilios (copiar enlace, imprimir QR, generar uno nuevo que anula el anterior).
  - **Configuración** (`domicilio_web`): activo, aprobación (por defecto sí) y un aviso visible en la carta (horario, tiempo estimado). Sin zonas de envío activas el enlace no recibe pedidos.
  - **Pedido:** misma carta y precios del mostrador; el cliente elige su zona (ve la tarifa y el pedido mínimo), escribe dirección, nombre y celular y acepta el aviso de datos (obligatorio). Se crea con `Orden.create_order(canal="domicilio", entrega=...)`; la dirección queda en la ficha del cliente.
  - **Confirmación:** con aprobación activa la orden queda por aprobar y no va a cocina. Quien despacha (`domicilios.despachar`) la confirma o rechaza en Entregas con `/orden/aprobar` y `/orden/rechazar`; ese permiso solo alcanza para órdenes de canal domicilio. Rechazar cierra la entrega como cancelada y no cobra el envío. Mientras espera confirmación no se puede asignar domiciliario.
  - **Pago:** el cliente indica si paga al recibir o en línea (`entrega.forma_pago`, informativo). El pago en línea solo se habilita cuando el pedido ya está confirmado, para no cobrar algo que el restaurante puede rechazar. No se retiene la producción hasta el pago.
  - **Anti-spam:** celular de 7 a 15 dígitos; máximo 3 domicilios por celular cada 30 minutos, contados en la base sobre los pedidos creados (no los intentos rechazados, y un reintento con la misma clave no cuenta); el tope por token del QR de mesa (6 cada 10 minutos) sería un bloqueo para un enlace compartido, así que el de domicilios tiene un freno general de 60 cada 10 minutos. Se mantienen los límites por IP.
  - **Seguimiento:** el cliente ve recibido → en preparación → en camino → entregado, la dirección, el valor del domicilio y el total.
  - El celular del cliente recuerda sus datos de entrega (almacenamiento local) para el siguiente pedido.
- **Consecuencias:**
  - No hay cuentas de cliente con contraseña: la identidad es el celular, como en el resto del sistema (doc 32A).
  - El celular no se verifica con un código; la aprobación manual es la defensa principal contra pedidos falsos.
  - Corregido de paso: las validaciones de "fecha futura" de compras y pagos del servicio comparaban contra la jornada; pasada la medianoche (antes del inicio de jornada) rechazaban la fecha de hoy. Ahora comparan contra la fecha del calendario local (`fecha_local`).
- **Cuándo revisar:**
  - Al tener un proveedor de SMS o WhatsApp para verificar el celular con un código.
  - Si los restaurantes piden retener la cocina hasta recibir el pago en línea.
  - Si se necesita cobertura por mapa en vez de lista de barrios (doc 15B).

## ADR-041: Exportación de datos en CSV y Excel

- **Estado:** Aprobada (2026-10-30). La exportación a formatos de software contable sigue en la fase 3 (doc 21).
- **Contexto:**
  - Los docs 26 (sección 8), 26B y 41 piden descargar datos en formatos abiertos: reportes, horas, propinas, pagos a domiciliarios, clientes, productos y órdenes.
  - Ya existían descargas CSV armadas en el navegador con lo que se ve en pantalla: recortadas (top 15, 300 cancelaciones), sin Excel y sin auditoría.
- **Opciones evaluadas:**
  - A) Seguir generando en el navegador y agregar una librería de Excel al frontend.
  - B) Generar en el servidor con una consulta completa para cada conjunto de datos.
- **Decisión: B.**
  - Pantalla **Exportar datos** (`/admin/exportar`) con periodo y 14 conjuntos: ventas por producto, órdenes, cancelaciones, cuentas, pagos, documentos de venta, compras, movimientos, existencias, productos, clientes, domicilios, horas y liquidaciones. Cada uno en CSV o Excel (`openpyxl`).
  - **Permisos:** `datos.exportar` para entrar (administradores, doc 29). Clientes además exige `clientes.exportar`; horas y liquidaciones exigen `nomina.exportar` (RN-NOM-03). Lo de un módulo no contratado no se ofrece ni se entrega.
  - **Datos de personas:** la pantalla advierte antes de descargar. Cada descarga queda en auditoría con conjunto, formato, filas y periodo. Los clientes anonimizados no salen; domicilios no lleva dirección ni teléfono del cliente. Las horas llevan la nota de que son dato operativo (RN-NOM-02).
  - **Fórmulas:** un texto como `=HYPERLINK(...)` en un nombre se ejecutaría al abrir el archivo. En CSV se antepone un apóstrofo y en Excel la celda se guarda como texto. Lo mismo se aplicó a las descargas CSV que ya existían en el navegador.
  - **Registro de peticiones:** el decorador no copia al log las respuestas que son archivos, solo su nombre.
  - **CSV:** separador `;`, coma decimal y marca BOM, como lo espera Excel en español.
  - Un periodo sin datos avisa en vez de bajar un archivo vacío; más de 100.000 filas pide un periodo más corto en vez de recortar.
- **Consecuencias:**
  - El archivo se genera dentro de la petición, en memoria. El doc 26 prevé tareas en segundo plano para los pesados; no hacen falta con el volumen actual.
  - Un restaurante suspendido o cancelado queda solo con el módulo base y no puede bajar lo de los otros módulos. El doc 41 (RN-ONB-04) pide entregarlo todo al terminar el contrato: queda pendiente con el modo de solo lectura.
  - El PDF del doc 26 sigue saliendo con la impresión del navegador.
- **Cuándo revisar:**
  - Al construir el modo de solo lectura para suspendidos.
  - Si las descargas empiezan a tardar: pasarlas a segundo plano.
  - Al integrar un software contable o de nómina (fase 3).

## ADR-042: Solo lectura al suspender y solo exportación al cancelar

- **Estado:** Aprobada (2026-10-30). Reemplaza lo que el ADR-039 y el ADR-041 dejaron pendiente sobre los restaurantes suspendidos.
- **Contexto:**
  - Los docs 02A y 06 dicen: suspendido es solo lectura y nunca se pierden datos; cancelado es acceso solo para exportar durante un plazo. El doc 41 (RN-ONB-04) exige entregar los datos completos al terminar.
  - El sistema dejaba al suspendido solo con el módulo base: no veía sus ventas ni sus órdenes. Una empresa cancelada no podía entrar y no podía bajar nada.
  - Todas las rutas son POST: el método no distingue leer de escribir.
- **Opciones evaluadas:**
  - A) Quitar permisos de escritura: no sirve, porque muchas pantallas de consulta usan los mismos permisos que las de gestión.
  - B) Marcar las rutas que escriben: una ruta nueva sin marcar quedaría abierta en un restaurante suspendido.
  - C) Lista cerrada de las rutas que sí se permiten.
- **Decisión: C** (`Utils/acceso.py`), revisada en `JWTBearer` después de módulo y permiso.
  - **Modos:** `completo`, `lectura` (empresa o contrato suspendidos, o vigencia vencida, incluida la prueba) y `exportacion` (empresa o contrato cancelados). El servidor lo calcula en cada petición y lo devuelve en la sesión.
  - **Lectura:** se conservan los módulos contratados y los permisos; pasan las rutas de consulta, las descargas y las de sesión. Lo demás responde 403 `solo_lectura` con un mensaje claro. Entrar no abre turno de mesero.
  - **Exportación:** solo pasan las descargas y las rutas de sesión, con los permisos de exportar. Quien no los tiene no entra. El plazo es de **90 días** desde la cancelación (`contrato.cancelado_en`, `empresa.cancelada_en`); al terminar nadie entra a ese restaurante. Reactivar borra la fecha.
  - **Lo público:** `modulos_activos` ahora también mira la empresa, así el QR, el domicilio web y el pago en línea tampoco reciben nada de una empresa suspendida (antes el pago en línea sí podía). Los avisos de la pasarela siguen entrando para no perder un pago ya hecho.
  - **Interfaz:** aviso permanente arriba en todas las pantallas. Con contrato cancelado la navegación lleva siempre a Exportar datos.
  - Una prueba recorre todas las rutas con sesión y exige 403 a las que no están en la lista.
- **Consecuencias:**
  - Los botones de guardar siguen visibles en solo lectura: al usarlos se recibe el mensaje que explica la suspensión. Ocultarlos pantalla por pantalla queda para cuando un cliente lo pida.
  - Toda ruta de consulta nueva debe agregarse a la lista; si no, un restaurante suspendido no la verá.
  - Suspender corta el cobro de las cuentas abiertas. El aviso de mora y los 10 días de gracia son el aviso previo, y suspender sigue siendo una decisión manual de soporte.
- **Cuándo revisar:**
  - Si los contratos llegan a fijar otro plazo de conservación (docs 32A y 42). Los 90 días los confirmó el dueño del producto el 2026-10-30.
  - Si soporte necesita cerrar las cuentas abiertas antes de suspender.

## ADR-043: Importación de productos desde una hoja de cálculo

- **Estado:** Aprobada (2026-10-30).
- **Contexto:** los docs 12 y 41 piden cargar la carta desde CSV o Excel para el inicio de cada cliente. Crear 80 platos a mano es el primer obstáculo.
- **Decisión:**
  - Plantilla Excel, revisión sin guardar y aplicación. El servidor no guarda el archivo: al aplicar lo vuelve a validar completo.
  - **Todo o nada:** con una fila con error no entra ninguna. Evita cartas a medias y, como lo existente se omite, subir el archivo corregido no duplica.
  - **Columnas:** producto, categoría y precio obligatorios; descripción, punto de producción e impuesto opcionales. Las categorías que no existen se crean; los puntos y los impuestos deben existir, porque un error de escritura ahí mandaría el plato al lugar equivocado.
  - **Precios:** se aceptan `18000`, `18.000`, `18,000` y `$ 18.000`. Lo ambiguo, como `18,5`, es error de la fila: no se adivina.
  - **Si ya existe:** por defecto se deja igual. Con "actualizar" se puede subir una lista de precios: exige `catalogo.precios` y audita cada cambio de precio como si fuera a mano.
  - El producto nuevo queda en todas las cartas, igual que al crearlo a mano. Los grupos de modificadores no se importan.
  - **Archivo:** viaja en base64 dentro del JSON, para conservar la regla de la API. Hasta 2 MB y 1.000 filas con datos, y no se copia al registro de peticiones. De un Excel se lee el valor calculado, nunca la fórmula.
- **Consecuencias:** cada importación queda en auditoría. El CSV acepta `;` o `,` y UTF-8 o Windows-1252, lo que suele producir Excel.
- **Cuándo revisar:** si los clientes piden importar modificadores, insumos o clientes.

## ADR-044: Rol de contador o auditor

- **Estado:** Aprobada (2026-10-30). Completa el rol previsto en el doc 08.
- **Decisión:**
  - Rol fijo `contador`, de alcance restaurante, que el administrador asigna en Personal. Tiene reportes, órdenes, caja, facturación, compras, inventario, cupones y auditoría en modo consulta, más las descargas de datos y de nómina.
  - **Sin clientes:** el doc 29 pide conceder aparte la exportación de datos personales. Si un contador la necesita, el administrador le entrega el archivo.
  - Una prueba recorre todas las rutas que no son de consulta y exige que este rol reciba 403 en cada una.
- **Consecuencias:** los documentos de venta sí traen el nombre y el documento de quien recibe la factura, porque son soporte contable. Solo ve los módulos contratados.
- **Cuándo revisar:** si un contador atiende varios restaurantes o empresas: un usuario pertenece a una sola empresa (RN-EMP-03).

## ADR-045: Paquete de Docker listo para instalar

- **Estado:** Aprobada (2026-10-30). El hosting sigue pendiente (doc 40, sección 4).
- **Contexto:** ya existían los contenedores, pero nadie los había probado, y faltaba lo necesario para un piloto: respaldos, restauración, revisión de salud y cerrar lo que queda público en producción.
- **Decisión:**
  - **Respaldos:** servicio `respaldos` con un `pg_dump` diario, verificado con `pg_restore --list` antes de darlo por bueno, y retención configurable. `ops/restaurar.sh` restaura sin dueños ni permisos y corre `seed.py` para reponer permisos y RLS.
  - **Se prueba de verdad:** GitHub Actions construye las imágenes, levanta todo, corre el recorrido `fase1` por nginx y hace respaldo, cambio y restauración en cada envío (`e2e/prueba_docker.py`).
  - **Producción:** sin `APP_ENV` no se publica `/docs`, CORS solo acepta `PUBLIC_URL` y el backend no arranca con una `MY_SECRET_KEY` corta. Compose se niega a arrancar si falta una clave.
  - **Salud:** `GET /salud` revisa la base. Docker lo usa para ordenar el arranque y sirve para un monitor externo.
  - **nginx:** `client_max_body_size 4m`, porque con el valor por defecto la importación de productos fallaría, y cabeceras básicas de seguridad.
  - Guía en `docs/40A`.
- **Consecuencias:**
  - **Aún sin resolver, por depender del hosting:** HTTPS, copia de los respaldos a otro lugar y su cifrado, monitoreo y alertas, despliegue automático.
  - Un solo proceso del backend: el tiempo real y las colas viven dentro de él.
  - El respaldo no incluye `.env`, y sin `MY_SECRET_KEY` no se leen las credenciales guardadas.
- **Cuándo revisar:** al elegir el hosting, y antes de escalar a varias réplicas.

## ADR-046: Asistente de configuración inicial

- **Estado:** Aprobada (2026-10-30). Implementa el doc 41, secciones 2.3 a 2.7.
- **Opciones evaluadas:**
  - A) Pantallas seguidas que repiten cada formulario. Duplica mucho y se desincroniza de las pantallas reales.
  - B) Lista de pasos que lee el estado real y lleva a la pantalla de cada cosa.
- **Decisión: B.**
  - Cada paso se **deduce de los datos**: lo que se hizo en su pantalla, o antes del asistente, cuenta. No se guarda avance aparte.
  - Mesas e importación de la carta se hacen en la misma pantalla, por ser lo más tedioso. El resto abre su pantalla.
  - **Solo se confirman a mano** los QR impresos y el ensayo en vacío (`restaurante.puesta_en_marcha`), con usuario y fecha, y quedan en auditoría.
  - **Ensayo (RN-ONB-01):** se confirma solo si lo obligatorio está listo. Es una declaración de la persona: el sistema no verifica que haya ocurrido.
  - Los pasos dependen de los módulos contratados: un plan sin pedidos no pide mesas ni QR, y el personal es opcional.
  - El aviso en administración desaparece al confirmar el ensayo y no reaparece aunque luego cambien los datos.
- **Consecuencias:**
  - No impide operar: es una guía, no un candado. La regla RN-ONB-01 se cumple por acompañamiento, no por bloqueo.
  - Las órdenes y ventas del ensayo quedan en los reportes de ese día; no hay modo de prueba ni forma de borrarlas. La pantalla avisa, y que el cierre de jornada bloquea más órdenes ese día.
- **Cuándo revisar:** con el primer piloto, si el ensayo ensucia reportes o facturación: un modo de prueba sería el siguiente paso. *(Hecho en ADR-053: el ensayo se recomienda en el restaurante de práctica.)*

## ADR-047: Reportes de la fase 2

- **Estado:** Aprobada (2026-10-30). Implementa el doc 26, sección 5, salvo lo que ya existía (margen en Recetas y costos, rentabilidad en Cupones).
- **Decisión:**
  - `/reporte/analisis` entrega horas pico, tiempos de preparación, domiciliarios, clientes e inventario, según módulos; se calcula en vivo, sin tablas de resumen.
  - **Horas pico:** usa las mismas cuentas pagadas que el total de ventas y una prueba exige que sumen igual (RN-REP-01). Sin caja, los ítems vendidos. Las horas van en la zona horaria del restaurante.
  - **Tiempos:** de que el ítem entra a producción (o se aprueba) al último despacho. Muestra promedio y percentil 90, porque el promedio esconde las demoras.
  - **Clientes:** el nombre solo lo ve quien tiene `clientes.ver`; el contador ve cantidades (doc 29). Inactivo: 30 días sin comprar.
  - **Sedes:** `/reporte/sedes`, solo para el administrador de empresa y con más de un restaurante.
  - El mapa de calor escribe el valor en cada celda: no depende del color.
- **Consecuencias:** con muchos datos, un periodo largo puede tardar; el doc 26 prevé tablas de resumen cuando haga falta.
- **Cuándo revisar:** cuando un periodo de un año tarde más de lo aceptable.

## ADR-048: Duplicar productos y copiarlos entre restaurantes

- **Estado:** Aprobada (2026-10-30). Docs 07 y 12.
- **Decisión:**
  - **Duplicar:** crea "X (copia)" con la misma categoría, precio, cartas, modificadores y receta, y abre el formulario para ajustarla.
  - **Copiar a otra sede:** solo el administrador de empresa, y solo entre sus restaurantes. Copia lo que esté en la lista filtrada, y así se puede pasar una sola categoría.
  - **No pisa nada:** un producto que ya existe allá con ese nombre se deja igual, para conservar los precios de cada local.
  - **Por nombre:** categoría y grupos de modificadores se reutilizan si existen o se crean. Punto de producción e impuesto se enlazan solo si existen con ese nombre; si no, aplica el de la categoría o el de defecto.
  - **Las recetas no se copian entre sedes:** cada local tiene sus propios insumos y costos.
- **Consecuencias:** los catálogos siguen siendo independientes: un cambio posterior de precio no se propaga. El catálogo compartido por empresa queda fuera.
- **Cuándo revisar:** si una cadena necesita cambiar precios en todas sus sedes a la vez.

## ADR-049: Fotos y alérgenos de los productos

- **Estado:** Aprobada (2026-11-01). Docs 11 y 12.
- **Decisión:**
  - **Carpeta por restaurante** (lo pidió el dueño del producto): `media/restaurantes/<id>-<nombre>/productos/<aleatorio>.webp`. El número la hace única y el nombre deja reconocerla. La ruta completa queda en `producto.imagen`, así que cambiar el nombre del restaurante no rompe nada.
  - **Compresión con Pillow:** WebP, máximo 1000 px por lado, bajando la calidad hasta acercarse a 150 KB. No se guarda la original. El celular también reduce la foto antes de subirla, para que una de cámara no se rechace ni tarde.
  - **Validación:** se abre como imagen de verdad, solo JPG, PNG o WebP, hasta 6 MB y 40 megapíxeles. Regenerarla quita los metadatos, como la ubicación GPS.
  - **Se sirve en `/media`, sin sesión**, porque la carta es pública. El nombre aleatorio impide adivinar otras fotos y permite caché larga. No hay listado de carpetas.
  - **Copias independientes:** duplicar o copiar a otra sede crea otro archivo, para que borrar una foto no deje a otro producto sin la suya.
  - **Docker y respaldos:** volumen `media_data`. El respaldo diario agrega `<nombre>.fotos.tar.gz` y `restaurar.sh` lo repone. CI lo prueba.
  - **Permisos:** un volumen nuevo no hereda el dueño de la imagen, así que el contenedor arranca como root solo para ajustar esa carpeta y corre la aplicación como usuario 1000. `/salud` falla si no se puede escribir ahí, y CI comprueba el usuario.
  - **Alérgenos:** texto libre del restaurante en `producto.alergenos`, también en la importación; la carta lo muestra como "Contiene: ...".
- **Consecuencias:**
  - Los alérgenos son lo que escribe el restaurante: el sistema no los deduce de la receta ni los verifica.
  - Reiniciar la base de desarrollo no borra los archivos; quedan huérfanos en `backend/media`.
  - Con varios servidores harían falta almacenamiento compartido; hoy hay uno solo (doc 40A).
- **Cuándo revisar:** al comprar el hosting, si ofrece almacenamiento de objetos.

## ADR-050: Combos

- **Estado:** Aprobada (2026-11-06). Doc 12, sección 4. El dueño del producto eligió que las ventas cuenten como el combo.
- **Decisión:**
  - **Producto de tipo combo,** con partes (`combo_componente`) y opciones por parte (`combo_opcion`), cada una con valor extra. Con una sola opción la parte es fija. Un combo no va dentro de otro.
  - **En la orden:** la línea del combo cobra su precio más lo extra de lo elegido, incluidos los modificadores de las partes. Cada parte es un ítem hijo de valor 0 (`orden_item.combo_item_id`) que va a su cocina o bar y descuenta su propio inventario.
  - **Estado:** el combo está en preparación si alguna parte arrancó, y listo o entregado solo cuando todas lo están. Así el mesero no lo ve listo antes de tiempo.
  - **Cancelaciones:** cancelar el combo cancela sus partes; si una parte se cancela o se agota en cocina, cae el combo completo, porque es lo que se cobra. Cancelar algo ya cancelado no hace nada, lo que protege los procesos que cancelan varios ítems seguidos.
  - **Cobro y factura:** una línea por combo con sus partes como detalle; las partes de valor 0 no aparecen como líneas.
  - **Reportes:** se vende el combo. Aparte, "Lo que salió en combos" muestra las unidades de cada parte. Las cancelaciones y los favoritos del cliente cuentan el combo.
  - **Todos los canales:** se arma en el cálculo de precio y en la inserción de ítems que ya comparten mesa, QR, mostrador, domicilio y venta directa.
  - **Copiar a otra sede** omite los combos: sus partes son productos de ese local, así que se arman allá.
- **Consecuencias:**
  - El margen del combo no sale en Recetas y costos: el combo no tiene receta propia, sus partes sí.
  - Si se cambian las partes de un combo, lo ya pedido no se afecta: cada ítem guarda su copia.
- **Cuándo revisar:** si hacen falta partes con varias elecciones distintas ("2 salsas a elegir") o combos que repartan el valor entre sus partes.

## ADR-051: Sugerir agotados con el inventario

- **Estado:** Aprobada (2026-11-06). Doc 12, sección 5.
- **Decisión:**
  - **Porciones que alcanzan:** para cada producto simple activo con receta se calcula el stock de cada ingrediente entre lo que lleva una porción (con su merma y rendimiento); el menor manda. Se calcula al consultar, sin tablas nuevas.
  - **Solo insumos con inventario cargado:** cuenta un insumo que tuvo alguna entrada, compra, producción o ajuste. Uno que solo tiene consumos nunca se cargó y su stock en cero no dice que se acabó; así un restaurante que no lleva inventario no recibe sugerencias falsas.
  - **Tres listas en `/producto/sugerir_agotados`** (permiso `productos.agotar`, módulo inventario): agotar (no alcanza para una porción), se están acabando (5 o menos) y agotados que ya se pueden preparar.
  - **Solo sugiere, nunca agota solo:** el stock del sistema puede no coincidir con la nevera. "Todavía hay" oculta la sugerencia hasta que el stock vuelva a cambiar. Agotar sigue por `/producto/agotado`, con su auditoría y aviso en tiempo real.
  - **Dónde se ve:** la pantalla de cocina o bar muestra lo de su punto (el del producto o el de su categoría; un plato que depende de la zona aparece en todos) y se refresca con cada comanda, porque abrirla descuenta inventario. Hoy muestra las tres listas de todo el restaurante.
  - **Combos:** la sugerencia dice qué combos se quedan sin ese plato; al agotarlo, el combo deja de ofrecerse como ya pasaba (ADR-050).
- **Consecuencias:** las opciones de modificador con insumo ("Queso extra") no se sugieren: un modificador no se puede marcar agotado. Una merma registrada desde Existencias no avisa en tiempo real; se ve en la siguiente consulta de la pantalla.
- **Cuándo revisar:** si los restaurantes piden agotar opciones de modificador o que el umbral de "se están acabando" sea configurable.

## ADR-052: Alertas del dueño y resumen del día

- **Estado:** Aprobada (2026-11-07). Docs 27 (secciones 2 y RN-DAS-03), 26 y 31B.
- **Decisión:**
  - **Alertas calculadas al consultar,** sin tablas de eventos: comandas que pasan el tiempo objetivo del punto (o el umbral si no tiene), platos listos sin entregar, mesas abiertas muchas horas, una persona con muchas cancelaciones en la jornada, turnos con diferencia de caja, stock bajo o negativo, y numeración por agotarse o vencerse. Cada una aparece solo si el restaurante tiene contratado su módulo.
  - **Umbrales con valores sugeridos** y configurables en `restaurante.alertas` (JSON), que también guarda las apagadas y las silenciadas. **Silenciar vale por la jornada:** al día siguiente vuelve a aparecer si sigue pasando.
  - **En Hoy,** se revisan cada minuto y con cada evento de órdenes. Verlas pide `reportes.ver`; silenciarlas y configurarlas, `restaurante.configurar`. El nivel urgente usa un borde doble de tinta, no los colores de estado de las órdenes (RN-EST-06).
  - **Resumen del día** (`/reporte/resumen_diario`): ventas con comparativo del mismo día de la semana pasada, cuentas y ticket, propinas y descuentos, medios de pago, lo más pedido, cancelaciones, turnos abiertos o con diferencia, inventario bajo y agotados. Sale en pantalla y como texto listo para WhatsApp; se puede consultar cualquier jornada pasada.
  - **Al cerrar la jornada** en caja, si el dueño dejó su celular en `restaurante.resumen_diario`, el resumen queda como aviso `resumen_diario` en la misma cola de WhatsApp de los clientes: en modo manual lo envía quien atiende Mostrador o Entregas con un toque; en automático sale por el proveedor. Una falla nunca frena el cierre. Sin el módulo de pedidos (donde viven los avisos), queda el botón "Enviar por WhatsApp" de la página.
- **Consecuencias:** un restaurante sin caja no cierra jornada, así que no recibe el resumen automático: lo abre o lo envía desde la página. El resumen a la hora del cierre no se repite si la jornada se consulta después; la página siempre muestra las cifras actuales de esa jornada.
- **Cuándo revisar:** cuando haya proveedor de correo, o si el dueño de varias sedes pide un resumen consolidado de la empresa.

## ADR-053: Restaurante de práctica

- **Estado:** Aprobada (2026-11-07). Doc 33, sección 7; doc 41 (capacitación y ensayo en vacío).
- **Decisión:**
  - **Un restaurante de práctica por restaurante real** (`restaurante.practica_de`), no una marca en cada orden: el sistema ya separa todo por restaurante, así que órdenes, cobros, turnos, inventario, reportes, cierres, alertas y tiempo real de la práctica quedan aparte sin tocar ninguna consulta.
  - **Se crea copiando la configuración** (`Utils/practica.py`): carta, categorías, productos y combos, modificadores, mesas y zonas con QR nuevos, puntos de producción, horarios, impuestos, medios de pago, numeración POS desde cero, domiciliarios, proveedores, insumos y recetas. La copia es genérica por tabla, traduciendo las referencias a los ids nuevos. Las existencias entran como un ajuste, así el inventario de práctica arranca igual y las sugerencias de agotados funcionan.
  - **No se copia** lo de la operación (órdenes, turnos, compras, avisos, auditoría) ni la configuración de facturación electrónica, pagos en línea, avisos por WhatsApp y domicilio web.
  - **Módulos:** los del contrato del real, **sin facturación electrónica ni pagos en línea**, que tocarían la DIAN o dinero de verdad. La práctica no tiene contrato propio ni aparece en la consola de plataforma ni en el comparativo entre sedes.
  - **Personal:** entra con su mismo usuario quien tiene acceso al real, con los mismos permisos; sus zonas y puntos se buscan por nombre en la práctica, así el personal nuevo no necesita nada extra. No aparece en la lista de restaurantes: se entra con "Entrar a la práctica" (inicio y puesta en marcha) y una franja con rayas en todas las pantallas dice que nada cuenta y lleva de vuelta al real. Las tirillas salen con el nombre "… · Práctica".
  - **Clientes:** son de la empresa; los creados en la práctica llevan `cliente.practica_restaurante_id`, solo se ven allí y no chocan con el celular de un cliente real (índices únicos parciales).
  - **Reiniciar** borra todo lo de la práctica, de las tablas hijas a las padres, y vuelve a copiar el real. Se niega a correr sobre un restaurante que no sea de práctica. Crear y reiniciar piden `restaurante.configurar` y quedan en la auditoría del real.
  - **Fotos:** la práctica usa los mismos archivos; subir o quitar una foto allí se bloquea para no borrar la del real.
- **Consecuencias:** un cambio en la carta del real no llega a la práctica hasta reiniciarla. Si el real cambia o borra una foto, la práctica puede mostrarla rota hasta reiniciar. Los avisos por WhatsApp en la práctica son manuales: alguien podría escribirle de verdad a un cliente si usa su celular real.
- **Cuándo revisar:** si hace falta practicar facturación electrónica (con el proveedor simulado forzado) o si se quiere sincronizar la carta sin borrar lo practicado.

## ADR-054: Verificación en dos pasos

- **Estado:** Aprobada (2026-11-08). Docs 08 y 32.
- **Decisión:**
  - **Códigos TOTP** (RFC 6238, 6 dígitos cada 30 segundos) de cualquier aplicación autenticadora. Implementado en `Utils/totp.py` sin librerías nuevas; el QR lo genera `segno`, que ya se usaba para las mesas. Sin SMS ni correo: no hay proveedor y el SMS es el factor más débil.
  - **Guardado:** el secreto va cifrado con la clave del servidor (como las credenciales de pasarela). Se guarda el último código usado, para que uno visto por encima del hombro no sirva otra vez. De los 10 códigos de respaldo solo se guarda la huella, y cada uno sirve una vez.
  - **Ingreso en dos llamadas a `/login`:** con la clave correcta y sin código responde `requiere_codigo`, sin sesión; la interfaz pide el código y repite la llamada con él. No hay sesión intermedia que pueda quedar a medias. Los códigos tienen su propio límite de intentos por usuario (5 cada 5 minutos).
  - **El PIN de las tablets no pide código:** quien tiene la verificación activa no entra con PIN, entra con usuario, clave y código.
  - **Quién:** cualquiera puede activarla en Mi cuenta (pantalla nueva, que también trae el cambio de clave). A los administradores (superadministrador, de empresa y de restaurante) se les recomienda en Hoy. El administrador de la empresa puede exigirla (`empresa.exigir_2fa`): quien no la tenga, al entrar solo puede ir a activarla, y el backend rechaza todo lo demás con `activar_2fa`. En el servidor real `EXIGIR_2FA_PLATAFORMA=1` la exige al superadministrador (doc 32).
  - **Perdió el celular y los códigos:** quien gestiona usuarios se la quita (queda en auditoría) y la persona la vuelve a activar. Nadie se la quita a sí mismo por ese camino, y a un administrador de empresa solo se la quita otro administrador de empresa.
  - Los códigos, secretos y claves no se copian al registro de peticiones.
- **Consecuencias:** si el superadministrador pierde su celular y sus códigos, solo se recupera desde la base de datos. La guía de instalación pide guardar sus códigos fuera del servidor.
- **Cuándo revisar:** si se agrega correo como canal de recuperación, o llaves de seguridad (WebAuthn).

## ADR-055: Solo lectura sin botones de guardar

- **Estado:** Aprobada (2026-11-08). Completa ADR-042.
- **Decisión:**
  - **Directiva `v-escribe`:** marca lo que guarda datos. Con el restaurante suspendido o cancelado, `<html>` lleva la clase `solo-lectura` y el CSS oculta lo marcado. En un formulario solo se oculta su botón de guardar: la consulta y los filtros siguen funcionando.
  - **Marcado generado:** el script de marcado lo pone a un botón o formulario cuando su acción llama a una ruta de la API que no está en la lista de solo lectura del backend (`RUTAS_LECTURA`, la misma que aplica el servidor), y a los botones que abren formularios de crear o editar. Los que solo avisan a la pantalla que los contiene (comanda de cocina, movimientos de inventario) se marcaron a mano.
  - **La API sigue siendo la que decide:** un botón que se escape responde con el aviso de solo lectura, como antes.
  - Las pantallas públicas y la consola de plataforma no se marcan: nunca están en solo lectura.
- **Consecuencias:** un botón nuevo que escriba debe llevar `v-escribe`. Si no lo lleva, en solo lectura se ve pero responde con el aviso.
- **Cuándo revisar:** si se agregan muchas pantallas nuevas, conviene volver a correr el script de marcado y revisar su informe.

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
