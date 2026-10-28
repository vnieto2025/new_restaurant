# 18 - Módulo Cocina

**Estado:** Propuesto

Pantalla de producción (KDS) para cocina, bar, parrilla, postres o cualquier **punto de producción** (`19`). En este documento "cocina" se usa como caso típico; todo aplica igual a un bar.

## 1. Objetivo

Que quien prepara vea **qué hacer, en qué orden y para quién**, sin leer ni escribir más de lo necesario, y que el mesero se entere de inmediato cuando algo está listo.

## 2. Estructura de la pantalla

Dos pestañas principales:

| Pestaña | Contiene |
|---|---|
| **En proceso** | Comandas nuevas (azul claro) y en proceso (amarillo) |
| **Listos** | Comandas despachadas pendientes de entregar |

Opcional: una tercera pestaña **Historial** del turno para consultar lo despachado y reabrir por error.

```
┌──────────────────────────────────────────────────────────┐
│  COCINA        [ En proceso (7) ]  [ Listos (3) ]   🖨 ⚙ │
├──────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│ │ #042  Mesa 5│ │ #043 PARA   │ │ #044  Mesa 2│           │
│ │ Zona Rápidas│ │ LLEVAR Ana  │ │ Zona Carta  │           │
│ │ ● NUEVO     │ │ ● EN PROCESO│ │ ● NUEVO     │           │
│ │ 2x Hamburg. │ │ 1x Pizza    │ │ 1x Lasaña   │           │
│ │  - sin cebol│ │ 1x Papas    │ │ ...         │           │
│ │ 1x Papas    │ │ ⏱ 08:12     │ │ ⏱ 00:35     │           │
│ │ [ Abrir ]   │ │ [Despachar] │ │ [ Abrir ]   │           │
│ └─────────────┘ └─────────────┘ └─────────────┘           │
└──────────────────────────────────────────────────────────┘
```

*(Boceto conceptual; el diseño real se define en `33` y `34`.)*

## 3. La tarjeta (comanda)

Cada tarjeta muestra, **en este orden de prioridad visual**:

1. **Número de orden** y **mesa o nombre del cliente externo**.
2. **Zona** y **canal** (con etiqueta destacada: PARA LLEVAR, DOMICILIO, QR).
3. **Estado** con su color.
4. **Ítems** con cantidad, modificadores y notas (las notas resaltadas).
5. **Tiempo transcurrido** desde que llegó.
6. Aviso si es una **adición** o **modificación** a una orden anterior.
7. Acción principal: **Abrir** o **Despachar**.

## 4. Flujo de uso

1. Llega una tarjeta **azul claro** con sonido o aviso.
2. El cocinero pulsa **Abrir**: pasa a **amarillo** (en proceso).
3. Si el punto de producción lo tiene configurado, **se imprime la tirilla** de la comanda (`19A`). También se puede imprimir manualmente.
4. Al terminar y entregarlo al mesero, pulsa **Despachar**: la tarjeta pasa a la pestaña **Listos**.
5. El mesero o domiciliario recoge y confirma `entregado` desde su dispositivo (`16`). La tarjeta sale de **Listos**.

**La tirilla final con precios** se imprime desde caja al cobrar, no desde cocina (`19A`). `[POR CONFIRMAR]`: tu descripción inicial sugería que la tirilla despachada ya llegara facturada; propongo separarlo para no mostrar precios en cocina ni mezclar la comanda con el documento fiscal.

## 5. Acciones disponibles

| Acción | Quién | Comentario |
|---|---|---|
| Abrir comanda | Cocina | Pasa a `en_proceso` |
| Imprimir tirilla | Cocina | Reimpresión queda registrada |
| Despachar | Cocina | Pasa a `despachado` |
| Despachar parcialmente | Cocina | Despacha algunos ítems de la comanda |
| Marcar ítem como agotado | Cocina | Avisa a la tablet de la zona; el ítem se cancela con motivo |
| Reabrir | Cocina | Solo desde Listos, queda auditado |
| Ver historial del turno | Cocina | Consulta |

## 6. Ordenamiento

- Por defecto: **más antigua primero**.
- Las órdenes **modificadas** o **con alerta de tiempo** destacan visualmente.
- Se puede filtrar por **zona** o por **canal**.
- Opción de agrupar por **mesa** para ver todo lo que sale a una misma mesa.

## 7. Alertas y sonido

- Sonido o aviso al llegar una comanda nueva (configurable, con permiso de audio del navegador).
- Indicador visual de **tiempo excedido** (distinto de los colores de estado).
- Aviso de **conexión perdida**: la pantalla indica claramente "sin conexión" y que los datos pueden estar desactualizados.

## 8. Dispositivos y acceso

- Pantalla fija o tablet en modo pantalla completa.
- Inicio de sesión con usuario de **rol cocina** o con **dispositivo emparejado** (el administrador lo vincula a un punto de producción con un código), para no depender de teclear contraseñas en medio del servicio.
- Sesión larga y renovable; no debe cerrarse en plena operación.
- Tema **oscuro** disponible por brillo en cocinas.

## 9. Resiliencia

- Si la pantalla pierde conexión, **no borra** lo que muestra; avisa y reintenta.
- Al reconectar, **recarga el estado completo** desde el servidor (los eventos son avisos, no la fuente de verdad; `04`).
- Si el WebSocket falla, hace **sondeo corto** como respaldo.
- Cada acción de cocina (abrir, despachar) debe confirmarse con el servidor antes de verse como hecha; si falla, lo indica.

## 10. Reglas importantes (resumen)

Detalle en `36`.

- Un ítem despachado no vuelve a `nuevo`.
- Producción solo ve ítems de **su** punto de producción.
- Cualquier modificación a una comanda abierta se avisa con claridad.
- Las acciones de cocina quedan registradas con usuario y hora.

## 11. Preguntas abiertas

- ¿Despachar es por comanda completa, por ítem o ambos? (Recomiendo **ambos**, con la comanda como acción rápida.)
- ¿Se imprime tirilla siempre al abrir o solo bajo demanda? (Configurable por punto de producción.)
- ¿Hace falta un modo "pase" donde una persona coordine varios puntos de producción antes de entregar? (Fuera del MVP.)
