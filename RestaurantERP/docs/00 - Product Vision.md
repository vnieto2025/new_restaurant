# 00 - Product Vision

**Estado:** Propuesto

## 1. Problema

Los restaurantes pequeños y medianos suelen operar con una mezcla frágil de papel, WhatsApp, una caja registradora y una hoja de cálculo. Los problemas más comunes:

- Los pedidos se pierden o se entienden mal entre mesa, mesero y cocina.
- El dueño no sabe con claridad cuánto vendió, qué se vende más ni cuánto gana por plato.
- Los pedidos por WhatsApp y domicilio se anotan a mano y se cobran sin un registro ordenado.
- Las propinas y los pagos a domiciliarios se liquidan con cuentas hechas a mano.
- Los programas existentes son caros, pensados para cadenas, o cubren solo una parte (solo caja, solo carta QR).

## 2. Visión

Ser el sistema operativo del restaurante pequeño: un solo producto, por módulos, que lleve desde la orden en la mesa hasta el cierre del día, sin instalar nada y sin exigir personal técnico.

## 3. Público objetivo

**Sí:** restaurantes pequeños, pizzerías, comida rápida, bares y discotecas pequeñas, cocinas ocultas (dark kitchens), panaderías, negocios de comidas especiales; empresas con uno o pocos locales.

**No (por ahora):** grandes cadenas con cientos de sedes, franquicias con ERP corporativo, hoteles con restaurante integrado.

## 4. Propuesta de valor

1. **Todo en la web.** Sin apps de tienda; las tablets son navegadores.
2. **Orden por QR en la mesa**, más tablet de mesero, mostrador, WhatsApp y domicilio, todos alimentando la misma cocina.
3. **Pantalla de cocina clara** con estados por color y tirilla impresa.
4. **Modular:** el cliente paga solo por lo que usa (solo pedidos, solo facturación e inventario, o completo).
5. **Informes simples pero útiles** para el dueño: ventas, comparativos, desempeño por mesero, zona y canal.

## 5. Diferenciador (hipótesis a validar)

> **[POR CONFIRMAR]** Estas son hipótesis, no hechos. Deben contrastarse con entrevistas a restaurantes reales y con un análisis directo de la competencia.

- Combinar en un solo producto lo que hoy suele repartirse entre varias herramientas: carta QR, comandas, domicilios por WhatsApp, caja e inventario.
- Estar pensado desde cero para el **mercado local** (facturación, impuestos, WhatsApp, propinas, domiciliarios propios).
- Precio y complejidad acordes a un negocio pequeño.

## 6. Fuera de alcance (por ahora)

- Aplicaciones nativas en tiendas de apps.
- Nómina completa (se evaluará integrar o exportar; ver ADR-009 en `37`).
- Integraciones directas con plataformas de domicilio (Rappi, Uber Eats): fase posterior.
- Gestión de franquicias y grandes cadenas.
- Reservas y lista de espera en el MVP.

## 7. Actores principales

Dueño o administrador de empresa, administrador de restaurante, mesero, cocinero o bartender, cajero o encargado de pedidos externos, domiciliario, cliente final. Detalle en `00B` y `08`.

## 8. Cómo mediremos el éxito (hipótesis)

| Indicador | Qué mide |
|---|---|
| Restaurantes que operan al menos 2 semanas seguidas con el sistema | Adopción real |
| Porcentaje de órdenes que pasan por el sistema frente al papel | Profundidad de uso |
| Tiempo medio entre orden y despacho | Valor operativo |
| Restaurantes que pagan después de la prueba | Valor comercial |

## 9. Riesgos principales

| Riesgo | Mitigación |
|---|---|
| Querer abarcar demasiado antes de validar | MVP estricto (`38`) y primer corte vertical |
| Dependencia de internet en el local | Diseño de resiliencia desde el inicio (`33A`) |
| Impresión de tirillas desde la web | Prototipo temprano con impresoras reales (ADR-005) |
| Complejidad legal de facturación electrónica y nómina | Integrar con proveedores en lugar de construir; fuera del MVP |
| Pedidos falsos por QR | Diseño de seguridad del QR (`10A`, `32`) |
