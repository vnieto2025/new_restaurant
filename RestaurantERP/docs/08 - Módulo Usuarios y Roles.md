# 08 - Módulo Usuarios y Roles

**Estado:** Propuesto

Este documento define **quiénes son los actores** y cómo se identifican. La **matriz de permisos** (qué puede hacer cada rol) está en `29 - Usuarios y Permisos`.

## 1. Roles del sistema

| Rol | Descripción | Aplicación principal |
|---|---|---|
| **Superadministrador de plataforma** | Personal del proveedor del software | Consola de plataforma |
| **Administrador de empresa** | Dueño o gerente general; ve todos sus restaurantes | Administración de empresa |
| **Administrador de restaurante** | Configura y supervisa un local | Administración de restaurante |
| **Cajero** | Cobra, abre y cierra turnos de caja | Caja |
| **Encargado de pedidos externos** | Registra órdenes de mostrador, WhatsApp, domicilio | Caja / mostrador |
| **Mesero** | Atiende mesas de su zona | Tablet de zona |
| **Cocina / bar** | Prepara y despacha comandas | KDS |
| **Domiciliario** | Entrega órdenes a domicilio | Vista de entregas (fase 2) |
| **Contador / auditor (lectura)** | Consulta informes y exporta, sin operar | Administración, solo lectura (fase 2) |

El **cliente final** no es un usuario con rol: es una persona que usa la carta digital y puede estar registrada como cliente (`25`).

## 2. Identificación y acceso

| Quién | Cómo entra | Comentario |
|---|---|---|
| Administradores, cajero, encargados | Correo o usuario + contraseña | Con recuperación de contraseña |
| **Mesero en tablet compartida** | **PIN corto** sobre una tablet de zona ya autorizada | Cada acción queda atribuida a su mesero (clave para el informe diario) |
| **Cocina / bar** | Dispositivo **emparejado** a un punto de producción | Evita teclear contraseñas en pleno servicio (`18`) |
| Domiciliario | Código de domiciliario (y acceso móvil en fase 2) | Se identifica para liquidación |

### Tablet compartida con varios meseros

- La tablet se autoriza una vez a una **zona** (dispositivo de zona).
- Cada mesero se **identifica con su PIN** para operar; el cambio de mesero es rápido.
- Toda orden y acción queda ligada al mesero que se identificó, no a la tablet.
- Cierre automático de identificación por inactividad.

## 3. Datos de un usuario

Nombre, documento (opcional), correo o usuario, rol, restaurantes asignados, zonas asignadas (meseros), estado (`activo`, `inactivo`), fecha de ingreso, último acceso, PIN (guardado con hash, nunca en claro).

## 4. Asignación a restaurantes y zonas

- Un usuario puede tener acceso a **uno o varios restaurantes** de su empresa.
- Un mesero se asigna a **una o varias zonas** (`08A`).
- Un cambio de asignación aplica de inmediato y queda auditado.

## 5. Ciclo de vida

1. **Creación** por un administrador (no hay autorregistro de personal).
2. **Activación**: primer acceso, cambio de contraseña o PIN.
3. **Desactivación**: el usuario deja de acceder; su historial **se conserva** (RG-11).
4. Nunca se elimina un usuario con historial de órdenes, pagos o turnos.

## 6. Reglas

- **RN-USR-01.** Un usuario pertenece a una sola empresa (`RN-EMP-03`).
- **RN-USR-02.** Toda acción operativa se atribuye a una persona identificada, nunca a un usuario genérico compartido.
- **RN-USR-03.** El PIN es de uso por dispositivo autorizado; no sirve para acceder desde fuera.
- **RN-USR-04.** Debe haber siempre al menos un administrador de restaurante activo.
- **RN-USR-05.** Un usuario desactivado cierra sus sesiones activas al instante.
- **RN-USR-06.** Los intentos fallidos de acceso se limitan y se auditan.

## 7. Preguntas abiertas

- ¿Se pide doble factor de autenticación a los administradores? (Recomiendo ofrecerlo en fase 2.)
- ¿Roles personalizados por el cliente? (Recomiendo roles fijos en el MVP, con permisos granulares por debajo; ver `29`.)
- ¿Un mesero puede trabajar en dos restaurantes de la misma empresa el mismo día?
