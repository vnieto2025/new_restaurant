# 38 - Roadmap

**Estado:** Propuesto

> Este roadmap **no incluye estimaciones de tiempo**. Con un equipo pequeño, una estimación honesta solo es posible después del **primer corte vertical** (fase 0), que revela la velocidad real de desarrollo y los problemas técnicos (impresión, tiempo real, tablets).

## 1. Definición del MVP

**Pregunta que responde:** ¿cuál es lo mínimo que un restaurante pequeño pagaría por usar?

### Dentro del MVP

| Área | Alcance |
|---|---|
| Plataforma | Empresas, restaurantes, contrato con módulos (`02A`) |
| Estructura | Zonas, mesas, QR por mesa descargable, mesa externa |
| Catálogo | Productos, categorías, modificadores simples, carta por zona, producto agotado |
| Órdenes | Tablet de mesero, QR de mesa, mostrador (mesa externa) |
| Cocina | Pantalla con tarjetas, pestañas En proceso y Listos, colores de estado, impresión de tirilla |
| Caja | Apertura y cierre de turno, cobro con medios simples (efectivo, tarjeta externa, transferencia), tirilla de cuenta |
| Meseros | Usuario por mesero, informe diario por mesero |
| Reportes | Ventas del día y por periodo, comparativo básico, productos más vendidos, por mesero y por zona |
| Seguridad | Roles básicos, auditoría de anulaciones, QR firmado, aislamiento por empresa |

### Fuera del MVP (y por qué)

| Función | Motivo |
|---|---|
| Facturación electrónica | Complejidad legal; necesita proveedor tecnológico. Entra en fase 2 |
| Pagos en línea | Requiere pasarela, conciliación y manejo de errores de pago |
| Orden por WhatsApp automatizada y notificaciones | Costos y reglas de la API oficial; en el MVP la orden se captura manualmente |
| Domicilios (zonas de envío, domiciliarios) | Depende de pedidos externos estables |
| Integración con Rappi / Uber Eats | Requiere acuerdos con las plataformas |
| Inventario y recetas | Valioso pero separable; entra en fase 2 |
| Propinas, liquidaciones y nómina | Dependen de caja y turnos estables |
| Cupones y fidelización | Mejora comercial, no esencial |
| Reservas, calificaciones | Opcionales |
| Modo offline completo | Se diseña en `33A`; en MVP basta con aviso de conexión |

> **Nota:** si tu primer cliente real necesita facturación electrónica obligatoria desde el día uno, el MVP debe incluirla o debe convivir con su sistema de facturación actual. **Esto es una de las primeras preguntas para los restaurantes que entrevistes.** `[POR CONFIRMAR]`

## 2. Fases

### Fase 0: validación y corte vertical

**Objetivo:** probar la parte más riesgosa con código real y con restaurantes reales.

- Entrevistas con 2 o 3 negocios del público objetivo.
- Corte vertical: QR de mesa → carta → orden → pantalla de cocina → "en proceso" → "listo".
- Multi-tenencia mínima (empresa → restaurante) con aislamiento probado.
- Prototipo de impresión con impresoras reales.
- Decisiones ADR-004 y ADR-005 con evidencia.
- **Salida:** estimación realista de las siguientes fases y lista corregida del MVP.

### Fase 1: MVP operativo

**Objetivo:** un restaurante puede operar un día completo con el sistema.

- Todo lo "dentro del MVP" de la sección 1.
- Piloto con uno o dos negocios reales, acompañados de cerca.
- **Salida:** informe de uso del piloto, lista de problemas, decisión de continuar.

### Fase 2: versión comercial

**Objetivo:** producto vendible por módulos.

- Facturación electrónica con proveedor tecnológico.
- Inventario, recetas, compras y proveedores.
- Pedidos externos completos y domicilios (zonas de envío, domiciliarios).
- Notificaciones por WhatsApp.
- Pagos en línea.
- Propinas y liquidaciones.
- Cupones.
- Licenciamiento y planes funcionando (`42`).

### Fase 3: escalamiento

**Objetivo:** crecer y diferenciarse.

- Integraciones con plataformas de domicilio.
- Fidelización con puntos.
- Reservas.
- Multi-sucursal avanzado y comparativos entre locales.
- Exportación a software contable.
- Evaluar nómina (integración o exportación).

## 3. Cómo se escriben los documentos (relación con las fases)

| Cuándo | Documentos |
|---|---|
| **Ya (primer borrador de los 61 documentos)** | Todos los documentos de `00` a `42` tienen un primer borrador |
| Antes de la fase 0 | **Revisar y confirmar** `10A`, `15` a `19` y `35`/`36` del flujo del corte vertical; completar los `[POR CONFIRMAR]` con las entrevistas |
| Antes de la fase 1 | Revisar `06` a `13`, `15A`, `20`, `08A`, `29`, `32`, `32A`, `33`, `33A`, `34`, `39`, `40` y ampliar `35` y `36` |
| Antes de la fase 2 | Revisar con contador y abogado `14`, `21`, `21A`, `20A`, `22` a `25A`, `26`, `26A`, `15B`, `31B`, `41`, `42` |
| Antes de la fase 3 | Revisar `31A`, `26B` y reglas con las plataformas |

> **Aviso:** tener un borrador de todo **no significa** que todo esté decidido. Los documentos de fases posteriores son **hipótesis**; deben releerse y corregirse con lo que se aprenda en cada fase antes de construir.

## 4. Criterios para pasar de fase

| Paso | Criterio |
|---|---|
| Fase 0 → 1 | El corte vertical funciona con impresora real y con al menos 2 tablets; el aislamiento entre empresas está probado; los restaurantes entrevistados confirman que el MVP les sirve |
| Fase 1 → 2 | Al menos un restaurante operó varias semanas con el sistema y lo seguiría usando; sin pérdida de órdenes en el piloto |
| Fase 2 → 3 | Hay clientes que pagan por módulos; el licenciamiento funciona; la operación (respaldos, soporte) es estable |

## 5. Riesgos que pueden mover el roadmap

| Riesgo | Efecto | Cómo se detecta |
|---|---|---|
| La impresión resulta más difícil de lo esperado | Retrasa el MVP | Fase 0 |
| Los restaurantes exigen facturación electrónica desde el inicio | El MVP crece | Entrevistas |
| WebSockets inestables en las tablets reales | Cambia ADR-004 | Fase 0 |
| Poco tiempo disponible para desarrollar | Todo se alarga | Velocidad medida en fase 0 |
| Cambios regulatorios | Retrasa facturación y propinas | Seguimiento con contador |

## 6. Preguntas para las entrevistas con restaurantes

1. ¿Cómo toman hoy los pedidos? ¿Qué se pierde o se equivoca más?
2. ¿Qué impresora y qué dispositivos tienen? ¿Tienen internet estable?
3. ¿Facturan electrónicamente hoy? ¿Con qué software?
4. ¿Qué porcentaje de ventas es mesa, para llevar, WhatsApp, domicilio y plataformas?
5. ¿Cómo reparten las propinas y cómo pagan a los domiciliarios?
6. ¿Qué reporte miran cada día? ¿Cuál les gustaría tener?
7. ¿Cuánto pagan hoy por software y cuánto pagarían por esto?
8. ¿Qué haría que dejaran de usar un sistema nuevo a las dos semanas?
