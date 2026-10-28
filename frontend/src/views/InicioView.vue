<script setup>
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'

const auth = useAuthStore()
const router = useRouter()
const { busy, attempt } = useAction()

const DESCRIPCIONES = {
  plataforma: 'Empresas, restaurantes y contratos',
  mesero: 'Tomar órdenes y atender las mesas de tu zona',
  mostrador: 'Para llevar y pedidos que no son de mesa',
  caja: 'Cobrar mesas y pedidos, turno y cierre del día',
  cocina: 'Comandas de cocina o bar',
  admin: 'Carta, zonas, mesas, QR y personal',
  'mi-informe': 'Mesas atendidas, ventas y propinas de hoy',
  'mis-liquidaciones': 'Lo que te corresponde de propinas o entregas, y tus pagos',
  entregas: 'Asignar, seguir y entregar domicilios',
  bodega: 'Mermas, preparaciones, conteos y mercancía que llega',
}

// Pantallas de apoyo: no cuentan para entrar directo a la pantalla de trabajo
const SECUNDARIAS = ['mi-informe', 'bodega', 'mis-liquidaciones']

const apps = computed(() => auth.apps)

onMounted(async () => {
  await attempt(() => auth.refresh())
  // Quien tiene una sola pantalla de trabajo entra directo
  const trabajo = auth.apps.filter((app) => !SECUNDARIAS.includes(app.name))
  if (trabajo.length === 1 && !router.currentRoute.value.query.menu) router.replace({ name: trabajo[0].name })
})

async function changeRestaurant(event) {
  await attempt(() => auth.changeRestaurant(Number(event.target.value)), { success: 'Restaurante cambiado.' })
}
</script>

<template>
  <main class="inicio">
    <header class="head">
      <div>
        <h1>Hola, {{ auth.user?.nombre?.split(' ')[0] }}</h1>
        <p v-if="auth.restaurante" class="muted">{{ auth.restaurante.nombre }}</p>
      </div>
      <div class="actions">
        <select v-if="auth.restaurantes.length > 1" class="select" :value="auth.restaurante?.id" :disabled="busy"
                aria-label="Restaurante" @change="changeRestaurant">
          <option v-for="r in auth.restaurantes" :key="r.id" :value="r.id">{{ r.nombre }}</option>
        </select>
        <button class="btn btn-secundario" type="button" @click="auth.logout()">Salir</button>
      </div>
    </header>

    <p v-if="auth.restaurante?.contrato_estado === 'suspendido'" class="aviso">
      El contrato de este restaurante está suspendido. Puedes consultar, pero no tomar órdenes.
    </p>

    <nav v-if="apps.length" class="apps" aria-label="Pantallas de trabajo">
      <RouterLink v-for="app in apps" :key="app.name" :to="{ name: app.name }" class="app">
        <strong>{{ app.label }}</strong>
        <span>{{ DESCRIPCIONES[app.name] }}</span>
      </RouterLink>
    </nav>
    <p v-else class="empty">Tu usuario todavía no tiene una pantalla asignada. Pídele al administrador que revise tus roles.</p>
  </main>
</template>

<style scoped>
.inicio {
  max-width: 56rem;
  margin: 0 auto;
  padding: var(--space-6) var(--space-4);
}

.head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-end;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

h1 {
  font-size: var(--text-3xl);
  font-stretch: 70%;
}

.apps {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
  gap: var(--space-3);
}

.app {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-height: 7.5rem;
  padding: var(--space-5);
  border-radius: var(--radio);
  border: 1px solid var(--linea);
  border-left: 6px solid var(--accion);
  background: var(--superficie);
  text-decoration: none;
}

.app:hover {
  border-color: var(--tinta);
  border-left-color: var(--accion);
}

.app strong {
  font-size: var(--text-xl);
  font-stretch: 78%;
}

.app span {
  color: var(--acero);
}

.aviso {
  margin-bottom: var(--space-5);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radio);
  background: var(--estado-proceso-suave);
}
</style>
