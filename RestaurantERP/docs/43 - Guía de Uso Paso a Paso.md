# 43 - Guía de uso paso a paso

Recorrido por la plataforma con los usuarios de la base demo, en el orden en que se vive un día en un restaurante. Sirve para probarla de punta a punta y como base para capacitar al personal.

## 0. Antes de empezar

**Levantar el sistema (desarrollo):**

```bash
# Backend (puerto 8000)
cd backend && ./env/Scripts/python.exe main.py

# Frontend en la red local (puerto 5173)
cd frontend && pnpm dev --host
```

- En el mismo computador: `http://localhost:5173`
- Desde otro celular o tablet de la misma red: `http://192.168.1.68:5173` (la IP del computador)

**Volver a la base demo limpia** (borra lo que se haya hecho):

```bash
cd backend && ./env/Scripts/python.exe ../e2e/reiniciar_base.py
```

**Consejo:** usa una ventana de incógnito o un navegador distinto por cada persona. Así puedes tener al mesero, la cocina y la caja abiertos al mismo tiempo y ver cómo se avisan entre sí en tiempo real.

## 1. Usuarios disponibles

Todos usan la clave **`demo1234`**, salvo el superadministrador.

### Plataforma (el proveedor del software)

| Usuario | Clave | Quién es | Qué ve |
|---|---|---|---|
| `soporte` | `Soporte12345` | Superadministrador | Consola de empresas, contratos y pagos del servicio |

### La Esquina Centro (comida rápida, plan completo)

Tiene todos los módulos: pedidos, caja, facturación, inventario, domicilios, pagos en línea, cupones y propinas.

| Usuario | Nombre | Rol | Pantalla principal |
|---|---|---|---|
| `esquina` | Dueño La Esquina | Administrador de empresa | Administración completa |
| `admin.esquina` | Laura Admin | Administradora del restaurante | Administración |
| `mesero.salon` | Carlos Mesero | Mesero (zona Salón) | Mesas |
| `mesero.terraza` | Ana Mesera | Mesera (zona Terraza) | Mesas |
| `cocina.esquina` | Pedro Cocina | Cocina | Pantalla de Cocina |
| `bar.esquina` | Sofía Bar | Bar | Pantalla de Bar |
| `caja.esquina` | Marta Caja | Cajera | Caja y Mostrador |
| `domi.esquina` | Julián Moto | Domiciliario | Domicilios (sus entregas) |
| `contador.esquina` | Pedro Contador | Contador (solo lectura) | Reportes y descargas |

**Lo que trae la demo:**
- **Zonas y mesas:** Salón con Mesa 1 a Mesa 8, donde los pedidos por QR los aprueba el mesero y todo el pedido va a la Cocina; Terraza con Terraza 1 a 4, donde los pedidos QR van directo y cada producto va a su punto (comida a Cocina, bebidas a Bar); y Mostrador con la mesa "Para llevar".
- **Puntos de producción:** Cocina y Bar.
- **Carta:** hamburguesas con término de la carne y adicionales, perros y papas, bebidas y el "Combo clásico".
- **Inventario:** insumos con existencias y recetas.
- **Domicilios:** zonas de envío, dos domiciliarios y pedido web activo.
- **Cupones** de ejemplo.

### Pizzería Napoli (solo pedidos, sin caja)

| Usuario | Rol |
|---|---|
| `napoli` | Dueño |
| `mesero.napoli` | Mesero |
| `cocina.napoli` | Cocina |

Sirve para ver cómo funciona un restaurante que solo toma y despacha pedidos, sin cobro en el sistema.

### Panadería Dulce Trigo (caja e inventario, sin pedidos)

| Usuario | Rol |
|---|---|
| `trigo` | Dueña |
| `caja.trigo` | Cajera |

Vende directo desde la caja (POS), sin mesas ni cocina. Además, la demo la deja **en mora** con el pago del servicio, para ver el aviso de cuenta.

## 2. Un día completo en La Esquina

### Paso 1 · Abrir la caja (Marta, `caja.esquina`)
1. Entra y abre **Caja**.
2. Escribe la **base en efectivo**, por ejemplo 100000, y toca **Abrir turno**.
3. La caja queda lista para cobrar mesas, pedidos para llevar y domicilios.

### Paso 2 · Encender las pantallas de producción (Pedro y Sofía)
1. `cocina.esquina` entra y abre **Producción → Cocina**.
2. `bar.esquina` entra y abre **Producción → Bar**.
3. Opcional: tocar **Sonido activado** para que suene con cada comanda nueva. La pantalla viene en modo oscuro y se puede cambiar.

> En un restaurante real estas pantallas se emparejan una vez como dispositivos (Administración → Dispositivos) y cada persona entra con su PIN.

