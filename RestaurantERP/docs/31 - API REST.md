# 31 - API REST

**Estado:** Propuesto

Define **cómo se comunican** las aplicaciones web con el backend y cómo se exponen integraciones. No es la lista final de endpoints: se construye con los módulos.

## 1. Principios

- **API REST sobre HTTPS** con JSON, más **WebSockets** para eventos en tiempo real (`04`).
- **FastAPI** genera documentación **OpenAPI** automática; es la referencia de endpoints.
- **Versionada** en la URL: `/api/v1/...`.
- Cada ruta pertenece a un **módulo** y se bloquea si el módulo no está contratado (`02A`).
- **Sin lógica en el cliente:** precios, estados y permisos se deciden siempre en el servidor.
- Nombres de recursos y campos en **español** y consistentes con el glosario (`01`).

## 2. Tipos de acceso

| Tipo | Quién | Autenticación |
|---|---|---|
| **Administración y operación** | Usuarios con rol | Token de acceso corto + renovación |
| **Dispositivo emparejado** | KDS, tablets de zona | Credencial de dispositivo + (mesero) PIN |
| **Público por QR / enlace** | Clientes en la carta digital | **Token del QR** para resolver contexto; sesión anónima por dispositivo |
| **Integraciones entrantes** | Pasarela de pagos, WhatsApp, plataformas | Firma del webhook o clave del proveedor |
| **Plataforma (interna)** | Superadministrador | Autenticación reforzada |

## 3. Contexto de cada petición

Toda petición fija, antes de tocar datos:

1. **Identidad** (usuario, dispositivo o sesión pública).
2. **Empresa** (tenant) y **restaurante**.
3. **Permisos** del actor y **módulo** contratado.

Sin contexto válido, la petición se rechaza. La empresa se aplica en la base de datos (RLS, `02A`).

## 4. Convenciones

| Tema | Convención |
|---|---|
| **Formato de error** | Objeto con `codigo`, `mensaje` legible, `detalle` y `id_peticion` |
| **Códigos HTTP** | Usados con su significado estándar (400 validación, 401 autenticación, 403 permiso o módulo, 404, 409 conflicto, 422, 429 límite, 5xx) |
| **Idempotencia** | Cabecera `Idempotency-Key` en creación de órdenes, pagos y otras operaciones críticas (RG-20) |
| **Concurrencia** | Control de versión (ETag o campo `version`) en recursos editables para evitar sobrescrituras |
| **Paginación** | Por cursor o por página, con límites máximos |
| **Filtros y orden** | Parámetros uniformes |
| **Fechas** | ISO 8601 en UTC (RG-08) |
| **Dinero** | Cadena decimal o entero en unidad menor, con moneda; nunca flotante (RG-03) |
| **Límites de uso** | Por usuario, dispositivo e IP; más estrictos en endpoints públicos (`10A`) |

## 5. Recursos principales (visión general)

| Grupo | Recursos |
|---|---|
| **Plataforma** | empresas, restaurantes, contratos, módulos |
| **Estructura** | zonas, mesas, qr, puntos-produccion, dispositivos |
| **Personas** | usuarios, roles, turnos, clientes, domiciliarios |
| **Catálogo** | cartas, categorias, productos, modificadores, recetas |
| **Operación** | ordenes, items, comandas, sesiones-mesa, entregas |
| **Dinero** | cuentas, pagos, turnos-caja, facturas, propinas, liquidaciones, cupones |
| **Logística** | insumos, movimientos, compras, proveedores |
| **Transversal** | auditoria, configuracion, notificaciones, reportes |
| **Público** | `/q/{token}` (resolver QR), carta pública, creación de orden pública, estado de orden pública |

## 6. Tiempo real

- Canal **WebSocket** por aplicación (tablet de zona, KDS, caja).
- El cliente se **suscribe** solo a lo que tiene permiso de ver (su zona, su punto de producción).
- Los eventos llevan un identificador y la versión de la entidad; son **avisos**: ante dudas o reconexión, el cliente **vuelve a pedir** el estado a la API (`04`).
- Para la carta pública: **seguimiento de estado** por SSE o sondeo con límites.

## 7. Webhooks entrantes

| Origen | Uso | Requisitos |
|---|---|---|
| **Pasarela de pagos** | Resultado de pagos | Verificar firma; procesar de forma idempotente (`20A`) |
| **WhatsApp** | Estado de mensajes, respuestas | Verificar firma (`31B`) |
| **Proveedor de facturación** | Estado de emisión | Verificar firma (`21A`) |
| **Plataformas de domicilio** | Nuevas órdenes y cambios | Según la plataforma (`31A`) |

Todo webhook: se **guarda crudo** antes de procesarse, se responde rápido y se procesa en segundo plano con reintentos.

## 8. Webhooks salientes y API para terceros (fase 3)

Posibilidad de exponer webhooks o una API a clientes que quieran integrar el sistema con otro software. Fuera del MVP; requiere claves de API por empresa, límites y documentación pública.

## 9. Reglas

- **RN-API-01.** Ninguna ruta devuelve datos de otra empresa (RG-16).
- **RN-API-02.** Toda creación crítica acepta clave de idempotencia (RG-20).
- **RN-API-03.** Un módulo no contratado responde 403 con código `modulo_no_contratado`.
- **RN-API-04.** Los endpoints públicos tienen límites de uso y no exponen identificadores internos (RG-01).
- **RN-API-05.** Los cambios incompatibles de la API requieren nueva versión.
- **RN-API-06.** Los webhooks se validan por firma antes de procesarse.

## 10. Preguntas abiertas

- ¿Autenticación con JWT y renovación, o sesiones en servidor? (Decidir en el primer corte vertical.)
- ¿La carta pública se sirve como sitio aparte con su propia caché? (Probablemente sí.)
- ¿Cuándo se publica una API para terceros?
