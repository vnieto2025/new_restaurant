# 42 - Modelo Comercial y Planes

**Estado:** Borrador; paquetes, cobro manual del servicio y estado de cuenta implementados en la fase 2 (ADR-039). **Todo lo de este documento son hipótesis a validar con clientes reales.** No incluye cifras de precios: dependen de tu mercado, tus costos y lo que paguen tus primeros clientes.

## 1. Qué se vende

Un servicio **por suscripción**, con módulos activables por contrato (`02A`). El cliente paga por **restaurante** y por **módulos**, no por instalación ni por licencia perpetua.

## 2. Paquetes (hipótesis)

| Paquete | Módulos | Para quién |
|---|---|---|
| **Pedidos** | `base` + `pedidos` | Quien ya factura y lleva caja con otro sistema |
| **Gestión** | `base` + `caja` + `inventario` | Panaderías, tiendas de comida, negocios de mostrador |
| **Completo** | Todo lo disponible en la fecha | Restaurantes que quieren operar de punta a punta |
| **Complementos** | Domicilios, pagos en línea, fidelización, reportes avanzados, integraciones | Venta adicional según necesidad |

## 3. Modelos de cobro

| Modelo | Cómo funciona | Pros | Contras |
|---|---|---|---|
| **Cuota fija por restaurante y módulo** | Pago mensual | Predecible para ambos | Un restaurante pequeño puede sentirlo caro |
| **Por usuario o por dispositivo** | Pago por cada tablet o usuario | Escala con el uso | Desincentiva crecer o desalentar usuarios |
| **Por volumen** (órdenes o ventas) | Porcentaje o tarifa por orden | Alineado con el éxito del cliente | Menos predecible; molesta cuando crece; complica la facturación |
| **Híbrido** | Cuota base + variable por servicios externos con costo real (mensajes, facturas electrónicas) | Cubre costos variables | Más difícil de explicar |
| **Prueba gratuita limitada** | Plazo corto o límite de uso | Reduce fricción | Costo de soporte sin ingreso |

**Recomendación inicial:** **cuota fija por restaurante y por módulo**, más **cobro aparte de costos variables de terceros** (mensajes de WhatsApp por la API oficial, facturas electrónicas) cuando existan. Es simple de explicar y de vender. `[POR CONFIRMAR]` con los primeros clientes.

## 4. Cómo estimar precios (sin inventar cifras)

Un precio se construye de tres piezas:

```
Piso: costo por restaurante activo (infraestructura + servicios externos + soporte)
Valor: cuánto ahorra o gana el cliente (menos errores, más ventas, tiempo)
Referencia: qué pagan por alternativas (software POS, carta QR, hojas de cálculo)
```

- Calcular el **costo por restaurante activo** (`40`): cómputo, base de datos, respaldos, servicios por uso y **tiempo de soporte**.
- Investigar precios de **alternativas del mercado local** y de herramientas parciales (carta QR, POS, facturación).
- **Preguntar a los restaurantes** cuánto pagan hoy y cuánto pagarían por esto (`38`, sección 6).
- Fijar **un precio de lanzamiento** con los primeros clientes del piloto, explícitamente temporal y con condiciones.

### Pregunta de viabilidad

> ¿A cuántos restaurantes con qué precio necesitas llegar para que el negocio cubra costos y tu tiempo? Esa cifra se calcula con los **costos reales** y condiciona si un público de negocios muy pequeños es viable. Hacer este cálculo **antes** de invertir meses de desarrollo.

## 5. Ciclo de vida comercial

| Etapa | Descripción |
|---|---|
| **Piloto** | Primeros clientes con condiciones especiales, acompañamiento y retroalimentación |
| **Prueba** | Periodo limitado antes de contratar |
| **Contrato activo** | Suscripción mensual (o anual con descuento) |
| **Cambio de módulos** | Activar o desactivar con efecto desde el siguiente periodo |
| **Mora** | Aviso, periodo de gracia, suspensión **sin pérdida de datos** (`02A`) |
| **Cancelación** | Exportación de datos y plazo de conservación (`41`) |

## 6. Cobro del propio SaaS (plataforma)

El producto necesita **cobrar a sus clientes**, función que normalmente se descuida:

| Capacidad | Descripción |
|---|---|
| **Cobro recurrente** | Medios de pago para suscripciones; evaluar pasarela con soporte de recurrencia |
| **Facturación del servicio** | Emisión de facturas por el proveedor del software; **debe revisarlo un contador** |
| **Estado de la cuenta** | Pagos, vencimientos, historial visible para el cliente |
| **Avisos de mora** | Automáticos y con tono cuidadoso |
| **Cambios de plan** | Proporcionales o desde el siguiente periodo, según política |
| **Descuentos y cupones comerciales** | Para pilotos y campañas |

En el MVP puede ser **manual** (cobro por transferencia y factura emitida a mano) si hay pocos clientes; automatizarlo antes de tener volumen es un error de prioridades.

## 7. Estructura legal y contractual

Documentos a preparar con un abogado (`32A`, `21A`):

- **Términos y condiciones del servicio** y política de uso.
- **Contrato de servicio** con alcance, precios, soporte, disponibilidad y limitación de responsabilidad.
- **Contrato de encargo de datos personales.**
- **Acuerdo de nivel de servicio (SLA)** realista.
- **Política de privacidad** del sitio y de la carta digital.
- Aclaración de **responsabilidades fiscales** (del restaurante) y de los servicios de terceros.

## 8. Qué pagarían y qué no

**Hipótesis** a verificar en entrevistas:

| Pagarían por... | Probablemente no pagarían por... |
|---|---|
| Que las órdenes no se pierdan | Estadísticas avanzadas al inicio |
| Informe diario claro | Integraciones que no usan |
| Carta digital por QR | Programa de puntos |
| Cierre de caja sin hojas de cálculo | Funciones que requieren mucha carga de datos (recetas) |
| Avisos por WhatsApp a clientes | Módulos que no entienden |

## 9. Riesgos comerciales

| Riesgo | Mitigación |
|---|---|
| Público demasiado pequeño para sostener el precio | Calcular viabilidad temprano; segmentar por tipo de negocio |
| Soporte consume todo el tiempo | Onboarding estandarizado, guías, límite de clientes por mes (`41`) |
| Costos variables de terceros se comen el margen | Cobrar aparte; medir por cliente |
| Competencia con productos muy conocidos | Diferenciador claro y foco en un segmento (`00`) |
| Clientes piden funciones a medida | Política de **no desarrollar a medida** al inicio |
| Mora y cancelaciones | Contratos claros y cobro disciplinado |

## 10. Qué validar antes de fijar el plan

1. Qué paquetes entienden y quieren los primeros 5 a 10 restaurantes.
2. Cuánto pagan hoy por soluciones parciales.
3. Si prefieren cuota fija o por volumen.
4. Costo real de operar y soportar a cada uno en el piloto.
5. Si el segmento objetivo sostiene el precio mínimo viable.

## 11. Preguntas abiertas

- ¿Se vende directamente o mediante aliados (contadores, distribuidores de impresoras, proveedores de insumos)?
- ¿Hay descuento por varios restaurantes de la misma empresa?
- ¿Se ofrece plan anual con descuento?
- ¿Se cobra aparte la capacitación y la instalación en sitio?
