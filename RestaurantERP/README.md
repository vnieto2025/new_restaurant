# RestaurantERP

Software SaaS **modular** para restaurantes y negocios de comida pequeños y medianos: pizzerías, comida rápida, bares pequeños, cocinas ocultas, panaderías y negocios de comidas especiales. No apunta a grandes cadenas.

Todo funciona como **aplicación web responsive (PWA)** alojada en un servidor: no hay apps en tiendas. Las tablets de zona, la pantalla de cocina, el panel de administración y la carta digital del cliente se abren desde el navegador.

> **Estado del proyecto:** documentación en **primer borrador** (61 documentos). Las **fases 0 y 1** están construidas en `../backend` y `../frontend` (corte vertical y MVP operativo: caja, modificadores, tablets con PIN, horarios y reportes), con las decisiones registradas como ADR-018 a ADR-030 en `37`. Lo demás sigue siendo **propuesta** hasta que se registre como ADR.

---

## Cómo leer esta documentación

Los documentos viven en `docs/` y se numeran por bloques. Cada uno lleva su **estado** en la cabecera:

| Estado | Significado |
|---|---|
| **Borrador** | Primera redacción, puede cambiar mucho |
| **Propuesto** | Hay una recomendación concreta pendiente de que el responsable la confirme |
| **Aprobado** | Decisión tomada; cambiarla requiere un nuevo ADR en `37` |

Los textos marcados con **`[POR CONFIRMAR]`** son supuestos que deben validarse antes de construir. Los marcados con **advertencia legal** requieren revisión de un abogado o contador.

## Por dónde empezar

1. `00 - Product Vision` y `38 - Roadmap` (qué es el producto y qué entra en el MVP).
2. `01 - Glosario` y `02 - Reglas Globales`.
3. `02A - Multi-tenencia y Licenciamiento Modular` y `04 - Arquitectura Técnica`.
4. `37 - Decisiones de Arquitectura` (qué está decidido y qué está pendiente).
5. Los documentos del flujo central: `10A`, `15`, `16`, `17`, `17A`, `18`, `19`.

## Índice


### Fundamentos

| Doc | Estado |
|---|---|
| [00 - Product Vision](docs/00%20-%20Product%20Vision.md) | Propuesto |
| [00A - Principios de Diseño](docs/00A%20-%20Principios%20de%20Dise%C3%B1o.md) | Propuesto |
| [00B - Visión del Dominio](docs/00B%20-%20Visi%C3%B3n%20del%20Dominio.md) | Propuesto |
| [01 - Glosario](docs/01%20-%20Glosario.md) | Propuesto |
| [02 - Reglas Globales](docs/02%20-%20Reglas%20Globales.md) | Propuesto |
| [02A - Multi-tenencia y Licenciamiento Modular](docs/02A%20-%20Multi-tenencia%20y%20Licenciamiento%20Modular.md) | Propuesto |
| [03 - Arquitectura Funcional](docs/03%20-%20Arquitectura%20Funcional.md) | Propuesto |
| [04 - Arquitectura Técnica](docs/04%20-%20Arquitectura%20T%C3%A9cnica.md) | Propuesto |
| [05 - Modelo de Datos](docs/05%20-%20Modelo%20de%20Datos.md) | Borrador |

### Estructura del negocio

| Doc | Estado |
|---|---|
| [06 - Módulo Empresas](docs/06%20-%20M%C3%B3dulo%20Empresas.md) | Propuesto |
| [07 - Módulo Restaurantes](docs/07%20-%20M%C3%B3dulo%20Restaurantes.md) | Propuesto |
| [08 - Módulo Usuarios y Roles](docs/08%20-%20M%C3%B3dulo%20Usuarios%20y%20Roles.md) | Propuesto |
| [08A - Meseros, Turnos y Horarios](docs/08A%20-%20Meseros%2C%20Turnos%20y%20Horarios.md) | Propuesto |
| [09 - Módulo Zonas](docs/09%20-%20M%C3%B3dulo%20Zonas.md) | Propuesto |
| [10 - Módulo Mesas](docs/10%20-%20M%C3%B3dulo%20Mesas.md) | Propuesto |
| [10A - Códigos QR y Acceso por Mesa](docs/10A%20-%20C%C3%B3digos%20QR%20y%20Acceso%20por%20Mesa.md) | Propuesto |

