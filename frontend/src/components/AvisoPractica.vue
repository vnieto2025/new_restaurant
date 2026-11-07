<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'

// En el restaurante de práctica (ADR-053) la franja está siempre a la vista, en todas las pantallas
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const { busy, attempt } = useAction()

const visible = computed(() => auth.isAuthenticated && auth.enPractica && !route.meta.public)

async function volver() {
  const ok = await attempt(() => auth.changeRestaurant(auth.practica.real.id), { success: `De vuelta en ${auth.practica.real.nombre}.` })
  if (ok !== undefined) router.push({ name: 'inicio', query: { menu: 1 } })
}
</script>

<template>
  <div v-if="visible" class="practica no-print" role="status">
    <p><strong>Modo práctica.</strong> Nada de lo que hagas aquí cuenta en ventas, caja, inventario ni clientes del restaurante real.</p>
    <button class="volver" type="button" :disabled="busy" @click="volver">Volver a {{ auth.practica.real.nombre }}</button>
  </div>
</template>

<style scoped>
/* Franja con rayas: se distingue de cualquier aviso y de los colores de estado */
.practica {
  position: sticky;
  top: 0;
  z-index: 50;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2) var(--space-4);
  padding: var(--space-2) var(--space-4);
  background: repeating-linear-gradient(-45deg, #1c2225 0 14px, #2c3438 14px 28px);
  color: #fff;
  font-size: var(--text-sm);
}

.volver {
  min-height: 2.5rem;
  padding: 0 var(--space-3);
  border: 2px solid #fff;
  border-radius: var(--radio);
  background: transparent;
  color: #fff;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}
</style>
