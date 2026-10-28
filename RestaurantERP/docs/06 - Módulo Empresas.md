# 06 - Módulo Empresas

**Estado:** Propuesto

La **empresa** es el cliente del software y la frontera de aislamiento de datos (tenant). Ver `02A` para la lógica de multi-tenencia y licenciamiento.

## 1. Qué es una empresa

La persona jurídica o natural dueña de uno o varios restaurantes. Un restaurante independiente también es una empresa con un solo restaurante; esa jerarquía es invisible para el usuario.

## 2. Datos de la empresa

| Campo | Descripción |
|---|---|
| Nombre comercial | Como la conocen sus clientes |
| Razón social y documento fiscal | Para facturar el servicio y, si aplica, datos fiscales por defecto |
| País, moneda y zona horaria por defecto | Heredados por sus restaurantes (RG-04, RG-08) |
| Contacto principal | Nombre, correo, teléfono |
| Estado | `prueba`, `activa`, `suspendida`, `cancelada` |
| Fecha de alta | Auditoría |
| Plan comercial | Referencia a `42` |

## 3. Quién gestiona qué

| Actor | Puede |
|---|---|
| **Superadministrador de plataforma** (personal del proveedor) | Crear y suspender empresas, ver contratos, dar soporte |
| **Administrador de empresa** | Ver y administrar sus restaurantes, usuarios, consolidados |
| Otros roles | No ven datos de la empresa más allá de su restaurante |

> **Acceso de soporte:** el superadministrador puede entrar en modo soporte a una empresa para ayudar, pero cada acceso queda **auditado**, con motivo y con aviso al cliente. `[POR CONFIRMAR]`

## 4. Alta de una empresa

**MVP:** el alta la hace el proveedor del software (manual). Autoservicio (el dueño se registra solo) queda para la fase 3.

Pasos mínimos: crear empresa → crear administrador → crear primer restaurante con su contrato (módulos) → entregar credenciales y guía de onboarding (`41`).

## 5. Vista consolidada

El administrador de empresa ve, **solo de los módulos contratados** en cada restaurante: ventas por restaurante, comparativos y alertas generales (`27`). No ve datos de módulos no contratados.

## 6. Ciclo de vida

| Estado | Efecto |
|---|---|
| Prueba | Acceso completo, vigencia limitada |
| Activa | Operación normal |
| Suspendida | Solo lectura; no se crean órdenes ni cobros (ver periodo de gracia en `02A`) |
| Cancelada | Solo exportación de datos durante un plazo |

## 7. Reglas

- **RN-EMP-01.** Toda empresa tiene al menos un administrador activo.
- **RN-EMP-02.** Una empresa no se elimina; se cancela y sus datos se conservan o anonimizan según política (`32A`).
- **RN-EMP-03.** Un usuario pertenece a una sola empresa en el MVP (`02A`).
- **RN-EMP-04.** Cambiar el estado de una empresa genera registro de auditoría.

## 8. Preguntas abiertas

- ¿Qué plazo de conservación se ofrece tras cancelar?
- ¿Se permite transferir un restaurante de una empresa a otra? (Recomiendo no en el MVP.)
