# 34 - Componentes UI

**Estado:** Borrador

Catálogo de **componentes de interfaz** y reglas de diseño visual. Complementa `33`. La elección de librería de UI está **pendiente** (ADR por abrir); este documento define lo que cualquier librería o componente propio debe cumplir.

## 1. Tokens de diseño

Los **tokens** son valores con nombre que se usan en todo el sistema; permiten cambiar el aspecto sin tocar componentes.

### Color semántico

| Token | Uso |
|---|---|
| `estado-pendiente-aprobacion` | Gris |
| `estado-nuevo` | Azul claro |
| `estado-en-proceso` | Amarillo |
| `estado-despachado` | Verde claro |
| `estado-entregado` | Verde |
| `estado-cancelado` | Rojo |
| `accion-primaria` | Acción principal de la pantalla |
| `accion-peligro` | Cancelar, anular, eliminar |
| `alerta-tiempo` | Indicador de demora (**distinto** de los colores de estado) |
| `fondo`, `superficie`, `texto`, `texto-secundario` | Base, en modo claro y oscuro |

Los valores exactos se definen con una **paleta con contraste verificado**. Los colores de estado son idénticos en todas las apps (RG-24).

### Tamaños

| Token | Valor orientativo |
|---|---|
| **Objetivo táctil mínimo** | 48 px (recomendado 56 px o más en tablet y cocina) |
| **Separación entre objetivos** | 8 px o más |
| **Texto base** | Legible a distancia de brazo; tamaño grande en cocina |
| **Escala tipográfica** | Pocos tamaños, con jerarquía clara |

### Otros

Espaciado, radios, sombras y animaciones **mínimas**: nada que distraiga ni retrase.

## 2. Componentes por categoría

### Base

| Componente | Notas |
|---|---|
| **Botón** | Variantes: primario, secundario, peligro, solo ícono. Estados: normal, presionado, deshabilitado, **cargando** (bloquea doble toque) |
| **Campo de texto, numérico, teléfono, búsqueda** | Teclado adecuado; errores claros |
| **Selector y lista de opciones** | Táctil, con búsqueda cuando es larga |
| **Interruptor y casillas** | Grandes |
| **Teclado numérico en pantalla** | Para cantidades, PIN y montos |
| **Etiqueta de estado (chip)** | Color + texto, nunca solo color |
| **Diálogo de confirmación** | Solo para acciones costosas |
| **Aviso y toast** | Éxito, error, información; los errores no desaparecen solos |
| **Banner de conexión** | Persistente (`33A`) |

### Operación

| Componente | Notas |
|---|---|
| **Tarjeta de mesa** | Nombre, estado, indicador del ítem más urgente, tiempo |
| **Cuadrícula de mesas por zona** | Con filtros por estado |
| **Selector de productos** | Categorías, favoritos, búsqueda, cantidades con +/- |
| **Modal de producto** | Variantes, modificadores con mínimos y máximos, notas |
| **Resumen de orden** | Ítems, notas, total, botón "Enviar" |
| **Tarjeta de comanda (KDS)** | Ver `18`: número, mesa o cliente, canal, estado, ítems, tiempo, acción principal |
| **Pestañas En proceso / Listos** | Con contadores |
| **Aviso de orden pendiente de aprobación** | Destacado en la tablet |
| **Identificación de mesero con PIN** | Teclado grande, cambio rápido |

### Dinero

| Componente | Notas |
|---|---|
| **Resumen de cuenta** | Ítems, descuentos, impuestos, propina, total |
| **Selector de medio de pago y pagos mixtos** | Montos parciales visibles |
| **División de cuenta** | Por partes iguales o por ítems |
| **Apertura y cierre de turno** | Conteo de efectivo con teclado numérico |
| **Entrada de monto** | Formato de moneda del restaurante (RG-25) |

### Administración

| Componente | Notas |
|---|---|
| **Tabla de datos** | Orden, filtros, paginación, totales, exportación |
| **Formulario con secciones** | Pocos campos por pantalla |
| **Editor de carta (arrastrar y ordenar)** | Fase 2 si es complejo; en MVP, orden numérico |
| **Importador de datos (CSV/Excel)** | Vista previa y reporte de errores |
| **Generador de QR** | Vista previa, descarga y impresión |
| **Gráficos** | Barras, líneas, tortas con pocos segmentos (`26`) |
| **Línea de tiempo de auditoría** | Quién, qué, cuándo |

### Carta digital (cliente)

| Componente | Notas |
|---|---|
| **Cabecera con restaurante, zona y mesa** | Contexto visible |
| **Lista de categorías con salto rápido** | Móvil |
| **Tarjeta de producto** | Foto opcional, precio, agotado |
| **Carrito flotante** | Total estimado visible |
| **Seguimiento del estado de la orden** | Línea o pasos simples |

## 3. Estados de cada componente

Todo componente interactivo define: **normal, foco, presionado, deshabilitado, cargando, error**. Los estados de **error** y **cargando** no se omiten.

## 4. Modo claro y oscuro

- **Cocina y bar:** modo oscuro disponible por brillo y descanso visual.
- **Caja y administración:** modo claro por defecto, oscuro opcional.
- Los **colores de estado** mantienen su identidad en ambos modos y su contraste se verifica.

## 5. Iconografía

- Un solo conjunto de íconos, coherente y simple.
- Cada ícono importante lleva **texto** al lado.
- Íconos para canal (mesa, QR, mostrador, WhatsApp, domicilio, plataforma) consistentes en toda la app.

## 6. Organización técnica

- Componentes compartidos en un paquete común (`packages/ui` en `04`).
- **Catálogo visual** (por ejemplo Storybook) para ver y probar cada componente aislado, incluidos todos sus estados.
- Pruebas visuales automáticas de componentes críticos (tarjeta de comanda, resumen de orden).
- Nombres de componentes y propiedades coherentes con el glosario (`01`).

## 7. Decisión pendiente: librería de UI

| Opción | Pros | Contras |
|---|---|---|
| **Librería existente de Vue** (por ejemplo PrimeVue, Vuetify, Naive UI, Element Plus) | Rapidez, componentes listos | Hay que adaptarla a lo táctil; riesgo de aspecto genérico |
| **Componentes propios sobre Tailwind (o CSS propio)** | Control total, mejor ajuste a lo táctil | Más trabajo inicial |
| **Mixto** | Equilibrio | Requiere disciplina |

**Recomendación provisional:** en el **primer corte vertical**, probar rápidamente una librería y evaluar si sus componentes se ajustan a lo táctil; decidir con evidencia en un ADR. `[POR CONFIRMAR]`

## 8. Reglas

- **RN-UI-01.** Los colores de estado solo se usan para estados de órdenes (`RN-EST-06`).
- **RN-UI-02.** Ninguna acción crítica depende de pasar el cursor o de gestos ocultos.
- **RN-UI-03.** Todo botón que envía datos muestra estado de carga y se bloquea para evitar doble envío.
- **RN-UI-04.** Los objetivos táctiles cumplen el tamaño mínimo definido.
- **RN-UI-05.** Ninguna información crítica se transmite solo por color.

## 9. Preguntas abiertas

- ¿Qué librería de UI se usa? (ADR pendiente.)
- ¿Se necesita personalización por restaurante del color de la carta digital?
- ¿Qué tamaño de pantalla de cocina se considera mínimo?
