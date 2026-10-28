<script setup>
import { ref, watch } from 'vue'
import AppModal from '@/components/AppModal.vue'

/*
  Confirmación con motivo para acciones costosas: cancelar, rechazar, reabrir (doc 33, principio 5).
  El motivo queda en el historial y en la auditoría.
*/
const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, required: true },
  description: { type: String, default: '' },
  confirmLabel: { type: String, default: 'Confirmar' },
  danger: { type: Boolean, default: true },
  busy: { type: Boolean, default: false },
  options: { type: Array, default: () => [] },
})
const emit = defineEmits(['close', 'confirm'])

const motivo = ref('')

watch(() => props.open, (open) => {
  if (open) motivo.value = ''
})

function submit() {
  if (motivo.value.trim().length < 3) return
  emit('confirm', motivo.value.trim())
}
</script>

<template>
  <AppModal :open="open" :title="title" width="30rem" @close="emit('close')">
    <form @submit.prevent="submit">
      <p v-if="description" class="description">{{ description }}</p>
      <div v-if="options.length" class="options">
        <button v-for="option in options" :key="option" type="button" class="btn btn-secundario btn-sm"
                :aria-pressed="motivo === option" @click="motivo = option">{{ option }}</button>
      </div>
      <div class="field">
        <label for="motivo">Motivo</label>
        <input id="motivo" v-model="motivo" class="input" maxlength="200" required minlength="3" autocomplete="off">
      </div>
      <div class="form-actions">
        <button type="button" class="btn btn-secundario" @click="emit('close')">Volver</button>
        <button type="submit" class="btn" :class="{ 'btn-peligro': danger }" :disabled="busy || motivo.trim().length < 3"
                :aria-busy="busy">{{ confirmLabel }}</button>
      </div>
    </form>
  </AppModal>
</template>

<style scoped>
.description {
  color: var(--acero);
  margin-bottom: var(--space-4);
}

.options {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.options [aria-pressed='true'] {
  border-color: var(--accion);
  background: var(--accion-suave);
}
</style>
