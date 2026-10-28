# 25 - Módulo Clientes

**Estado:** Propuesto

Los **clientes registrados** permiten reconocer compras, guardar direcciones y ofrecer cupones. El cliente es **por empresa**: la misma persona que compra en dos empresas distintas es dos registros separados (RG-16, `05`).

> Los datos de clientes son **datos personales**. Todo lo de este documento está sujeto a `32A`.

## 1. Quién es un cliente

| Tipo | Descripción |
|---|---|
| **Anónimo** | Pide por QR de mesa sin dejar datos; no se guarda |
| **Con datos mínimos** | Dejó nombre y teléfono para una orden externa |
| **Registrado** | Tiene perfil con historial, direcciones y preferencias |

## 2. Datos de un cliente registrado

| Campo | Descripción |
|---|---|
| Nombre | Obligatorio |
| **Teléfono** | Obligatorio y es el identificador principal (WhatsApp) |
| Correo | Opcional |
| Documento | Solo si se requiere para facturar |
| Direcciones | Una o varias, con indicaciones y zona de envío |
| Fecha de cumpleaños | Opcional, solo con consentimiento |
| Notas del restaurante | Preferencias, alergias informadas por el cliente |
| **Consentimientos** | Tratamiento de datos, comunicaciones comerciales: fecha y canal en que se otorgaron |
| Estado | `activo`, `inactivo`, `bloqueado` |

## 3. Cómo se crea un cliente

| Vía | Cómo |
|---|---|
| **Captura en orden externa** | El encargado ingresa teléfono; si no existe se crea con los datos mínimos |
| **Autorregistro en la carta digital** | Fase 2, al pedir domicilio |
| **Importación** | Carga de una lista existente del restaurante (con cuidado de consentimientos) |

**Reconocimiento:** al ingresar un teléfono, el sistema busca coincidencia y propone autocompletar nombre y direcciones. Dos registros con el mismo teléfono se **fusionan** con permiso.

## 4. Historial y utilidad

- Órdenes anteriores y total gastado.
- Productos favoritos.
- Última visita y frecuencia.
- Cupones usados.
- Segmentos simples: clientes frecuentes, inactivos hace X días, nuevos (fase 2).

## 5. Verificación del teléfono

Confirmar que el teléfono es del cliente (código por mensaje) previene datos falsos, pero **cuesta dinero y agrega fricción**. En el MVP no se verifica; en fase 2 se evalúa para domicilios y pagos en línea. `[POR CONFIRMAR]`

## 6. Derechos de los titulares

El cliente puede pedir conocer, actualizar, corregir o eliminar sus datos. El sistema debe permitir:

- **Exportar** los datos de un cliente.
- **Eliminar o anonimizar** un cliente conservando integridad de ventas históricas (las órdenes quedan, desligadas de los datos personales).
- Registrar la solicitud y quién la atendió.

## 7. Reglas

- **RN-CLI-01.** Un cliente pertenece a una sola empresa.
- **RN-CLI-02.** El teléfono es único dentro de la empresa.
- **RN-CLI-03.** Los datos de un cliente solo se usan para los fines autorizados (gestión de órdenes y comunicaciones consentidas).
- **RN-CLI-04.** No se envían comunicaciones comerciales sin consentimiento registrado.
- **RN-CLI-05.** Eliminar un cliente anonimiza sus datos personales y conserva las ventas.
- **RN-CLI-06.** Los accesos a datos de clientes se auditan.

## 8. Preguntas abiertas

- ¿Qué datos mínimos se piden para domicilio y cuáles son opcionales?
- ¿Se permite ingresar la fecha de cumpleaños de menores? (Recomiendo no.)
- ¿Se comparte la base de clientes entre restaurantes de una empresa? (Recomiendo sí dentro de la empresa, con consentimiento claro.)
