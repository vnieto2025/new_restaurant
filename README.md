# RestaurantERP

Software para restaurantes pequeños: carta por QR, tablet del mesero, pantalla de cocina, mostrador y administración. La documentación funcional está en [RestaurantERP/](RestaurantERP/README.md).

**Estado:** fases 0, 1 y 2 construidas ([38 - Roadmap](RestaurantERP/docs/38%20-%20Roadmap.md)).

- **Fase 0, corte vertical:** QR de mesa → carta → orden → cocina → en proceso → listo → entregado.
- **Fase 1, MVP operativo:** modificadores de producto; caja con turnos, arqueo, cuenta por mesa, pagos mixtos, división de cuenta, propina, descuentos, anulaciones y cierre de jornada; trasladar, unir y reasignar mesas; tablets autorizadas con PIN y turnos de mesero; horarios de restaurante, zona y carta por franja; reportes con comparativos, informe por mesero y dashboard; aislamiento por empresa también en la base de datos (RLS) y migraciones con Alembic.

- **Fase 2, versión comercial:** clientes, impuestos y facturación electrónica, inventario y recetas, compras, domicilios (también pedidos por la web), avisos por WhatsApp, pagos en línea, cupones, propinas y liquidaciones, POS y planes, exportación e importación de datos.

Los proveedores de facturación, pagos y WhatsApp funcionan con adaptadores simulados hasta elegirlos ([ADR en 37](RestaurantERP/docs/37%20-%20Decisiones%20de%20Arquitectura.md)).

## Cómo levantarlo

**Forma rápida:** doble clic en `iniciar.bat`. Aplica las migraciones pendientes, abre el backend en http://localhost:8000 (documentación de la API en `/docs`), el frontend en http://localhost:5173 y el navegador.

**Primera instalación** (Postgres 18 local):

```bash
# Backend, desde backend/
python -m venv env
env\Scripts\pip install -r requirements-dev.txt
copy .env.example .env          # completar DB_USER, DB_PASS, DB_APP_USER, DB_APP_PASS y MY_SECRET_KEY
env\Scripts\python seed.py --demo --superadmin soporte --password "ClaveLarga123" --nombre "Soporte"

# Frontend, desde frontend/
pnpm install
copy .env.example .env
```

`seed.py` se puede correr varias veces: aplica las migraciones (Alembic), crea el rol de la aplicación y activa el aislamiento por empresa (RLS), sincroniza módulos, permisos y roles, y no duplica nada.

**Dos usuarios de base de datos (ADR-029):** `DB_USER` es el dueño de las tablas (migraciones y `seed.py`); el backend se conecta con `DB_APP_USER`, un rol sin privilegios que `seed.py` crea. Así la base misma impide ver datos de otra empresa. Para un cambio en los modelos: `env\Scripts\python -m alembic revision --autogenerate -m "qué cambió"`.

**En un servidor:** sigue la [guía de instalación](RestaurantERP/docs/40A%20-%20Gu%C3%ADa%20de%20Instalaci%C3%B3n.md), con respaldos, restauración y actualización.

**Con Docker** (servidor): copiar `.env.example` a `.env`, completar las claves y `docker compose up -d --build`. Nginx sirve el frontend y reenvía `/api` (incluido el WebSocket) al backend.

## Usuarios de demostración

`seed.py --demo` crea dos empresas, la segunda para probar que una no ve los datos de la otra. Clave de todos: `demo1234`.

| Usuario | Rol | Entra a |
|---|---|---|
| `esquina` | Dueño (admin de empresa) | Administración |
| `admin.esquina` | Admin del restaurante | Todo el restaurante |
| `mesero.salon` | Mesero, zona Salón (QR con aprobación) | Mesas |
| `mesero.terraza` | Mesero, zona Terraza (QR libre) | Mesas |
| `cocina.esquina` | Cocina | Producción → Cocina |
| `bar.esquina` | Bar | Producción → Bar |
| `caja.esquina` | Cajero | Caja, mostrador y mesas |
| `domi.esquina` | Domiciliario | Entregas |
| `contador.esquina` | Contador (solo consulta) | Reportes y exportar datos |
| `napoli`, `mesero.napoli`, `cocina.napoli` | Otra empresa | — |
| `trigo`, `caja.trigo` | Panadería en plan Gestión, en mora | Caja |

