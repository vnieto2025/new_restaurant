# 00A - Principios de Diseño

**Estado:** Propuesto

Estos principios sirven para decidir cuando dos opciones parecen igual de buenas. Si una decisión los contradice, debe quedar justificada en `37`.

## Producto

1. **Simplicidad para personal poco técnico.** Un mesero debe poder tomar una orden en pocos toques, sin capacitación larga. Si una pantalla necesita explicación, está mal diseñada.
2. **La operación manda.** En hora pico nada puede bloquear la toma de órdenes ni el despacho. Las funciones administrativas nunca deben frenar las operativas.
3. **Una sola fuente de verdad para cada dato.** Un precio, un impuesto o un estado vive en un único lugar.
4. **Modular por diseño.** Cada módulo debe poder activarse o apagarse por contrato sin romper al resto. Las dependencias entre módulos son explícitas y opcionales cuando es posible.
5. **Lo mínimo útil primero.** Se construye lo que un restaurante pequeño pagaría; lo demás espera a validación.
6. **Los colores y estados significan lo mismo en todo el sistema.** Azul claro, amarillo, verde y rojo no se reutilizan con otro sentido.

## Técnicos

7. **Web primero, sin tiendas.** Todo funciona en navegador y se instala como PWA si el usuario quiere.
8. **Monolito modular antes que microservicios.** Equipo pequeño, un solo despliegue, fronteras claras entre módulos dentro del mismo código.
9. **Aislamiento entre clientes por defecto.** Ninguna consulta debe poder cruzar datos de empresas distintas, ni por error.
10. **Toda acción sensible deja rastro.** Anulaciones, descuentos, cambios de precio y cierres de caja se auditan.
11. **Tolerar fallas, no asumir red perfecta.** Operaciones críticas deben ser reintentables sin duplicarse (idempotencia).
12. **Dinero con precisión.** Nunca números de punto flotante para dinero.
13. **Integrar antes que construir** lo que es legalmente complejo o cambiante (facturación electrónica, pagos, nómina).
14. **Decidir con evidencia.** Cada decisión importante se registra como ADR con sus alternativas.

## Interfaz

15. **Táctil primero** en tablets y cocina: objetivos grandes, poco texto, buen contraste.
16. **Pantallas por rol.** Cada rol ve solo lo que necesita para su trabajo.
17. **Informes comprensibles.** Pocas métricas, bien comparadas, mejor que muchas métricas sin contexto.
