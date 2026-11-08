# 44 - Pendientes para producción

**Estado al 2026-11-08:** el código acordado está terminado. La operación completa, la administración, los reportes, la seguridad (con verificación en dos pasos), el restaurante de práctica, el paquete Docker, las pruebas y la integración continua funcionan. La plataforma está lista para un **piloto con un restaurante real**.

Lo que falta depende de decisiones o recursos externos: proveedores, servidor y los primeros usuarios. Está ordenado por cuándo se hace.

## 1. Al elegir proveedores (integraciones reales)

Hoy cada una funciona con un **adaptador simulado**. El código ya separa el adaptador, así que cambiar el simulado por el real es un trabajo acotado, pero necesita el proveedor elegido y sus credenciales de prueba.

| Integración | Hoy | Qué hace falta | Referencia |
|---|---|---|---|
| **Facturación electrónica (DIAN)** | Proveedor simulado: emite, numera y guarda el documento | Elegir el proveedor tecnológico autorizado, conectar su API y probar en su ambiente de habilitación | `Utils/proveedores_factura.py`, docs 21 y 21A |
| **Pagos en línea** | Pasarela simulada (aprobar o rechazar a mano) | Elegir la pasarela, conectar el cobro y los webhooks, y conciliar | Docs 20A y 31A |
| **WhatsApp automático** | Modo manual con un toque (sin costo) funcionando; el automático con proveedor simulado | Proveedor de la API oficial de Meta, plantillas aprobadas y costo por mensaje | `Utils/proveedores_mensaje.py`, doc 31B |
| **Correo** | No existe | Proveedor de correo, si se quiere el resumen diario o recuperación de cuenta por correo | ADR-052, ADR-054 |

## 2. Al comprar el hosting (servidor)

El hosting ya está decidido y se compra al llegar el primer cliente. La guía de instalación (doc 40A) cubre el montaje con Docker.

| Tema | Estado | Qué hacer |
|---|---|---|
| **HTTPS** | No incluido en el paquete | Certificado (Let's Encrypt o el del hosting) delante del frontend. Sin HTTPS no se deben usar QR ni pagos en línea |
| **Dominio y `PUBLIC_URL`** | Variable lista | Definir el dominio antes de imprimir los QR: va impreso en ellos |
| **Respaldos fuera del servidor** | Respaldo diario verificado en el mismo servidor | Copiarlos a otro lugar (almacenamiento del hosting u otro servidor), cifrados |
| **Probar la restauración** | El script existe y se prueba en la integración continua | Restaurar un respaldo real en otro servidor cada cierto tiempo (RN-OPS-03) |
| **Monitoreo** | Existe `/salud` | Un monitor externo que avise si se cae, y alertas de disco y errores |
| **Superadministrador con dos pasos** | `EXIGIR_2FA_PLATAFORMA=1` ya viene en Docker | Al primer ingreso, activarla y guardar los códigos de respaldo fuera del servidor |
| **Secretos** | `.env` fuera del repositorio | Generar claves nuevas y guardar `.env` aparte: sin `MY_SECRET_KEY` no se leen las credenciales guardadas |
| **Más de un servidor** | El límite de intentos de ingreso vive en memoria | Solo si se escala a varias instancias: pasarlo a Redis (ADR-004) |

## 3. Con el primer restaurante (piloto)

- **Impresoras térmicas reales:** hoy se imprime desde el navegador. Medir con el modelo real el corte de papel, las tildes, el ancho y si sale el diálogo de impresión (doc 19A, sección de pruebas).
- **Tablets y pantallas:** emparejar los dispositivos, asignar el PIN de cada persona y revisar la legibilidad de la pantalla de cocina a distancia.
- **Capacitación:** usar el **restaurante de práctica** y la guía paso a paso (doc 43). Hacer el ensayo en vacío allí antes de abrir (RN-ONB-01).
- **Datos reales:** importar la carta desde Excel, cargar las recetas de los platos más vendidos primero y hacer el primer conteo de inventario.
- **Escuchar y ajustar:** los pendientes menores de la sección 4 se priorizan según lo que pida el restaurante.

## 4. Pendientes menores conocidos (anotados en los ADR)

Ninguno bloquea la operación diaria; se hacen si un cliente los pide.

| Pendiente | Dónde está anotado |
|---|---|
| Copiar combos a otra sede (hoy se omiten al copiar la carta) | ADR-048, ADR-050 |
| Margen del combo en Recetas y costos (el combo no tiene receta propia) | ADR-050 |
| Partes de combo con varias elecciones distintas ("2 salsas a elegir") | ADR-050 |
| Marcar agotada una opción de modificador ("Queso extra") | ADR-051 |
| Umbral configurable de "se están acabando" (hoy 5 porciones) | ADR-051 |
| Resumen diario consolidado de varias sedes para el dueño | ADR-052 |
| La práctica no recibe los cambios de la carta real hasta reiniciarla | ADR-053 |
| Recuperar la verificación en dos pasos por correo o con llaves de seguridad | ADR-054 |
| Los botones nuevos que guarden datos deben llevar `v-escribe` (correr `frontend/scripts/marcar_escritura.py`) | ADR-055 |
| El recorrido `e2e/domicilios.py` falla de vez en cuando en la corrida completa (pasa solo); conviene hacerlo estable | — |

## 5. Decididos por el dueño del producto

- **Modo sin internet:** aplazado (2026-10-30). Se retoma cuando se decida.
- **Fiado o crédito a clientes:** no se implementa por ahora.
