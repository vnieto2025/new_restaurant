# Recorridos en el navegador

Pruebas de punta a punta con Playwright: usan la aplicación como lo haría una persona (mesero, caja, cocina,
cliente desde el celular, administración y soporte), toman capturas y fallan si la consola del navegador registra
errores o si una pantalla se desborda a lo ancho.

Complementan las pruebas del backend (`backend/tests`, pytest), que validan las reglas de negocio contra la API.

| Recorrido | Qué cubre |
|---|---|
| `fase1` | Pedido por QR, aprobación, cocina, entrega, caja, tablet con PIN y reportes |
| `clientes` | Registro con autorización de datos, búsqueda y ficha |
| `facturacion` | Impuestos, documento POS, factura a nombre del cliente, tirilla con CUFE |
| `inventario` | Insumos, recetas, consumo por venta, mermas y conteos |
| `compras` | Proveedores, orden de compra, recepción parcial y compra rápida |
| `domicilios` | Pedido a domicilio, asignación, salida, entrega y rendición del efectivo |
| `avisos` | Avisos por WhatsApp a clientes |
| `pagos` | Pago en línea desde el QR y con enlace, rechazo y conciliación |
| `cupones` | Cupones con reglas, cupón de la próxima visita y aplicación desde el celular |
| `liquidaciones` | Reparto de propinas, aprobación, pago y liquidación de domiciliarios |
| `pos_planes` | Venta directa sin pedidos, plan del restaurante y pagos del servicio |
| `solo_lectura` | Suspender y cancelar: consulta y descarga sin operar, QR cerrado y reactivación |
| `exportar` | Descarga de datos en Excel y CSV, datos de personas, auditoría y permisos |
| `domicilio_web` | Domicilio pedido por el cliente desde el enlace, confirmación o rechazo en Entregas y pago en línea |

## Preparar (una vez)

```bash
cd e2e
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # en Linux o Mac: .venv/bin/pip
.venv/Scripts/playwright install chromium         # solo si no usará Edge o Chrome
```

## Correr

1. Backend y frontend en marcha con la base de **desarrollo** (no la de pruebas):
   - `backend`: `python main.py` (puerto 8000)
   - `frontend`: `pnpm dev --host 127.0.0.1` (puerto 5173)
2. Desde `e2e`:

```bash
.venv/Scripts/python correr_todo.py              # todos, reiniciando la base antes de cada uno
.venv/Scripts/python correr_todo.py cupones      # solo uno
.venv/Scripts/python fase1.py                    # un recorrido suelto, sobre la base como esté
```

Cada recorrido se diseñó sobre la base recién reiniciada con los datos demo; `correr_todo.py` la reinicia antes
de cada uno con `reiniciar_base.py` (lo corre con el entorno virtual del backend, `backend/env`), que **borra la base de desarrollo** (nunca la de pruebas ni una con
`APP_ENV=production`).

Las capturas quedan en `e2e/capturas/<recorrido>/` (no se suben al repositorio).

## Variables

| Variable | Por defecto | Para qué |
|---|---|---|
| `E2E_APP` | `http://127.0.0.1:5173` | Dirección del frontend |
| `E2E_API` | `http://127.0.0.1:8000` | Dirección del backend |
| `E2E_NAVEGADOR` | `msedge` | `msedge`, `chrome` o `chromium` (el que instala Playwright) |

Los usuarios demo tienen la clave `demo1234`; el superadministrador es `soporte` / `Soporte12345`.
