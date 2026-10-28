# 25A - Cupones y Fidelización

**Estado:** Cupones implementados en la fase 2 (ver ADR-037); puntos en la fase 3

Cubre tus **cupones personalizados** que se crean y se entregan a los usuarios al pedir. Los puntos de fidelización quedan para la fase 3.

## 1. Tipos de cupón

| Tipo | Ejemplo |
|---|---|
| **Porcentaje** | 10% de descuento en la cuenta |
| **Valor fijo** | Descuento fijo en la cuenta |
| **Producto gratis o con descuento** | Postre de cortesía con una compra |
| **Envío gratis** | Domicilio sin costo |
| **2x1** | Segundo producto sin costo (fase 3) |

## 2. Reglas configurables de un cupón

| Regla | Descripción |
|---|---|
| **Código** | Texto que el cliente ingresa o se aplica automáticamente |
| **Vigencia** | Fecha de inicio y fin |
| **Canales** | En qué canales aplica (mesa, domicilio, para llevar) |
| **Zonas o restaurantes** | Dónde aplica |
| **Monto mínimo** | Compra mínima |
| **Productos o categorías** | Si aplica solo a algunos |
| **Usos totales** | Cantidad máxima de usos |
| **Usos por cliente** | Una vez por cliente, o hasta N |
| **Asignado a un cliente** | Cupón personal, solo lo usa esa persona |
| **Acumulable** | Si puede combinarse con otros (recomiendo **no** por defecto) |
| **Horario** | Días y horas en que se puede usar |
| **Estado** | `activo`, `pausado`, `vencido`, `agotado` |

## 3. Cómo se entregan

| Vía | Cómo |
|---|---|
| **Código impreso o compartido** | Se dice o se imprime en la tirilla |
| **Mensaje al cliente** | Por WhatsApp (con consentimiento, `31B`) |
| **Automático al pedir** | Después de una compra, se emite un cupón para la siguiente (por reglas simples) |
| **Asignación manual** | El administrador crea un cupón personal para un cliente |

## 4. Cómo se aplican

1. El cliente o el cajero ingresa el código.
2. El sistema **valida** todas las reglas.
3. Calcula el descuento sobre la cuenta.
4. Registra la **redención** (cupón, cuenta, cliente, valor).
5. El descuento aparece como línea separada en el documento (`21`).

## 5. Abuso y control

| Riesgo | Mitigación |
|---|---|
| Uso repetido del mismo cupón | Límites de uso y registro de redenciones |
| Códigos compartidos masivamente | Usos totales, vigencia corta, cupones personales |
| Descuentos que dejan pérdida | Mostrar el **costo del cupón** y su efecto en el margen |
| Aplicación fraudulenta por el personal | Permisos, auditoría y reportes de redenciones por usuario |
| Cupón aplicado sobre una cuenta que luego se anula | La redención se revierte con la anulación |

## 6. Reportes

- Redenciones por cupón, canal y periodo.
- Ventas atribuidas a cada cupón.
- **Costo del descuento** y ticket promedio con y sin cupón.
- Clientes nuevos captados.

## 7. Fidelización con puntos (fase 3)

Puntos por compra, canje por productos o descuentos, niveles. **No recomiendo construirlo antes de validar que los cupones simples funcionan**; los programas de puntos añaden pasivos y complejidad.

## 8. Reglas

- **RN-CUP-01.** Un cupón no se aplica si incumple alguna regla; el mensaje indica cuál.
- **RN-CUP-02.** El descuento nunca deja el total de la cuenta en negativo.
- **RN-CUP-03.** Cada redención queda registrada y es reversible solo con la anulación de la cuenta.
- **RN-CUP-04.** Un cupón personal solo se usa con el cliente asignado identificado.
- **RN-CUP-05.** El sistema valida el cupón en el servidor; el cliente solo muestra el resultado.

## 9. Preguntas abiertas

- ¿Los cupones aplican antes o después de la propina e impuestos?
- ¿Quién autoriza cupones de monto alto?
- ¿Pueden aplicarse a órdenes de plataformas externas? (Probablemente no.)
