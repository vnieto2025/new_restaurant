import { ref } from 'vue'
import { defineStore } from 'pinia'

let nextId = 1

// Avisos breves: confirmaciones y errores de las acciones. Los errores no desaparecen solos (doc 34).
export const useToastStore = defineStore('toast', () => {
  const items = ref([])

  function show(message, type = 'success', timeout = 3500) {
    const id = nextId++
    items.value.push({ id, message, type })
    if (timeout) setTimeout(() => dismiss(id), timeout)
  }

  function dismiss(id) {
    items.value = items.value.filter((item) => item.id !== id)
  }

  const success = (message) => show(message, 'success')
  const info = (message) => show(message, 'info', 5000)
  const error = (message) => show(message, 'error', 0)

  return { items, show, dismiss, success, info, error }
})
