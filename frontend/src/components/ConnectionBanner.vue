<script setup>
// Estado de conexión siempre visible cuando falla (doc 33, principio 7)
defineProps({
  status: { type: String, default: 'conectado' },
  online: { type: Boolean, default: true },
})
</script>

<template>
  <div v-if="!online || status === 'sin_conexion'" class="banner" role="alert">
    <strong>Sin conexión.</strong>
    <span v-if="!online">El dispositivo no tiene internet. Lo que ves puede estar desactualizado y no se pueden enviar cambios.</span>
    <span v-else>Reconectando con el servidor… mientras tanto la pantalla se actualiza cada pocos segundos.</span>
  </div>
</template>

<style scoped>
.banner {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: baseline;
  padding: var(--space-3) var(--space-4);
  background: var(--estado-cancelado);
  color: #fff;
  font-size: var(--text-sm);
}
</style>
