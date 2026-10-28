# 32A - Privacidad y Cumplimiento

**Estado:** Propuesto. **Requiere revisión de un abogado.**

El sistema trata **datos personales** de clientes (nombre, teléfono, dirección, historial de compras) y del personal. Este documento resume los principios y obligaciones que conviene cumplir.

> **Aviso:** asumo Colombia como mercado inicial (`[POR CONFIRMAR]`). **No soy abogado.** Esto es una guía de diseño, no asesoría legal. Debe revisarlo un abogado especializado en protección de datos antes del lanzamiento comercial.

## 1. Marco de referencia (Colombia)

| Norma | Qué regula (a verificar) |
|---|---|
| **Ley 1581 de 2012** | Régimen general de protección de datos personales (Habeas Data) |
| **Decreto 1377 de 2013** (hoy compilado en el Decreto 1074 de 2015) | Reglamenta aspectos como autorización, políticas de tratamiento y responsabilidades |
| **Superintendencia de Industria y Comercio (SIC)** | Autoridad de protección de datos |
| **Registro Nacional de Bases de Datos (RNBD)** | Registro de bases de datos para ciertos responsables; **verificar si aplica** a tu empresa y a tus clientes |

Si hay clientes en otros países o se alojan datos fuera de Colombia, aplican además reglas de **transferencia y transmisión internacional**; verificar.

## 2. Roles en el tratamiento de datos

| Figura | Quién es | Obligaciones principales |
|---|---|---|
| **Responsable del tratamiento** | El **restaurante** o la empresa (decide para qué y cómo se usan los datos de sus clientes) | Obtener autorización, tener política de tratamiento, atender solicitudes de los titulares |
| **Encargado del tratamiento** | El **proveedor del software** (procesa los datos por cuenta del restaurante) | Tratar los datos según las instrucciones del responsable, con medidas de seguridad |

Esto implica un **contrato** (de servicio y de transmisión o encargo de datos) entre el proveedor del software y cada cliente. **Pendiente de redactar con abogado** (`42`).

## 3. Datos que trata el sistema

| Dato | De quién | Para qué |
|---|---|---|
| Nombre, teléfono, dirección | Clientes de domicilio y para recoger | Gestionar y entregar la orden, notificar |
| Historial de compras | Clientes registrados | Reconocimiento, cupones, estadísticas |
| Correo, documento | Clientes que piden factura | Facturación |
| Datos laborales operativos | Personal | Turnos, propinas, informes |
| Datos de pago | Clientes | **No se almacenan**; los trata la pasarela (RG-19) |
| Datos de dispositivo y registros de acceso | Todos | Seguridad y auditoría |

**Datos sensibles:** el sistema **no debe pedir ni almacenar** datos sensibles (salud, orientación, etc.). Las notas de alergias se limitan a información necesaria para preparar el plato y deben tratarse con cuidado (`25`).

**Menores de edad:** no se solicitan datos de menores; los cumpleaños, si se piden, solo de adultos y con consentimiento.

## 4. Principios aplicados al diseño

| Principio | Cómo se aplica |
|---|---|
| **Finalidad** | Cada dato se usa solo para lo autorizado (`RN-CLI-03`) |
| **Minimización** | Pedir solo lo necesario; en la carta por QR, **nada obligatorio** salvo domicilio |
| **Autorización previa e informada** | Aviso y aceptación antes de recolectar datos en orden externa o registro |
| **Seguridad** | Controles de `32` |
| **Acceso restringido** | Permisos por rol y auditoría de consultas (`30`) |
| **Conservación limitada** | Plazos definidos; anonimización al terminar la finalidad |
| **Transparencia** | Política de tratamiento visible para el cliente final |

## 5. Funciones que el sistema debe ofrecer

| Función | Descripción |
|---|---|
| **Aviso de tratamiento** en carta digital y formularios | Texto configurable por restaurante con enlace a su política |
| **Registro del consentimiento** | Fecha, canal, versión del texto aceptado |
| **Consentimiento separado para comunicaciones comerciales** | `RN-CLI-04` |
| **Atender solicitudes del titular** | Conocer, actualizar, rectificar, suprimir y revocar autorización (`25`) |
| **Exportación y anonimización** | De los datos de un cliente |
| **Auditoría de acceso** | Quién consultó datos personales (`30`) |
| **Eliminación al terminar el contrato** | Según política acordada con el cliente |

## 6. Incidentes

Si ocurre un incidente de seguridad que afecte datos personales, hay obligaciones de **informar** a los afectados y, según el caso, a la autoridad. El plan de respuesta (`32`) debe incluir plazos y responsables, definidos con el abogado.

## 7. Alojamiento y transferencias

- Si el servidor está **fuera de Colombia**, hay que revisar las reglas sobre **transferencia o transmisión internacional** y las garantías exigidas. Verificar al elegir el proveedor de nube (`40`).
- Los **subencargados** (pasarela, proveedor de WhatsApp, facturación electrónica, hosting) deben ser conocidos y enumerarse en el contrato.

## 8. Tareas legales previas (para el responsable del proyecto)

1. Contratar o consultar a un **abogado de protección de datos**.
2. Redactar **política de tratamiento** del proveedor y **plantilla** para los restaurantes.
3. Redactar **contrato de servicio** y **contrato de encargo de datos**.
4. Determinar si se requiere **registro en el RNBD**.
5. Revisar **términos y condiciones** y **aviso de privacidad** de la carta digital.
6. Definir plazos de **retención**.

## 9. Reglas

- **RN-PRI-01.** No se recolectan datos personales sin aviso de tratamiento visible.
- **RN-PRI-02.** El consentimiento se registra con fecha, canal y versión del texto.
- **RN-PRI-03.** Las solicitudes de acceso, rectificación o eliminación se atienden y se registran.
- **RN-PRI-04.** Los datos de un cliente nunca se comparten entre empresas.
- **RN-PRI-05.** No se almacenan datos de tarjeta ni datos sensibles.
- **RN-PRI-06.** Al terminar la relación contractual, los datos se devuelven o eliminan según el contrato, salvo los que la ley obligue a conservar.

## 10. Preguntas abiertas

- ¿Quién redacta y mantiene la política de tratamiento de cada restaurante?
- ¿Qué retención se aplica a las órdenes con datos de cliente?
- ¿Se almacenarán datos de ubicación exacta de entregas? (Recomiendo no en el MVP.)
