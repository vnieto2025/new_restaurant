<script setup>
import { useAuthStore } from '@/stores/auth'

// Barra superior de las pantallas de operación (mesero, mostrador)
defineProps({
  title: { type: String, required: true },
  back: { type: Object, default: () => ({ name: 'inicio' }) },
})

const auth = useAuthStore()
</script>

<template>
  <header class="ops">
    <RouterLink :to="back.name === 'inicio' ? { name: 'inicio', query: { menu: 1 } } : back" class="volver" aria-label="Volver">‹</RouterLink>
    <div class="titulo">
      <h1>{{ title }}</h1>
      <span class="muted">{{ auth.restaurante?.nombre }}</span>
    </div>
    <slot />
    <span class="quien">{{ auth.user?.nombre }}</span>
  </header>
</template>

<style scoped>
.ops {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-4);
  padding-top: calc(var(--space-2) + env(safe-area-inset-top));
  background: var(--tinta);
  color: #fff;
}

.volver {
  display: grid;
  place-items: center;
  width: var(--toque);
  height: var(--toque);
  margin-left: calc(-1 * var(--space-2));
  font-size: 2rem;
  color: #fff;
  text-decoration: none;
}

.titulo {
  display: flex;
  flex-direction: column;
  min-width: 0;
  margin-right: auto;
}

.titulo h1 {
  font-size: var(--text-xl);
  font-stretch: 70%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.titulo .muted {
  color: #aab4b8;
  font-size: var(--text-sm);
}

.quien {
  color: #cfd6d9;
  font-size: var(--text-sm);
  white-space: nowrap;
}

@media (max-width: 34rem) {
  .quien {
    display: none;
  }
}
</style>
