# 39 - Pruebas y Calidad

**Estado:** Propuesto

Cómo se asegura que el sistema funciona **cuando importa**: en hora pico, con dinero de por medio y con varios clientes compartiendo infraestructura. Con un equipo pequeño no se puede probar todo; se prioriza lo que más daño haría si fallara.

## 1. Qué es lo más riesgoso (y se prueba primero)

| Prioridad | Riesgo | Por qué |
|---|---|---|
| 1 | **Aislamiento entre empresas** | Una fuga destruye la confianza (`02A`, `32`) |
| 2 | **Cálculos de dinero** (precios, impuestos, descuentos, propinas, cierres) | Errores costosos y difíciles de explicar |
| 3 | **Estados y flujo de órdenes** | Órdenes perdidas, duplicadas o en estado imposible (`16`) |
| 4 | **Concurrencia** | Dos meseros sobre la misma mesa, QR y mesero a la vez |
| 5 | **Permisos y módulos contratados** | Acciones prohibidas o funciones no pagadas (`29`, `02A`) |
| 6 | **Resiliencia** | Reconexiones, reintentos, caídas (`33A`) |
| 7 | **QR y rutas públicas** | Abuso y órdenes falsas (`10A`) |

## 2. Niveles de prueba

| Nivel | Qué verifica | Herramientas orientativas |
|---|---|---|
| **Unitarias** | Reglas de negocio puras: cálculo de totales, máquina de estados, reparto de propinas, cupones | pytest, Vitest |
| **De integración** | Módulos con base de datos real (PostgreSQL), RLS, transacciones | pytest con base de datos de prueba |
| **De API (contrato)** | Endpoints, errores, permisos, módulos contratados | pytest + cliente HTTP; esquema OpenAPI |
| **De extremo a extremo (E2E)** | Flujos completos desde la interfaz: orden por QR → cocina → entrega → cobro | Playwright o similar |
| **De carga** | Comportamiento con muchas órdenes y conexiones simultáneas | k6, Locust u otra |
| **De seguridad** | Vulnerabilidades comunes, dependencias | Análisis automático + revisión |
| **Manual exploratorio con personal real** | Usabilidad y casos raros | Pilotos (`38`) |
| **En dispositivos reales** | Tablets, pantallas, impresoras, navegadores móviles | Laboratorio de dispositivos |

Pirámide sugerida: **muchas** unitarias y de integración, **pocas pero críticas** E2E.

## 3. Pruebas obligatorias específicas

### 3.1 Aislamiento entre empresas (RLS)

- Con dos empresas de prueba, **ningún endpoint** debe devolver datos de la otra, con ningún rol.
- Pruebas automáticas que intentan acceder por ID de otra empresa y deben fallar.
- Pruebas que verifican que **toda tabla de negocio** tiene `empresa_id` y política RLS (un chequeo automático que falle si se agrega una tabla sin ella).

### 3.2 Máquina de estados

- Cada transición permitida funciona; **cada transición no permitida es rechazada** (`16`).
- El estado derivado de la orden se prueba con **muchas combinaciones** de ítems (pruebas basadas en propiedades).
- Reabrir, cancelar y reasignar quedan auditados.

### 3.3 Dinero

- Totales con impuestos, descuentos, cupones, domicilio y propina, contra casos conocidos.
- **Redondeo**: reglas definidas y probadas (RG-03).
- División de cuentas: la suma de partes **siempre** igual al total.
- Cierres de caja: diferencias calculadas correctamente.
- Reportes cuadran con caja (`RN-REP-01`).

### 3.4 Idempotencia y concurrencia

- Enviar la misma orden dos veces con la misma clave: **una sola orden**.
- Dos meseros agregando ítems a la vez: ambos aparecen, sin pérdida.
- Dos aprobaciones simultáneas de una orden de QR: solo una vale.
- Webhooks de pago repetidos o desordenados: **un solo efecto** (`20A`).

### 3.5 Permisos y módulos

- Matriz de `29` verificada automáticamente rol por rol.
- Un módulo no contratado responde `modulo_no_contratado` (`RN-API-03`).

### 3.6 QR

- Token revocado deja de funcionar al instante.
- Límites de uso se aplican.
- No es posible cambiar mesa, zona ni restaurante manipulando la URL.

### 3.7 Resiliencia

- Cortar la conexión de la tablet a mitad de un envío.
- Reconectar la cocina y verificar que se recupera el estado completo.
- Caída de servicios externos: la venta continúa (`33A`).

## 4. Datos de prueba

- **Nunca datos reales** de clientes en pruebas (`RN-SEG-04`).
- Conjuntos de datos reproducibles: dos empresas, varios restaurantes, zonas, mesas, productos con modificadores, usuarios de cada rol.
- Un **generador de datos de carga** para pruebas de volumen.
- Casos reales anonimizados del piloto cuando se tengan.

## 5. Integración continua (CI)

En cada cambio, automáticamente:

1. Formato y análisis estático del código.
2. Pruebas unitarias y de integración.
3. Pruebas de aislamiento y de permisos.
4. Análisis de dependencias y de secretos.
5. Construcción de las aplicaciones.
6. E2E críticos (en un conjunto reducido o en cada versión).

Un cambio que rompe las pruebas **no se despliega**.

## 6. Definición de "terminado" para una funcionalidad

- Reglas de negocio documentadas (`36`) y con pruebas.
- Permisos definidos (`29`) y probados.
- Auditoría de eventos sensibles (`30`).
- Casos de error y de conexión manejados (`33A`).
- Probada en un **dispositivo real**.
- Documentación actualizada.
- Revisada por otra persona o por una revisión propia con lista de verificación.

## 7. Pruebas de aceptación con restaurantes

- **Guion** de una jornada simulada: abrir caja, tomar órdenes de varios canales, procesar en cocina, cobrar con pagos mixtos, cerrar turno y jornada.
- **Observación en un local real** durante el piloto (`38`).
- Registrar cada problema como caso de prueba para que **no vuelva a ocurrir**.

## 8. Calidad operativa

- Indicadores de producción: errores por hora, tiempos de respuesta, órdenes fallidas, reintentos (`40`).
- **Revisión posterior** de cada incidente: causa, corrección y prueba que lo evita.
- Revisión periódica de la **deuda técnica**.

## 9. Reglas

- **RN-QA-01.** Ninguna tabla de negocio se crea sin `empresa_id` y política de aislamiento; una prueba automática lo exige.
- **RN-QA-02.** Todo error corregido en producción genera una prueba que lo reproduce.
- **RN-QA-03.** Los cálculos de dinero tienen pruebas con casos límite y de redondeo.
- **RN-QA-04.** Ninguna versión se despliega con pruebas críticas fallando.
- **RN-QA-05.** Los datos de producción no se copian a pruebas sin anonimizar.

## 10. Preguntas abiertas

- ¿Qué tablets y navegadores forman el **conjunto mínimo de dispositivos soportados**?
- ¿Qué cobertura mínima de pruebas se exige en el código de dinero y de estados?
- ¿Quién revisa el código si el equipo es una sola persona? (Revisión propia con lista de verificación y pruebas automáticas.)