La Esquina tiene contratados todos los módulos; Napoli, solo pedidos.

**PIN en tablet:** en Administración → Dispositivos crea una tablet de zona y anota el código. En Personal asigna un PIN al mesero. En otra ventana abre http://localhost:5173/dispositivo, escribe el código y entra con el PIN.

## Probar el flujo completo

1. Entra como `admin.esquina` → Administración → **Códigos QR** → "Abrir la carta" de la Mesa 5 (o escanéalo con el celular, ver abajo).
2. Pide como cliente. En el Salón la orden queda **por aprobar**.
3. En otra ventana (o en modo incógnito), entra como `mesero.salon`: aparece arriba "Por aprobar" → **Aprobar**.
4. En otra ventana, entra como `cocina.esquina`: la comanda llega sola (WebSocket) → **Abrir** → **Despachar**.
5. El mesero ve "Para llevar a la mesa" → **Entregado**. El cliente ve su pedido entregado.
6. El mesero entra a la mesa → En la mesa → **Pedir la cuenta**.
7. Con `caja.esquina` → **Caja**: abre el turno, toca la mesa, elige la propina y cobra (puede ser con varios medios). La mesa queda libre.
8. Con `admin.esquina` → **Reportes**: ventas del día, comparativos e informe por mesero.

**Con un celular en la misma red:** en `backend/.env` cambia `PUBLIC_URL` a `http://<IP del PC>:5173`, en `frontend/.env` cambia `VITE_API_URL` a `http://<IP del PC>:8000` y reinicia los dos. Los QR nuevos llevarán esa dirección.

## Estructura

Igual que AppGym (ADR-018 en [37](RestaurantERP/docs/37%20-%20Decisiones%20de%20Arquitectura.md)):

```
backend/
  Router/<Modulo>.py      endpoints POST, permiso y módulo exigidos en JWTBearer
  Class/<Modulo>.py       lógica de negocio
  Querys/<modulo>.py      consultas; Querys/base.py filtra todo por empresa y restaurante
  Rules/<modulo>.py       validación de entrada por ruta
  Models/                 una tabla por archivo, nombres en español
  Utils/                  contexto de la petición, máquina de estados, tiempo real, catálogo de roles
  tests/                  pruebas contra Postgres (base restaurant_test)
frontend/src/
  views/operacion/        mesero, mesa, mostrador, cocina
  views/publico/          carta por QR y seguimiento del pedido
  views/admin/            administración del restaurante
  views/plataforma/       consola del proveedor
  composables/            tiempo real, borradores de orden, acciones con estado "enviando"
```

## Pruebas

```bash
cd backend
env\Scripts\python -m pytest tests
```

Borran y recrean la base `restaurant_test` (no tocan la de desarrollo). Cubren el flujo completo, los casos del doc 17 §7 (envío duplicado, varios puntos de producción, edición después de enviar, QR con y sin aprobación, reconexión, dos meseros a la vez), el aislamiento entre empresas, los permisos y los módulos contratados.

## Pendiente

- **Al final del proyecto, con hardware:** probar la impresión con impresoras térmicas reales y tablets reales (ADR-005, doc 19A §8).
- **Fase 2:** facturación electrónica, inventario y recetas, compras y proveedores, domicilios, pagos en línea, WhatsApp, propinas y liquidaciones, cupones, POS de mostrador sin el módulo de pedidos (ADR-007).
- Validar con un contador: precio con impuesto incluido (ADR-021) y tratamiento de la propina.