### Paso 3 · Tomar una orden en la mesa (Carlos, `mesero.salon`)
1. Entra a **Mesas**. Solo ve las del Salón, que es su zona.
2. Toca **Mesa 1**, elige una categoría y toca los productos.
   - Si el producto tiene opciones (término de la carne, adicionales), se abre una ventana para elegirlas.
   - Un **combo** se arma eligiendo cada parte, por ejemplo la bebida.
3. Toca **Enviar a cocina**.
4. **Lo que pasa:** el Salón reparte **todo el pedido a su punto**, así que la comida y la bebida llegan juntas a la Cocina. En la **Terraza** (configurada como "cada producto a su punto"), la comida va a la Cocina y la bebida al Bar. Se cambia en Administración → Zonas.

### Paso 4 · Preparar y despachar (Pedro en Cocina, Sofía en Bar)
1. La comanda aparece en **En proceso**. Se toca **Abrir** al empezar; en ese momento se descuenta el inventario.
2. Al terminar, se toca **Despachar**. Se puede despachar todo o solo algunos ítems.
3. **Lo que pasa:** el mesero ve "Para llevar a la mesa" en su lista y lo marca **Entregado**.
4. **Si algo se acabó:** se toca **Agotado** en el ítem. El ítem se cancela, el producto queda agotado en todas las cartas y el mesero recibe el aviso.
5. **Si el inventario dice que un insumo se acabó:** arriba aparece "Se acabó con qué prepararlos" con la sugerencia de agotar los platos que lo usan.

### Paso 5 · El cliente pide desde el QR
1. Con `admin.esquina`, ve a **Administración → Códigos QR** y abre el enlace de una mesa. En un celular real se escanea el QR impreso.
2. El cliente ve la carta, arma su pedido y toca **Enviar pedido**. Después puede seguir el estado desde su celular.
3. **Mesa del Salón:** el mesero debe aprobar el pedido (botón **Aprobar** en Mesas) antes de que llegue a cocina.
4. **Mesa de Terraza:** el pedido va directo a cocina.

### Paso 6 · Pedido para llevar en mostrador (Marta)
1. Abre **Mostrador**, escribe el nombre del cliente, agrega productos y toca **Enviar a cocina**.
2. Lo cobra en **Caja** cuando el cliente paga.

### Paso 7 · Domicilios
1. **El cliente pide por la web:** con `admin.esquina`, en **Administración → Domicilios** está el enlace de pedidos web. El cliente pone zona, dirección y celular.
   > No confundirlo con el QR **"Para llevar"** de Códigos QR: ese es para pedir y **recoger en el local**, no pide dirección y, con el Mostrador en "Libre", va directo a cocina y queda por cobrar en caja.
2. **Confirmar (Marta):** en **Domicilios**, el pedido aparece por confirmar. Se toca **Confirmar y enviar a cocina**.
3. **Asignar y despachar:** cuando está listo, se elige el domiciliario, se imprime la tirilla y se toca **Salió**.
4. **Entregar (Julián, `domi.esquina`):** ve sus entregas y marca **Entregada**. Si no pudo, registra el fallo con el motivo.
5. **Rendir:** al final del turno, la caja recibe el efectivo que recaudó el domiciliario (**Rendir**).
6. **Aviso al cliente:** con cada cambio queda un aviso de WhatsApp listo para enviar con un toque ("Salió a domicilio", etc.).

### Paso 8 · Cobrar (Marta)
1. **Desde la mesa:** en **Mesas**, el mesero toca **Pedir la cuenta e imprimir precuenta** cuando el cliente la pide.
2. **En Caja,** se toca la mesa. Se ve la cuenta con su detalle, y los combos salen como una sola línea.
3. **Opciones de la cuenta:**
   - Elegir la **propina**: la sugerida, sin propina u otro valor.
   - Aplicar un **cupón** o un **descuento**.
   - Agregar el **cliente**, que es necesario para la factura electrónica.
4. **Pago:** se elige el medio de pago (efectivo, tarjeta, transferencia), o varios para dividir la cuenta, y se toca **Cobrar**.
5. **Pago con enlace:** también se puede mandar un enlace de pago en línea; en la demo usa una pasarela simulada.

### Paso 9 · Lo que ve el administrador durante el día (Laura, `admin.esquina`)
- **Hoy:** ventas del día comparadas con la semana pasada, órdenes por estado y caja. Muestra también:
  - **Alertas:** comandas demoradas, cancelaciones, diferencias de caja y stock bajo. Se pueden silenciar o configurar.
  - **Sugerencias de agotados.**
  - El botón para **pausar los pedidos por QR**.
- **Productos:** crear, editar, duplicar, poner foto y alérgenos, armar combos, importar desde Excel y copiar a otra sede.
- **Existencias / Recetas y costos / Compras / Proveedores:** inventario, margen por plato y órdenes de compra.
- **Personal:** usuarios, roles, zonas, PIN y verificación en dos pasos.
- **Reportes:** ventas por producto, categoría, canal, mesero y medio de pago, cancelaciones, horas pico y tiempos.
- **Resumen del día:** el resumen para el dueño, listo para mandar por WhatsApp.

