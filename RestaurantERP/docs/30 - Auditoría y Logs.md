# 30 - Auditoría y Logs

**Estado:** Propuesto

Distingue dos cosas que suelen confundirse:

| Concepto | Para qué sirve | Quién lo consulta |
|---|---|---|
| **Auditoría** | Responder "**quién hizo qué y cuándo**" sobre datos del negocio | Administradores, soporte, contadores |
| **Logs técnicos** | Diagnosticar fallos y rendimiento del sistema | Equipo técnico |

## 1. Auditoría de negocio

### Qué se audita siempre (RG-14)

| Área | Eventos |
|---|---|
| **Órdenes** | Cancelaciones, ediciones tras enviar, reaperturas, cambios de mesa, rechazos de QR |
| **Caja** | Apertura y cierre de turno, descuentos, anulaciones, devoluciones, diferencias de arqueo, gastos y retiros |
| **Productos** | Cambios de precio, agotados, cambios de impuesto |
| **Usuarios** | Altas, bajas, cambios de rol o permisos, restablecimiento de contraseña |
| **Seguridad** | Inicios de sesión (éxito y fallo), bloqueos, revocación de QR, accesos de soporte |
| **Datos personales** | Consultas, exportaciones y eliminaciones de datos de clientes |
| **Configuración** | Impuestos, jornada, modos de QR, medios de pago |
| **Inventario** | Ajustes, mermas, conteos |
| **Propinas y liquidaciones** | Ajustes manuales, aprobaciones |
| **Impresión** | Reimpresiones |
| **Integraciones** | Cambios de credenciales y de proveedor |

### Estructura de un registro

| Campo | Descripción |
|---|---|
| Momento | Fecha y hora UTC (RG-08) |
| Actor | Usuario, o sistema/integración |
| Dispositivo | Tablet, navegador o integración |
| Empresa y restaurante | Contexto |
| Acción | Código del evento (`orden.cancelar`) |
| Entidad | Tipo e ID afectado |
| Antes y después | Valores relevantes |
| Motivo | Cuando el evento lo exige |
| Origen | IP o identificador de dispositivo |

## 2. Propiedades exigidas

- **Inmutable:** nadie edita ni borra registros de auditoría, ni siquiera un administrador.
- **Completa:** no depende de que la interfaz "se acuerde" de registrarla; se genera en el backend.
- **Consultable:** filtros por usuario, fecha, acción, entidad.
- **Atada a la empresa:** aislada por tenant (RG-16).
- **Con retención definida:** se conserva el tiempo acordado (verificar con asesor), aunque el contrato termine.

## 3. Consulta

El administrador puede responder, entre otras:

- ¿Quién canceló esta orden y por qué?
- ¿Quién cambió el precio de este producto?
- ¿Quién anuló cuentas esta semana?
- ¿Qué hizo este usuario ayer?
- ¿Quién consultó los datos de este cliente?

## 4. Alertas derivadas

Con umbrales configurables:

- Muchas cancelaciones o descuentos de un mismo usuario en una jornada.
- Diferencias de arqueo repetidas.
- Intentos de acceso fallidos.
- Reimpresiones frecuentes.

## 5. Logs técnicos

| Aspecto | Criterio |
|---|---|
| Formato | Estructurado (JSON), con identificador de petición y de empresa |
| Niveles | Debug, info, advertencia, error, crítico |
| **Datos personales** | **No se registran** contraseñas, tokens, datos de tarjeta ni datos de clientes en claro |
| Retención | Corta (por ejemplo semanas) para logs técnicos |
| Trazabilidad | Una petición se rastrea de punta a punta |
| Errores | Se agrupan y alertan al equipo técnico (`40`) |

## 6. Reglas

- **RN-AUD-01.** Los eventos sensibles de la lista se auditan sin excepción y sin depender de la interfaz.
- **RN-AUD-02.** Un registro de auditoría no se modifica ni se elimina.
- **RN-AUD-03.** Los accesos de soporte a una empresa se registran con motivo y son visibles para el cliente.
- **RN-AUD-04.** Los logs técnicos no contienen secretos ni datos personales.
- **RN-AUD-05.** La consulta de auditoría tiene su propio permiso y también se audita.

## 7. Preguntas abiertas

- ¿Cuánto tiempo se retiene la auditoría? (Definir con asesor legal y contador.)
- ¿Se permite al cliente exportar su auditoría?
- ¿Qué herramienta de logs y errores se usa? (ADR pendiente, `40`.)
