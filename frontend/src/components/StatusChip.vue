<script setup>
import { computed } from 'vue'
import { ESTADOS } from '@/utils/format'

// Etiqueta de estado: color + texto, nunca solo color (RN-UI-05)
const props = defineProps({
  estado: { type: String, required: true },
  size: { type: String, default: 'md' },
  // Texto propio cuando el mismo estado se nombra distinto (documento "Anulado", compra "Anulada")
  label: { type: String, default: '' },
})

const info = computed(() => {
  const base = ESTADOS[props.estado] || { label: props.estado, tono: 'pendiente' }
  return props.label ? { ...base, label: props.label } : base
})
</script>

<template>
  <span class="chip" :class="[`tono-${info.tono}`, `chip-${size}`]">
    <span class="dot" aria-hidden="true"></span>{{ info.label }}
  </span>
</template>

<style scoped>
.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4em;
  padding: 0.2em 0.65em;
  border-radius: 999px;
  background: var(--chip-suave);
  color: var(--tinta);
  font-family: var(--font-ui);
  font-weight: 600;
  font-size: var(--text-sm);
  white-space: nowrap;
  line-height: 1.4;
}

.chip-lg {
  font-size: var(--text-base);
  padding: 0.3em 0.85em;
}

.dot {
  width: 0.65em;
  height: 0.65em;
  border-radius: 50%;
  background: var(--chip-color);
}

.tono-pendiente {
  --chip-color: var(--estado-pendiente);
  --chip-suave: var(--estado-pendiente-suave);
}

.tono-nuevo {
  --chip-color: var(--estado-nuevo);
  --chip-suave: var(--estado-nuevo-suave);
}

.tono-proceso {
  --chip-color: var(--estado-proceso);
  --chip-suave: var(--estado-proceso-suave);
}

.tono-despachado {
  --chip-color: var(--estado-despachado);
  --chip-suave: var(--estado-despachado-suave);
}

.tono-entregado {
  --chip-color: var(--estado-entregado);
  --chip-suave: var(--estado-entregado-suave);
}

.tono-cancelado {
  --chip-color: var(--estado-cancelado);
  --chip-suave: var(--estado-cancelado-suave);
}
</style>
