<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// Elegir el punto de producción de esta pantalla. Con uno solo, entra directo.
const auth = useAuthStore()
const router = useRouter()

onMounted(() => {
  if (auth.puntos.length === 1) router.replace({ name: 'cocina-punto', params: { puntoId: auth.puntos[0].id } })
})
</script>

<template>
  <main class="elegir">
    <h1>¿Qué pantalla es esta?</h1>
    <p class="muted">Elige el punto de producción. La pantalla mostrará solo sus comandas.</p>
    <div class="puntos">
      <RouterLink v-for="punto in auth.puntos" :key="punto.id" class="punto"
                  :to="{ name: 'cocina-punto', params: { puntoId: punto.id } }">
        {{ punto.nombre }}
      </RouterLink>
    </div>
    <p v-if="!auth.puntos.length" class="empty">No tienes puntos de producción asignados.</p>
    <RouterLink class="btn btn-secundario" :to="{ name: 'inicio', query: { menu: 1 } }">Volver</RouterLink>
  </main>
</template>

<style scoped>
.elegir {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  padding: var(--space-5);
  background: var(--tinta);
  color: var(--papel);
  text-align: center;
}

.elegir .muted {
  color: #b5bec2;
}

.puntos {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-3);
  margin: var(--space-4) 0;
}

.punto {
  min-width: 12rem;
  padding: var(--space-5) var(--space-6);
  border-radius: var(--radio);
  background: var(--papel);
  color: var(--tinta);
  font-size: var(--text-2xl);
  font-weight: 700;
  font-stretch: 75%;
  text-decoration: none;
}
</style>
