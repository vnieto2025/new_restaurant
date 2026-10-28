# 10A - Códigos QR y Acceso por Mesa

**Estado:** Propuesto

El QR es la puerta de entrada del cliente al sistema y también **la principal superficie de abuso**: cualquiera con el enlace puede intentar crear órdenes en un restaurante. Este documento define los tipos de QR, cómo se construyen y cómo se protegen.

## 1. Tipos de QR

| Tipo | Dónde se coloca | Qué identifica | Mesa asociada |
|---|---|---|---|
| **QR de mesa** | En cada mesa | Empresa, restaurante, zona y mesa | La mesa real |
| **QR de pedidos rápidos** (nombre configurable) | Pared o mostrador | Restaurante y carta de "para llevar" | Mesa externa |
| **QR de domicilios** | Redes sociales, volantes, vitrina | Restaurante y carta de domicilio | Mesa externa |

Los tres abren la misma **carta digital** (`11`), pero con contexto distinto. El contexto lo decide el servidor, no el cliente.

## 2. Qué contiene el QR

El QR contiene **solo una URL** con un **token opaco**, nunca los identificadores de mesa o restaurante en claro:

```
https://<dominio>/q/<token>
```

- El token es **aleatorio y largo** (no secuencial, no adivinable).
- El servidor guarda el token (`qr_acceso`) y lo asocia a empresa, restaurante, zona y mesa.
- Al abrir la URL, el servidor **resuelve el token** y entrega la carta correcta con el contexto ya fijado.
- Quien escanea no puede cambiar la mesa ni la zona editando la URL.

> **Por qué no usar `?mesa=7`:** cualquiera cambiaría el número y pediría en otra mesa o en otro restaurante.

## 3. Ciclo de vida del token

| Acción | Efecto |
|---|---|
| **Crear** | Se genera al crear la mesa o el QR externo |
| **Descargar / imprimir** | El administrador obtiene el QR en PDF o imagen, con nombre de mesa y zona |
| **Revocar y regenerar** | El token anterior deja de funcionar al instante; hay que imprimir el nuevo |
| **Desactivar** | Una mesa o zona fuera de servicio no acepta órdenes por QR |

**Revocar** es la herramienta de emergencia si alguien fotografía el QR de una mesa y lo abusa desde fuera.

## 4. Amenazas y defensas

| Amenaza | Ejemplo | Defensa |
|---|---|---|
| Orden falsa desde fuera del local | Alguien con una foto del QR pide en una mesa vacía | Modo de **aprobación por el mesero** o **mesa abierta** (ver sección 5); límites de frecuencia; revocación |
| Spam de órdenes | Script que crea cientos de órdenes | Límite de órdenes por token y por dispositivo en un periodo; bloqueo temporal |
| Adivinar tokens | Probar URLs al azar | Tokens largos y aleatorios; límite de intentos por IP |
| Cambiar de mesa editando la URL | `?mesa=...` | No existe: el contexto sale del token en el servidor |
| Pedir en nombre de otro restaurante | Reutilizar un token en otro contexto | El token está atado a un único restaurante y mesa |
| Enlaces compartidos por chat | El QR llega a gente que no está en el local | Mismo mecanismo de aprobación/aperturas; sesión de mesa |
| Datos personales expuestos | Se pide teléfono y nombre | Solo los mínimos y con aviso de tratamiento de datos (`32A`) |

> **Verificar ubicación (geolocalización):** se puede pedir la ubicación del celular, pero **no es confiable** (el usuario la deniega o la falsea) y genera fricción. Se considera como señal débil opcional, **no** como defensa principal.

## 5. Modos de aceptación de órdenes por QR de mesa

Se configura **por zona** (con valor por defecto por restaurante):

| Modo | Cómo funciona | Pros | Contras | Recomendado para |
|---|---|---|---|---|
| **Libre** | La orden va directo a producción | Más rápido; cero fricción | Más vulnerable al abuso | Comida rápida, zonas con mucha rotación |
| **Con aprobación** | La orden entra como "pendiente de aprobación" y el mesero la acepta en su tablet | Filtra abusos y errores; el mesero sabe que hay clientes | Depende de que el mesero responda | Restaurantes de mesa, bares |
| **Mesa abierta por mesero** | El QR solo funciona si el mesero abrió la mesa | Máxima protección | Más pasos operativos | Bares y discotecas |

**Recomendación del MVP:** implementar **Libre** y **Con aprobación**, con **Con aprobación** como valor por defecto para zonas de mesa. `[POR CONFIRMAR]` con restaurantes reales.

## 6. Sesión de mesa (concepto)

Cuando un cliente escanea el QR de una mesa, se crea o se une a una **sesión de mesa** abierta:

- Varios clientes de la misma mesa comparten la misma sesión y la misma cuenta.
- Los ítems pedidos desde distintos celulares se acumulan en la misma cuenta.
- La sesión termina cuando el mesero o el cajero cierra la cuenta.
- Las órdenes posteriores a un cierre requieren una nueva sesión.

Esto evita que alguien pida desde casa horas después con una pestaña abierta.

## 7. Impresión y presentación del QR

- El administrador descarga **un PDF imprimible por mesa**, o uno con todas las mesas de una zona.
- Cada QR lleva visible: **nombre del restaurante, zona y número de mesa**, y una instrucción corta ("Escanea para pedir").
- Tamaños recomendados: que se pueda escanear a la distancia de una mesa; se valida con pruebas físicas.
- Materiales resistentes (laminado, acrílico): son responsabilidad del restaurante.

## 8. Información que ve el cliente al abrir el QR

- Nombre del restaurante, zona y mesa (para que confirme que es la correcta).
- Carta de esa zona.
- Si la zona o el restaurante están cerrados o el servicio está suspendido: mensaje claro, sin carta.

## 9. Preguntas abiertas

- ¿Se permite que un cliente pague desde el QR en el MVP? (Recomiendo no; entra con pagos en línea, `20A`.)
- ¿Cuánto tiempo dura una sesión de mesa sin actividad antes de cerrarse sola?
- ¿Se pide nombre o teléfono al cliente que pide por QR de mesa? (Recomiendo **no obligatorio**.)
- ¿Qué límite de órdenes por mesa y por periodo es razonable?
