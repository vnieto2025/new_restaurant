<script setup>
import { ref, watch, onMounted } from 'vue'

// Ventana modal basada en <dialog> nativo: maneja foco, Escape y fondo sin librerías.
const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, required: true },
  width: { type: String, default: '36rem' },
})
const emit = defineEmits(['close'])

const dialog = ref(null)

function sync(open) {
  if (!dialog.value) return
  if (open && !dialog.value.open) dialog.value.showModal()
  if (!open && dialog.value.open) dialog.value.close()
}

watch(() => props.open, sync)
onMounted(() => sync(props.open))

function onBackdropClick(event) {
  if (event.target === dialog.value) emit('close')
}
</script>

<template>
  <dialog
    ref="dialog"
    class="modal"
    :style="{ '--modal-width': width }"
    @cancel.prevent="emit('close')"
    @click="onBackdropClick"
  >
    <div class="modal-body">
      <header class="modal-head">
        <h2>{{ title }}</h2>
        <button class="close" type="button" aria-label="Cerrar" @click="emit('close')">×</button>
      </header>
      <slot v-if="open" />
    </div>
  </dialog>
</template>

<style scoped>
.modal {
  width: min(var(--modal-width), calc(100vw - 2rem));
  max-height: calc(100dvh - 2rem);
  padding: 0;
  border: none;
  border-radius: var(--radio);
  background: var(--superficie);
  color: var(--tinta);
  box-shadow: 0 20px 50px rgba(28, 34, 37, 0.3);
}

.modal::backdrop {
  background: rgba(28, 34, 37, 0.55);
}

.modal-body {
  padding: var(--space-5);
}

.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-5);
}

.close {
  border: none;
  background: none;
  font-size: 1.75rem;
  line-height: 1;
  cursor: pointer;
  color: var(--acero);
  padding: 0 var(--space-1);
}

.close:hover {
  color: var(--tinta);
}
</style>
