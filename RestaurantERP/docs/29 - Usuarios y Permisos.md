# 29 - Usuarios y Permisos

**Estado:** Propuesto

Define **qué puede hacer cada rol**. Los roles y su identificación están en `08`. Este documento es la **única fuente** sobre permisos.

## 1. Modelo

- Un **permiso** es una acción concreta con código: `ordenes.crear`, `ordenes.cancelar_en_proceso`, `caja.anular_cuenta`.
- Un **rol** es un conjunto de permisos.
- Los permisos se evalúan en el **backend** en cada petición (RG-16); ocultarlos en la interfaz es solo comodidad.
- Además del permiso, se verifica el **alcance**: empresa, restaurante y zona asignados al usuario.
- Además, el **módulo** debe estar contratado (`02A`).

**MVP:** roles **fijos** con permisos definidos por el sistema. Los **roles personalizados** por el cliente quedan para fase 2; el modelo por permisos lo hace posible sin rediseñar.

## 2. Matriz de permisos por rol (MVP)

Leyenda: **✔** permitido · **◐** permitido con condición · **—** no permitido

### Órdenes y operación

| Permiso | Admin empresa | Admin restaurante | Cajero | Enc. externos | Mesero | Cocina / bar |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| Crear orden en mesa | — | ✔ | ✔ | — | ✔ (su zona) | — |
| Crear orden externa | — | ✔ | ✔ | ✔ | — | — |
| Aprobar / rechazar orden de QR | — | ✔ | — | — | ✔ (su zona) | — |
| Agregar ítems a orden enviada | — | ✔ | ✔ | ✔ | ✔ | — |
| Cancelar ítem en `nuevo` | — | ✔ | ✔ | ✔ | ✔ | — |
| Cancelar ítem en `en_proceso` o posterior | — | ✔ | ◐ permiso específico | — | — | — |
| Abrir y despachar comanda | — | — | — | — | — | ✔ (su punto) |
| Reabrir comanda despachada | — | ✔ | — | — | — | ✔ (su punto) |
| Marcar `entregado` | — | ✔ | ✔ | ✔ | ✔ | — |
| Marcar producto agotado | — | ✔ | ✔ | — | — | ✔ |
| Trasladar / unir mesas | — | ✔ | ✔ | — | ◐ permiso específico | — |
| Reimprimir tirilla | — | ✔ | ✔ | ✔ | — | ✔ |

### Caja y facturación

| Permiso | Admin empresa | Admin restaurante | Cajero | Enc. externos | Mesero | Cocina / bar |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| Abrir / cerrar turno de caja | — | ✔ | ✔ | — | — | — |
| Cobrar cuenta | — | ✔ | ✔ | ◐ solo externas | — | — |
| Aplicar cupón | — | ✔ | ✔ | ✔ | — | — |
| Aplicar descuento manual | — | ✔ | ◐ permiso específico | — | — | — |
| Anular cuenta pagada | — | ✔ | — | — | — | — |
| Registrar gasto o retiro de caja | — | ✔ | ✔ | — | — | — |
| Cerrar jornada | — | ✔ | — | — | — | — |

### Catálogo y configuración

| Permiso | Admin empresa | Admin restaurante | Cajero | Enc. externos | Mesero | Cocina / bar |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| Gestionar productos y categorías | ✔ | ✔ | — | — | — | — |
| Cambiar precios | ✔ | ✔ | — | — | — | — |
| Gestionar zonas, mesas y QR | ✔ | ✔ | — | — | — | — |
| Revocar QR | ✔ | ✔ | — | — | — | — |
| Gestionar usuarios y roles asignados | ✔ | ✔ | — | — | — | — |
| Configurar restaurante | ✔ | ✔ | — | — | — | — |

### Informes y datos

| Permiso | Admin empresa | Admin restaurante | Cajero | Enc. externos | Mesero | Cocina / bar |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| Ver reportes de ventas | ✔ (todos sus restaurantes) | ✔ | ◐ solo su turno | — | ◐ solo lo suyo | — |
| Ver informe por mesero | ✔ | ✔ | — | — | ◐ solo el suyo | — |
| Exportar datos | ✔ | ✔ | — | — | — | — |
| Ver clientes y sus datos | ✔ | ✔ | ◐ lo necesario | ◐ lo necesario | — | — |
| Ver auditoría | ✔ | ✔ | — | — | — | — |

### Inventario, compras, propinas (fases posteriores)

| Permiso | Admin empresa | Admin restaurante | Cajero | Enc. externos | Mesero | Cocina / bar |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| Registrar compras y recibir mercancía | ✔ | ✔ | ◐ compra rápida | — | — | ◐ recepción |
| Ajustar inventario | ✔ | ✔ | — | — | — | — |
| Gestionar proveedores | ✔ | ✔ | — | — | — | — |
| Liquidar propinas | ✔ | ✔ | — | — | — | — |
| Ver su propia liquidación | — | — | ✔ | ✔ | ✔ | ✔ |

> **[POR CONFIRMAR]** Esta matriz es una **propuesta inicial**. Debe validarse con restaurantes reales: en negocios pequeños una misma persona suele cumplir varios roles (dueño que cobra y atiende), lo que sugiere permitir **asignar varios roles** a un usuario.

## 3. Permisos que requieren cuidado especial

Los siguientes se conceden de forma **explícita** y se auditan siempre:

- Cancelar ítems en proceso o posteriores.
- Aplicar descuentos manuales.
- Anular cuentas pagadas.
- Reabrir comandas despachadas.
- Revocar QR.
- Exportar datos personales de clientes.
- Reimprimir documentos.

## 4. Roles y alcance

| Rol | Alcance |
|---|---|
| Admin empresa | Todos los restaurantes de su empresa |
| Admin restaurante | Restaurantes asignados |
| Cajero, enc. externos, cocina | Restaurante asignado (cocina, además, su punto de producción) |
| Mesero | Restaurante y zonas asignados |
| Superadmin de plataforma | Todas las empresas, solo en modo soporte auditado (`06`) |

## 5. Reglas

- **RN-PER-01 y RN-PER-02:** ver `36`.
- **RN-PER-03.** Un usuario puede tener varios roles; los permisos son la unión de ellos.
- **RN-PER-04.** Un permiso solo es efectivo si el módulo correspondiente está contratado.
- **RN-PER-05.** Cambiar los permisos de un rol aplica de inmediato a las sesiones activas.
- **RN-PER-06.** Todo cambio de rol o permiso se audita.
- **RN-PER-07.** Ningún rol puede concederse permisos a sí mismo.

## 6. Preguntas abiertas

- ¿Quién puede crear al primer administrador de un restaurante? (Superadmin de plataforma.)
- ¿Cuándo se habilitan roles personalizados? (Fase 2.)
- ¿Un mesero puede cobrar en la mesa? Cambia varias filas de la matriz.
