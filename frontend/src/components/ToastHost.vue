<script setup>
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()
</script>

<template>
  <div class="toasts" aria-live="polite">
    <div v-for="item in toast.items" :key="item.id" class="toast" :class="`toast-${item.type}`" :role="item.type === 'error' ? 'alert' : 'status'">
      <span>{{ item.message }}</span>
      <button class="close" type="button" aria-label="Cerrar aviso" @click="toast.dismiss(item.id)">×</button>
    </div>
  </div>
</template>

<style scoped>
.toasts {
  position: fixed;
  left: 50%;
  bottom: calc(var(--space-4) + env(safe-area-inset-bottom));
  transform: translateX(-50%);
  z-index: 60;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  width: min(28rem, calc(100vw - 2rem));
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radio);
  border-left: 6px solid var(--toast-color);
  background: var(--tinta);
  color: #fff;
  box-shadow: 0 8px 24px rgba(28, 34, 37, 0.3);
  animation: enter 160ms ease-out;
}

.toast span {
  flex: 1;
}

.toast-success {
  --toast-color: var(--estado-despachado);
}

.toast-info {
  --toast-color: var(--estado-nuevo);
}

.toast-error {
  --toast-color: var(--estado-cancelado);
}

.close {
  border: none;
  background: none;
  font-size: 1.5rem;
  line-height: 1;
  cursor: pointer;
  padding: 0 var(--space-1);
  min-width: 2rem;
}

@keyframes enter {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
}
</style>
