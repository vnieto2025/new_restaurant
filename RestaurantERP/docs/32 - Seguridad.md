# 32 - Seguridad

**Estado:** Propuesto

Visión de seguridad del sistema. Es un SaaS **multi-cliente** con dinero, datos personales y puertas públicas (los QR). Un incidente grave puede acabar con el producto. Aquí se resume el modelo de amenazas y los controles; el detalle de privacidad está en `32A`.

## 1. Qué se protege

| Activo | Por qué importa |
|---|---|
| **Aislamiento entre empresas** | Una fuga entre clientes destruye la confianza |
| **Dinero y caja** | Fraude interno o externo |
| **Datos personales de clientes** | Obligaciones legales y reputación |
| **Credenciales de integraciones** | Acceso a pasarelas, facturación, WhatsApp |
| **Disponibilidad** | Un restaurante sin sistema en hora pico pierde ventas |
| **Integridad de órdenes y estados** | Un error cuesta platos y dinero |

## 2. Modelo de amenazas (resumen)

| Amenaza | Ejemplo | Control principal |
|---|---|---|
| **Cruce de datos entre empresas** | Un error de consulta expone datos ajenos | `empresa_id` + RLS + pruebas automáticas (`02A`, `39`) |
| **Órdenes falsas por QR** | Foto del QR usada a distancia | Token opaco y revocable, aprobación, límites (`10A`) |
| **Robo o abuso de cuentas** | Contraseña débil o reutilizada | Contraseñas fuertes, bloqueo por intentos, 2FA para administradores (fase 2) |
| **Fraude interno** | Cajero anula cuentas y se queda con el dinero | Permisos mínimos, auditoría, alertas, arqueos (`29`, `30`) |
| **Inyección y fallos web** | SQL injection, XSS, CSRF | Consultas parametrizadas, validación, escape, cabeceras de seguridad |
| **Webhooks falsos** | Alguien simula "pago aprobado" | Verificación de firma, idempotencia (`20A`, `31`) |
| **Fuga de secretos** | Credenciales en el código o en logs | Gestión de secretos, cifrado, escaneo (`40`) |
| **Denegación de servicio** | Spam sobre endpoints públicos | Límites de uso, caché, CDN o proxy con protección |
| **Dispositivo comprometido** | Tablet perdida o robada | Dispositivos emparejados revocables, PIN, cierre de sesión remoto |
| **Pérdida de datos** | Falla o borrado accidental | Respaldos y pruebas de restauración (`40`) |
| **Proveedor externo caído o comprometido** | Pasarela o facturación | Adaptadores, contingencia, mínimo de datos compartidos |

## 3. Autenticación y sesiones

- **Contraseñas** con hash moderno para contraseñas (RG-17); política mínima de longitud; **sin** reglas absurdas.
- **Bloqueo temporal** tras intentos fallidos y alertas.
- **Tokens de acceso de vida corta** con renovación; revocables.
- **PIN de mesero** solo sirve en dispositivos autorizados (`RN-USR-03`).
- **2FA opcional** para administradores y obligatorio para superadministradores.
- **Cierre automático por inactividad** configurable, **sin** afectar las pantallas de cocina (`18`).
- **Recuperación de acceso** con verificación segura.

## 4. Autorización

- Permisos evaluados **siempre en el backend** (`29`).
- Verificación de **alcance** (empresa, restaurante, zona) y **módulo contratado**.
- Principio de **mínimo privilegio**: cada rol recibe lo estrictamente necesario.
- Acciones sensibles exigen permisos explícitos y quedan auditadas.

## 5. Protección de datos

| Aspecto | Control |
|---|---|
| **En tránsito** | HTTPS obligatorio, versiones modernas de TLS, cabeceras de seguridad |
| **En reposo** | Cifrado de disco y de respaldos; **cifrado a nivel de campo** para credenciales y secretos |
| **Datos personales** | Mínimos necesarios, acceso auditado (`32A`) |
| **Tarjetas** | **No se almacenan** (RG-19) |
| **Contraseñas** | Solo hashes |
| **Logs** | Sin datos sensibles (`RN-AUD-04`) |

## 6. Seguridad de los QR y de las rutas públicas

Ver `10A`. Resumen: token opaco, contexto resuelto en servidor, revocación inmediata, límites por token, dispositivo e IP, aprobación configurable y registro de abuso.

## 7. Desarrollo seguro

- Revisión de código y **análisis de dependencias** (vulnerabilidades conocidas).
- **Escaneo de secretos** en el repositorio.
- Principios de **OWASP** como lista de verificación.
- Entornos separados con **datos de prueba**, nunca datos reales de clientes.
- Pruebas automáticas de seguridad en el CI (`39`).
- **Prueba de penetración o revisión externa** antes del lanzamiento comercial.

## 8. Dispositivos en el local

- Las tablets y pantallas se **emparejan** y se pueden **revocar** desde administración.
- Recomendación de **modo kiosco** y bloqueo de navegación libre.
- Guía de red del local (Wi-Fi con contraseña propia para el sistema, separada de la red de clientes) en `41`.

## 9. Respuesta a incidentes

- Plan escrito: detección, contención, comunicación con clientes, recuperación y análisis posterior.
- **Aviso a clientes afectados** y, cuando la ley lo exija, a la autoridad (`32A`).
- Rotación inmediata de credenciales comprometidas.
- Capacidad de **revocar** QR, dispositivos y sesiones masivamente.

## 10. Reglas

- **RN-SEG-01.** Ninguna credencial ni secreto se guarda en el código, ni en logs, ni en claro en la base de datos.
- **RN-SEG-02.** Toda ruta pública tiene límite de uso y validación estricta de entrada.
- **RN-SEG-03.** Los administradores pueden revocar sesiones, dispositivos y QR de inmediato.
- **RN-SEG-04.** Los datos de producción no se usan en entornos de prueba.
- **RN-SEG-05.** Una vulnerabilidad crítica se corrige o se mitiga antes de continuar con nuevas funciones.

## 11. Preguntas abiertas

- ¿Se hará una prueba de penetración externa antes de salir a producción?
- ¿Se ofrecerá inicio de sesión con proveedores externos (Google) a administradores?
- ¿Qué proveedor de CDN o protección se usa? (Pendiente, `40`.)