### Paso 10 · Cerrar el día
1. **Mesero:** en **Mesas → Terminar mi turno**. Ve sus ventas y propinas en **Mi informe del día**.
2. **Caja:** **Cerrar turno**. Se cuenta el efectivo y el sistema muestra si sobró o faltó.
3. **Caja o administrador:** **Cerrar la jornada**.
   - Ya no se reciben órdenes ni cobros ese día.
   - Los agotados vuelven a estar disponibles.
   - Si el dueño dejó su celular en **Resumen del día**, el resumen queda listo para enviarle por WhatsApp.

## 3. Lo que hace cada usuario, en detalle

### `soporte`: consola de plataforma
1. Entra y ve la lista de **empresas**, con su plan, estado y pagos.
2. Puede crear una empresa nueva con su primer restaurante y su administrador.
3. Puede cambiar el contrato: módulos, prueba, activo, **suspendido** o **cancelado**. También registra los pagos del servicio.
4. **Para probar:** suspende La Esquina y entra con `admin.esquina`. Verás el aviso **Solo lectura** y sin botones de guardar. Reactívala al terminar.

### `esquina`: dueño de la empresa
- Ve todo lo de Laura, más el **comparativo entre sedes** en Reportes.
- Puede **exigir la verificación en dos pasos** a los administradores (Personal, al final). Al activarla, él mismo queda obligado a configurarla.

### `admin.esquina`: administradora
- Todo lo de **Administración**. Para empezar con un restaurante nuevo, **Puesta en marcha** guía los pasos.
- **Mi cuenta:** cambiar la clave y activar la **verificación en dos pasos** con una app del celular.
- **Puesta en marcha → Restaurante de práctica:**
  1. Crea una copia para entrenar.
  2. El personal entra con "Entrar a la práctica"; una franja con rayas avisa que nada cuenta.
  3. Se reinicia cuando se quiera.

### `mesero.salon` y `mesero.terraza`
- **Mesas:** solo las de su zona. Toman órdenes, aprueban los pedidos QR, entregan, piden la cuenta y cierran la mesa. Trasladar, unir mesas y cambiar el mesero lo hacen la caja y la administración.
- **Mi informe del día:** mesas atendidas, ventas y propinas.
- **Mis propinas y pagos:** lo que le corresponde en cada liquidación.

### `cocina.esquina` y `bar.esquina`
- **Producción:** comandas en proceso y listas, agotados, reimprimir tirilla y reabrir una comanda.
- **Inventario (bodega):** registrar mermas, producir preparaciones (como la salsa de la casa), hacer conteos y recibir mercancía.

### `caja.esquina`
- **Caja:** turno, cobros, abonos, facturas, movimientos de caja (entradas y salidas de efectivo) y cierre. También traslada o une mesas.
- **Mostrador:** pedidos para llevar.
- **Domicilios:** confirmar, despachar y rendir.

### `domi.esquina`
- **Domicilios:** solo sus entregas: salió, entregada o fallida.
- **Mis propinas y pagos.**

### `contador.esquina`
- Ve reportes, facturación, caja e inventario, y descarga todo en **Exportar datos** (Excel o CSV). No puede modificar nada.

### Pizzería Napoli (`napoli`, `mesero.napoli`, `cocina.napoli`)
- El mesero toma la orden y la cocina la despacha. No hay caja: el mesero cierra la mesa cuando el cliente paga por fuera del sistema.

### Panadería Dulce Trigo (`trigo`, `caja.trigo`)
- `caja.trigo` abre turno y vende directo con la **venta directa (POS)**: toca los productos y cobra, sin mesas ni cocina.
- `trigo` ve el aviso de **pago del servicio pendiente** en Administración (Mi plan).

## 4. Pruebas rápidas recomendadas

| Qué probar | Cómo |
|---|---|
| Tiempo real | Mesero, cocina y caja abiertos a la vez: enviar una orden y verla aparecer sin recargar |
| Agotado | En Cocina, marcar **Agotado** un ítem: el mesero recibe aviso y el producto sale de la carta del QR |
| Sugerir agotado | En Existencias, ajustar el **Pan de perro** a 0: Cocina y Hoy sugieren agotar el Perro sencillo |
| Combo | Pedir el Combo clásico: cada parte va a su punto, la caja lo cobra como una línea |
| Alertas | En Hoy → Configurar alertas, bajar el umbral de cancelaciones a 1 y cancelar un ítem |
| Práctica | Crear la práctica, tomar una orden allí y ver que Hoy del restaurante real no cambia |
| Dos pasos | Mi cuenta → activar; salir y volver a entrar con el código del celular |
| Solo lectura | Con `soporte`, suspender La Esquina y entrar con `admin.esquina` |
| Exportar | Exportar datos → descargar productos o ventas en Excel |