### Catálogo

| Doc | Estado |
|---|---|
| [11 - Módulo Carta Digital](docs/11%20-%20M%C3%B3dulo%20Carta%20Digital.md) | Propuesto |
| [12 - Módulo Productos](docs/12%20-%20M%C3%B3dulo%20Productos.md) | Propuesto |
| [13 - Módulo Categorías](docs/13%20-%20M%C3%B3dulo%20Categor%C3%ADas.md) | Propuesto |
| [14 - Módulo Recetas](docs/14%20-%20M%C3%B3dulo%20Recetas.md) | Propuesto |

### Operación

| Doc | Estado |
|---|---|
| [15 - Módulo Órdenes](docs/15%20-%20M%C3%B3dulo%20%C3%93rdenes.md) | Propuesto |
| [15A - Pedidos Externos y Para Llevar](docs/15A%20-%20Pedidos%20Externos%20y%20Para%20Llevar.md) | Propuesto |
| [15B - Domicilios](docs/15B%20-%20Domicilios.md) | Propuesto |
| [16 - Estados de las Órdenes](docs/16%20-%20Estados%20de%20las%20%C3%93rdenes.md) | Propuesto |
| [17 - Flujo de Órdenes](docs/17%20-%20Flujo%20de%20%C3%93rdenes.md) | Propuesto |
| [17A - Canales de Pedido](docs/17A%20-%20Canales%20de%20Pedido.md) | Propuesto |
| [18 - Módulo Cocina](docs/18%20-%20M%C3%B3dulo%20Cocina.md) | Propuesto |
| [19 - Módulo Punto de Producción](docs/19%20-%20M%C3%B3dulo%20Punto%20de%20Producci%C3%B3n.md) | Propuesto |
| [19A - Impresión y Tirillas](docs/19A%20-%20Impresi%C3%B3n%20y%20Tirillas.md) | Propuesto |

### Dinero y logística

| Doc | Estado |
|---|---|
| [20 - Módulo Caja](docs/20%20-%20M%C3%B3dulo%20Caja.md) | Propuesto |
| [20A - Pagos en Línea](docs/20A%20-%20Pagos%20en%20L%C3%ADnea.md) | Propuesto |
| [21 - Módulo Facturación](docs/21%20-%20M%C3%B3dulo%20Facturaci%C3%B3n.md) | Propuesto |
| [21A - Impuestos y Facturación Electrónica](docs/21A%20-%20Impuestos%20y%20Facturaci%C3%B3n%20Electr%C3%B3nica.md) | Propuesto |
| [22 - Módulo Inventario](docs/22%20-%20M%C3%B3dulo%20Inventario.md) | Propuesto |
| [23 - Módulo Compras](docs/23%20-%20M%C3%B3dulo%20Compras.md) | Propuesto |
| [24 - Módulo Proveedores](docs/24%20-%20M%C3%B3dulo%20Proveedores.md) | Propuesto |
| [25 - Módulo Clientes](docs/25%20-%20M%C3%B3dulo%20Clientes.md) | Propuesto |
| [25A - Cupones y Fidelización](docs/25A%20-%20Cupones%20y%20Fidelizaci%C3%B3n.md) | Propuesto |

### Análisis

| Doc | Estado |
|---|---|
| [26 - Módulo Estadísticas](docs/26%20-%20M%C3%B3dulo%20Estad%C3%ADsticas.md) | Propuesto |
| [26A - Propinas y Liquidaciones](docs/26A%20-%20Propinas%20y%20Liquidaciones.md) | Propuesto |
| [26B - Nómina](docs/26B%20-%20N%C3%B3mina.md) | Propuesto como **decisión de no construir en el MVP** |
| [27 - Dashboard](docs/27%20-%20Dashboard.md) | Propuesto |

