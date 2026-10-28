# 26B - Nómina

**Estado:** Propuesto como **decisión de no construir en el MVP** (ver ADR-009 en `37`)

Tu documento original preguntaba si convenía **liquidar nómina** dentro del sistema, o limitarse a propinas. Este documento registra la respuesta y qué se hace en su lugar.

## 1. Recomendación

> **No construir una nómina completa.** Ofrecer la liquidación de **propinas** y de **pagos a domiciliarios** (`26A`), y **exportar los datos operativos** a un software de nómina especializado.

## 2. Por qué

| Razón | Detalle |
|---|---|
| **Complejidad legal** | La nómina incluye seguridad social, parafiscales, prestaciones, retenciones, horas extras, recargos nocturnos y dominicales, incapacidades, licencias, liquidaciones de contrato, entre otros |
| **Cambio constante** | Los parámetros (salario mínimo, tasas, reglas) cambian cada año o con reformas |
| **Riesgo** | Un error de cálculo afecta a personas y expone al restaurante a sanciones; la responsabilidad recaería en el proveedor del software |
| **Soporte** | Cada cliente tiene contratos y casos particulares; el soporte consume mucho tiempo |
| **Competencia especializada** | Ya existen herramientas dedicadas, con equipos que solo se ocupan de mantenerlas al día |
| **Foco** | Para tu producto, el valor está en la operación del restaurante, no en competir con software de nómina |

## 3. Qué sí se puede ofrecer

| Función | Descripción | Fase |
|---|---|---|
| **Registro de turnos y horas operativas** | Ya existe para propinas (`08A`) | 2 |
| **Exportación de horas trabajadas** por persona y periodo | CSV/Excel | 2 |
| **Exportación de propinas y pagos a domiciliarios** | CSV/Excel | 2 |
| **Integración con software de nómina** vía exportación o API | Según el proveedor elegido | 3 |
| **Plantilla de datos** compatible con software de nómina comunes | Facilita la carga | 3 |

> **Aclaración:** el registro de turnos del sistema es **operativo**; no equivale al registro legal de la jornada laboral. El restaurante debe validar con su asesor si puede usarlo como soporte. `[POR CONFIRMAR]`

## 4. Cuándo reconsiderarlo

Solo si se cumplen **todas** estas condiciones:

1. Hay clientes que **pagarían** específicamente por esto.
2. Existe **conocimiento laboral** en el equipo o un socio contable.
3. Ya está estable la operación base y los reportes de horas.
4. Se tiene un **plan de mantenimiento regulatorio** (alguien responsable de actualizar parámetros cada año).

Incluso entonces, la alternativa de **integrar** con un proveedor suele ser más sensata que construir.

## 5. Reglas

- **RN-NOM-01.** El sistema no calcula salarios, prestaciones ni aportes en el MVP.
- **RN-NOM-02.** Cualquier exportación de horas indica que son datos operativos, no soportes laborales.
- **RN-NOM-03.** Los datos exportados se limitan a los necesarios y están protegidos por permiso específico.

## 6. Preguntas abiertas

- ¿Los restaurantes de tu público objetivo usan algún software de nómina? ¿Cuál?
- ¿Qué formato de archivo piden esos programas para importar datos?
