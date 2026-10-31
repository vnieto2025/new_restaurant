<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { formatDateLong } from '@/utils/format'

// Aviso permanente cuando el restaurante está suspendido o cancelado (doc 02A, sección 3). Lo calcula el servidor
const auth = useAuthStore()
const route = useRoute()
const acceso = computed(() => (auth.isAuthenticated && !route.meta.public ? auth.acceso : null))
</script>

<template>
  <p v-if="acceso?.mensaje" class="aviso no-print" role="status">
    <strong>{{ acceso.modo === 'lectura' ? 'Solo lectura.' : 'Contrato cancelado.' }}</strong>
    {{ acceso.mensaje }}
    <template v-if="acceso.hasta"> Disponible hasta el {{ formatDateLong(acceso.hasta) }}.</template>
  </p>
</template>

<style scoped>
.aviso {
  padding: var(--space-2) var(--space-4);
  background: var(--estado-proceso-suave);
  border-bottom: 2px solid var(--estado-proceso);
  color: var(--tinta);
  font-size: var(--text-sm);
}
</style>
