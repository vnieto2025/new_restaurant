# 01 - Glosario

**Estado:** Propuesto

Vocabulario único del proyecto. En código, base de datos, pantallas y documentación se usan **estos** términos y no sinónimos.

> **Decisión de vocabulario:** el término oficial es **Orden** (no "pedido"). "Pedido" puede aparecer en la conversación informal o en textos de cara al cliente final, pero no en el modelo ni en la documentación técnica. `[POR CONFIRMAR]`

## Estructura

| Término | Definición |
|---|---|
| **Plataforma** | El sistema completo, operado por el proveedor del software |
| **Empresa** | Cliente principal del software; dueña de uno o varios restaurantes. Raíz del aislamiento de datos |
| **Restaurante** | Un local o negocio concreto. Puede tener contrato propio e independiente |
| **Contrato** | Acuerdo de uso del software por restaurante: módulos activos, vigencia, estado |
| **Módulo** | Conjunto de funcionalidades que se activa o desactiva por contrato |
| **Zona** | Área del restaurante con identidad propia (comida corriente, comidas rápidas, bar, gourmet). Tiene su carta, sus mesas, sus meseros y sus tablets |
| **Mesa** | Puesto físico dentro de una zona, con QR propio |
| **Mesa externa** | Mesa estándar que representa a quien no se sienta: para llevar, mostrador, WhatsApp, domicilio |
| **Punto de producción** | Lugar donde se preparan ítems: cocina, bar, parrilla, postres, panadería |
| **Tablet de zona** | Pantalla táctil asociada a una zona desde donde el mesero atiende sus mesas |
| **Carta** | Conjunto de productos ofrecidos, asociado a una o varias zonas |

## Personas

| Término | Definición |
|---|---|
| **Usuario** | Persona con acceso al sistema (administrador, mesero, cajero, cocina, domiciliario) |
| **Rol** | Conjunto de permisos que define lo que un usuario puede hacer |
| **Mesero** | Usuario que atiende mesas y toma órdenes |
| **Domiciliario** | Persona que entrega órdenes a domicilio; se identifica con un código |
| **Cliente** | Persona que compra. Puede ser anónima o registrada |
| **Cliente registrado** | Cliente con datos guardados cuyo historial se reconoce |

## Operación

| Término | Definición |
|---|---|
| **Orden** | Solicitud de productos hecha por un cliente o en su nombre, por cualquier canal |
| **Ítem de orden** | Un producto dentro de una orden, con cantidad, notas y modificadores |
| **Comanda** | Parte de una orden dirigida a un punto de producción |
| **Canal** | Origen de la orden: tablet, QR de mesa, QR para llevar, WhatsApp, domicilio web, plataforma externa |
| **Tirilla** | Documento impreso (térmico) con información de una comanda o de una cuenta |
| **Estado de la orden** | Situación de la orden en el flujo (ver `16`) |
| **Despachado** | La cocina terminó la comanda y la entregó al mesero o al domiciliario |
| **Entregado** | La orden llegó al cliente `[POR CONFIRMAR si es distinto de despachado]` |
| **Cancelada / perdida** | Orden anulada o que no pudo cumplirse. La "pérdida" se distingue de la cancelación por su motivo |
| **Pendiente de aprobación** | Orden de QR que espera que el mesero la acepte antes de llegar a producción |
| **Sesión de mesa** | Periodo en que una mesa está en uso; agrupa las órdenes de todos los clientes de esa mesa hasta cerrar la cuenta |
| **Modo de aceptación** | Configuración por zona de cómo se aceptan órdenes por QR: libre, con aprobación o mesa abierta por mesero |
| **Despacho directo** | Ítem que no pasa por producción (por ejemplo una gaseosa de nevera) y se marca despachado al crearse |
| **Token de QR** | Código opaco y revocable contenido en el QR; el servidor lo traduce a empresa, restaurante, zona y mesa |
| **Trabajo de impresión** | Registro en cola de algo que debe imprimirse; desacopla la lógica de negocio del método de impresión |

## Dinero

| Término | Definición |
|---|---|
| **Cuenta** | Lo que se cobra al cliente; puede agrupar varias órdenes de una mesa |
| **Pago** | Entrada de dinero que cubre total o parte de una cuenta |
| **Medio de pago** | Efectivo, tarjeta, transferencia, pago en línea, etc. |
| **Factura** | Documento fiscal de la venta |
| **Turno de caja** | Periodo en el que un cajero responde por el dinero de la caja |
| **Arqueo** | Conteo del dinero al cerrar un turno para compararlo con lo registrado |
| **Propina** | Valor que el cliente da voluntariamente; se reparte según reglas configurables |
| **Cupón** | Descuento o beneficio con reglas de uso y vigencia |
| **Jornada operativa** | "Día" del restaurante; puede cruzar la medianoche |

## Logística

| Término | Definición |
|---|---|
| **Insumo** | Materia prima o artículo que se compra y se consume |
| **Receta** | Lista de insumos y cantidades que componen un producto |
| **Movimiento de inventario** | Entrada, salida, ajuste o merma de un insumo |
| **Merma** | Pérdida de un insumo (daño, desperdicio, vencimiento) |
| **Proveedor** | Quien suministra insumos |
| **Compra** | Adquisición de insumos a un proveedor |

## Domicilios

| Término | Definición |
|---|---|
| **Zona de envío** | Área geográfica de entrega con una tarifa asociada |
| **Domicilio** | Orden que se entrega fuera del local |
| **Para recoger** | Orden hecha a distancia que el cliente retira en el local sin cargo de envío |

## Técnicos

| Término | Definición |
|---|---|
| **Tenant** | Unidad de aislamiento de datos; en este proyecto equivale a la **Empresa** |
| **ADR** | Registro de decisión de arquitectura (documento `37`) |
| **KDS** | Kitchen Display System: pantalla de cocina |
| **PWA** | Aplicación web instalable desde el navegador |
| **Idempotencia** | Propiedad de una operación que, repetida, no produce duplicados |
