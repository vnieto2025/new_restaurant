# 02 - Reglas Globales

**Estado:** Propuesto

Reglas **transversales** que aplican a todos los módulos. Las reglas propias de cada módulo viven en `36 - Reglas de Negocio`. Cada regla tiene un código (RG-nn) para poder citarla.

## Identificadores

- **RG-01.** Todo registro tiene un identificador único universal (UUID). No se exponen identificadores secuenciales en URLs públicas.
- **RG-02.** Todo registro de un cliente lleva `empresa_id`. Ver `02A`.

## Dinero e impuestos

- **RG-03.** El dinero nunca se maneja con números de punto flotante. Se usa tipo decimal exacto o enteros en la unidad menor.
- **RG-04.** Cada valor monetario se guarda con su moneda. Moneda por defecto: **COP** `[POR CONFIRMAR]`.
- **RG-05.** Los precios se guardan **sin impuesto** y el impuesto se calcula por producto y configuración del restaurante; o con impuesto incluido, pero siempre de forma consistente en todo el sistema. **Decisión pendiente** (ver ADR-010).
- **RG-06.** Las tasas de impuestos son **configurables** y con vigencia por fecha. Nunca se escriben fijas en el código.
- **RG-07.** Una factura emitida no se modifica. Se corrige con documentos de ajuste (nota crédito o equivalente).

## Fechas y tiempo

- **RG-08.** Todas las fechas y horas se guardan en **UTC**. Cada restaurante tiene su zona horaria (por defecto `America/Bogota`) para mostrarlas.
- **RG-09.** Los reportes se agrupan por **jornada operativa**, no por día calendario. Cada restaurante define a qué hora comienza su jornada.
- **RG-10.** Los registros guardan siempre fecha de creación y de última modificación.

## Datos y borrado

- **RG-11.** El borrado es **lógico** (marcado como eliminado) para toda entidad con historial: productos, mesas, usuarios, clientes, proveedores.
- **RG-12.** Nunca se borra una orden, un pago, una factura ni un movimiento de inventario; solo se anulan con motivo y usuario.
- **RG-13.** Los precios y nombres de producto se **copian** a la orden al crearla (instantánea), para que cambios futuros no alteren el historial.

## Auditoría

- **RG-14.** Se audita siempre: anulaciones, descuentos, cambios de precio, cambios de estado manuales, aperturas y cierres de caja, cambios de permisos, inicios de sesión fallidos.
- **RG-15.** Todo registro de auditoría contiene quién, cuándo, qué cambió (antes y después) y desde qué dispositivo.

## Seguridad

- **RG-16.** Ninguna consulta puede devolver datos de otra empresa. El aislamiento se aplica en el backend, no solo en la interfaz.
- **RG-17.** Las contraseñas nunca se guardan en claro. Se usan algoritmos de hash modernos para contraseñas.
- **RG-18.** Los datos personales de clientes se tratan según la normativa de protección de datos aplicable (ver `32A`).
- **RG-19.** Los datos de tarjetas **no se almacenan** en el sistema; los procesa la pasarela de pagos.

## Operación y fiabilidad

- **RG-20.** Toda operación de creación crítica (orden, pago) acepta una **clave de idempotencia** para que un reintento no produzca duplicados.
- **RG-21.** Una orden enviada a producción puede editarse solo con las reglas definidas en `15`; cualquier edición genera un aviso en la pantalla de producción.
- **RG-22.** Los estados siguen una máquina de estados: solo se permiten las transiciones definidas en `16`.

## Presentación

- **RG-23.** Idioma de interfaz: español. La arquitectura admite agregar idiomas después.
- **RG-24.** Los colores de estado son los mismos en todas las pantallas: azul claro (nuevo), amarillo (en proceso), verde (entregado), rojo (cancelado o perdido).
- **RG-25.** Los importes se muestran con el formato de la moneda del restaurante (en COP, sin decimales).

## Módulos

- **RG-26.** Ningún módulo accede directamente a las tablas de otro; se comunican por interfaces definidas (ver `03` y `04`).
- **RG-27.** Una función de un módulo no contratado debe estar **ausente o bloqueada**, nunca a medias. Ver `02A`.
