# 10 - Módulo Mesas

**Estado:** Propuesto

Una **mesa** es un puesto físico dentro de una zona, con su propio QR. Existe además una **mesa externa** que representa a quien no se sienta. Los QR se detallan en `10A`.

## 1. Datos de una mesa

| Campo | Descripción |
|---|---|
| Número o nombre | Visible para mesero y cliente ("Mesa 5", "Barra 2") |
| Zona | Una sola (`RN-MES-01`) |
| Capacidad | Opcional; útil para reservas futuras |
| Tipo | `normal` o `externa` |
| Estado de configuración | `activa`, `inactiva` |
| QR | Token actual y fecha de generación (`10A`) |
| Posición en el plano | Opcional (fase 2) |

## 2. Estados operativos de una mesa

Se derivan de su **sesión de mesa**:

| Estado | Significado |
|---|---|
| **Libre** | Sin sesión abierta |
| **Ocupada** | Sesión abierta con o sin órdenes |
| **Con orden en curso** | Hay ítems sin entregar |
| **Cuenta solicitada** | El cliente pidió la cuenta |
| **Bloqueada** | Fuera de servicio temporal (no acepta órdenes ni QR) |

La tablet muestra cada mesa con su estado y, si hay ítems pendientes, el indicador del estado más urgente de sus ítems (`16`).

## 3. Sesión de mesa

- Se abre cuando el mesero abre la mesa o cuando un cliente pide por QR (según el modo, `10A`).
- Agrupa las órdenes de la mesa hasta que se cierra la cuenta.
- Se cierra al pagar; una nueva orden crea una nueva sesión.
- Tiene responsable (mesero) y hora de apertura y cierre.

## 4. Operaciones sobre mesas

| Operación | Descripción | Permiso |
|---|---|---|
| **Abrir mesa** | Crea sesión y asigna responsable | Mesero |
| **Trasladar mesa** | Mueve la sesión y sus órdenes a otra mesa | Mesero con permiso |
| **Unir mesas** | Varias mesas comparten sesión y cuenta (grupos grandes) | Mesero con permiso |
| **Dividir cuenta** | Reparte lo consumido entre varios pagos (en `20`) | Mesero / cajero |
| **Bloquear / desbloquear** | Pone la mesa fuera de servicio | Administrador |
| **Revocar QR y generar otro** | Seguridad (`10A`) | Administrador |
| **Cambiar de zona** | Solo sin sesión abierta | Administrador |

## 5. Mesa externa

Mesa estándar por restaurante para quienes no se sientan: para llevar, mostrador, WhatsApp, domicilio, plataformas.

- Se crea automáticamente con el restaurante (`07`).
- **No pertenece a una zona física**, pero se asocia a una zona "lógica" de mostrador para efectos de carta y producción.
- Admite **varias sesiones simultáneas** (muchos clientes a la vez), a diferencia de una mesa normal.
- Cada orden externa se identifica por **número de orden y nombre o teléfono del cliente**, no por mesa.

> **Decisión de modelado:** como la mesa externa admite muchas sesiones simultáneas, **cada orden externa abre su propia sesión**. `[POR CONFIRMAR]`

## 6. Creación y administración masiva

- Crear mesas **en lote** ("crear mesas 1 a 10 en la zona Corrientes").
- Descargar los **QR en PDF** por mesa o por zona (`10A`).
- Cambiar numeración o nombres sin perder historial.

## 7. Reglas

- **RN-MES-01 a RN-MES-05:** ver `36`.
- **RN-MES-06.** Los nombres de mesa son únicos dentro de una zona.
- **RN-MES-07.** Una mesa bloqueada rechaza órdenes por cualquier canal.
- **RN-MES-08.** Una mesa con historial no se elimina; se inactiva (RG-11).
- **RN-MES-09.** Unir o trasladar mesas se audita.

## 8. Preguntas abiertas

- ¿Un cliente que escanea el QR de una mesa libre abre sesión solo o espera al mesero? Depende del modo de la zona (`10A`).
- ¿Se necesita plano visual del local en el MVP? (Recomiendo no.)
- ¿Cómo se gestionan reservas sobre mesas? (Fuera del MVP.)