### Plataforma y transversales

| Doc | Estado |
|---|---|
| [28 - Módulo Configuración](docs/28%20-%20M%C3%B3dulo%20Configuraci%C3%B3n.md) | Propuesto |
| [29 - Usuarios y Permisos](docs/29%20-%20Usuarios%20y%20Permisos.md) | Propuesto |
| [30 - Auditoría y Logs](docs/30%20-%20Auditor%C3%ADa%20y%20Logs.md) | Propuesto |
| [31 - API REST](docs/31%20-%20API%20REST.md) | Propuesto |
| [31A - Integraciones Externas](docs/31A%20-%20Integraciones%20Externas.md) | Propuesto |
| [31B - Notificaciones y WhatsApp](docs/31B%20-%20Notificaciones%20y%20WhatsApp.md) | Propuesto |
| [32 - Seguridad](docs/32%20-%20Seguridad.md) | Propuesto |
| [32A - Privacidad y Cumplimiento](docs/32A%20-%20Privacidad%20y%20Cumplimiento.md) | Propuesto |
| [33 - UX General](docs/33%20-%20UX%20General.md) | Propuesto |
| [33A - Offline y Resiliencia](docs/33A%20-%20Offline%20y%20Resiliencia.md) | Propuesto |
| [34 - Componentes UI](docs/34%20-%20Componentes%20UI.md) | Borrador |

### Casos de uso, reglas y decisiones

| Doc | Estado |
|---|---|
| [35 - Casos de Uso](docs/35%20-%20Casos%20de%20Uso.md) | Borrador |
| [36 - Reglas de Negocio](docs/36%20-%20Reglas%20de%20Negocio.md) | Borrador |
| [37 - Decisiones de Arquitectura](docs/37%20-%20Decisiones%20de%20Arquitectura.md) | Propuesto |
| [38 - Roadmap](docs/38%20-%20Roadmap.md) | Propuesto |

### Calidad, operación y negocio

| Doc | Estado |
|---|---|
| [39 - Pruebas y Calidad](docs/39%20-%20Pruebas%20y%20Calidad.md) | Propuesto |
| [40 - Despliegue y Operación](docs/40%20-%20Despliegue%20y%20Operaci%C3%B3n.md) | Propuesto |
| [41 - Onboarding y Soporte](docs/41%20-%20Onboarding%20y%20Soporte.md) | Propuesto |
| [42 - Modelo Comercial y Planes](docs/42%20-%20Modelo%20Comercial%20y%20Planes.md) | Borrador |

## Convenciones

- Idioma de la documentación: **español**.
- Término oficial para el pedido del cliente: **Orden** (ver glosario y ADR-008).
- Mercado inicial asumido: **Colombia** `[POR CONFIRMAR]`.
- Códigos: `RG-nn` reglas globales (`02`), `RN-<módulo>-nn` reglas de negocio, `UC-nn` casos de uso (`35`), `ADR-nnn` decisiones (`37`).
- Cada decisión importante se registra en `37 - Decisiones de Arquitectura`.

## Decisiones pendientes más importantes

| Tema | Dónde |
|---|---|
| Estrategia de impresión de tirillas | ADR-005, `19A` |
| Precios con o sin impuesto incluido | ADR-010, `21` |
| Mercado, impuestos y facturación electrónica (validar con contador) | `21A` |
| Pasarela de pagos | `20A` |
| WhatsApp: enlace manual ahora, API oficial después | `31B` |
| Propinas: individual, colectiva o mixta | `26A` |
| Integraciones con plataformas de domicilio | `31A` |
| Hosting y librería de UI | `40`, `34` |

## Siguiente paso recomendado

Antes de escribir código: entrevistar a 2 o 3 restaurantes del público objetivo con las preguntas de `38 - Roadmap` (sección 6), revisar el borrador con un contador y un abogado en los puntos marcados, y construir el **primer corte vertical** (QR → carta → orden → cocina → listo).
