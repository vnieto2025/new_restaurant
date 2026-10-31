# 40A - Guía de Instalación y Operación

Cómo poner RestaurantERP en un servidor con Docker, respaldarlo, restaurarlo y actualizarlo. El hosting aún no se elige (`40`, sección 4): esta guía sirve para cualquier servidor Linux con Docker.

## 1. Instalar

Se necesita Docker con Compose y un dominio que apunte al servidor.

```bash
git clone https://github.com/vnieto2025/new_restaurant.git restaurant && cd restaurant
cp .env.example .env
```

Completa `.env`. Genera cada clave por separado:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

| Variable | Qué poner |
|---|---|
| `PUBLIC_URL` | La dirección real, por ejemplo `https://pedidos.mirestaurante.com`. Va impresa en los QR: si cambia, hay que imprimirlos de nuevo |
| `DB_PASS`, `DB_APP_PASS`, `MY_SECRET_KEY` | Claves generadas. `MY_SECRET_KEY` debe tener mínimo 32 caracteres o el backend no arranca |
| `RESPALDO_HORA`, `RESPALDO_DIAS` | Hora del respaldo diario y cuántos días se conservan |
| `RESPALDOS_DIR` | Carpeta del servidor donde quedan los respaldos |

Levanta todo y crea el superadministrador:

```bash
docker compose up -d --build --wait
docker compose exec backend python seed.py --superadmin soporte --password "UnaClaveLarga" --nombre "Soporte"
```

Entra a `PUBLIC_URL` con ese usuario y crea la primera empresa. **No uses `--demo` en producción:** crea usuarios con clave conocida.

## 2. HTTPS

El paquete sirve HTTP en `APP_PORT`. Antes de recibir clientes reales pon delante un proxy con certificado, del proveedor o propio (Caddy, Traefik o nginx). Sin HTTPS, las claves y los datos de los clientes viajan sin cifrar y el celular puede bloquear funciones del navegador.

## 3. Respaldos

El servicio `respaldos` guarda uno al día en `RESPALDOS_DIR`, lo verifica y borra los que pasen de `RESPALDO_DIAS`. Para hacer uno ahora, por ejemplo antes de actualizar:

```bash
docker compose exec respaldos /ops/respaldar.sh --ahora
```

**Falta por decidir con el hosting** (`40`, sección 6): los respaldos quedan en el mismo servidor y sin cifrar. Hay que copiarlos a otro proveedor o zona, y cifrarlos: si se pierde el servidor, se pierden con él.

Los respaldos no incluyen el archivo `.env`. Guárdalo aparte en un lugar seguro: sin `MY_SECRET_KEY` no se pueden leer las credenciales guardadas de pasarela y mensajería, ni siguen funcionando las tablets emparejadas.

## 4. Restaurar

```bash
sh ops/restaurar.sh respaldos/restaurant_AAAAMMDD_HHMMSS.dump
```

**Borra los datos actuales** y pide escribir `RESTAURAR` para seguir. Sirve también en un servidor nuevo: instala según la sección 1, con el mismo `.env`, y restaura.

Practica la restauración cada cierto tiempo en otro servidor y anota el resultado (RN-OPS-03). GitHub Actions la prueba en cada envío, pero eso no reemplaza probar tus propios archivos.

## 5. Actualizar

Hazlo fuera de las horas de servicio (RN-OPS-01):

```bash
docker compose exec respaldos /ops/respaldar.sh --ahora
git pull
docker compose up -d --build --wait
```

Las migraciones se aplican solas al arrancar el backend. **Volver atrás:** vuelve al commit anterior con `git checkout <commit>`, reconstruye y restaura el respaldo que hiciste, porque una migración ya aplicada no se deshace sola.

## 6. Revisar que esté bien

| Qué | Cómo |
|---|---|
| Estado de los servicios | `docker compose ps`: todos en `healthy` o `running` |
| Salud de la aplicación | `PUBLIC_URL/api/salud` responde `{"estado":"ok"}`. Sirve para un monitor externo |
| Errores | `docker compose logs --tail=100 backend` |
| Respaldos | `ls -lh respaldos/`: debe haber uno de hoy. Busca `ERROR` en `docker compose logs respaldos` |

## 7. Límites conocidos

- **Un solo proceso del backend:** el tiempo real y las colas de facturación y mensajes viven dentro de él. No se debe escalar a varias réplicas sin antes llevar eso a Redis y a un trabajador aparte (`37`, ADR de cola de tareas).
- **Sin monitoreo ni alertas incluidos** (`40`, sección 7): dependen del hosting. Como mínimo, apunta un monitor externo a `/api/salud`.
- **Sin despliegue automático:** las actualizaciones se hacen a mano con los pasos de la sección 5.
