import { ref } from 'vue'
import { useToastStore } from '@/stores/toast'

/*
  Ejecuta una acción que envía datos: muestra "enviando", bloquea el doble toque (RN-UI-03)
  y convierte el error en un aviso claro sin perder lo que el usuario escribió (doc 33, sección 5).
*/
export function useAction() {
  const toast = useToastStore()
  const busy = ref(false)

  async function run(action, { success } = {}) {
    if (busy.value) return undefined
    busy.value = true
    try {
      const result = await action()
      if (success) toast.success(typeof success === 'function' ? success(result) : success)
      return result
    } catch (error) {
      toast.error(error.message)
      throw error
    } finally {
      busy.value = false
    }
  }

  // Igual que run pero sin propagar el error (el aviso ya se mostró)
  async function attempt(action, options) {
    try {
      return await run(action, options)
    } catch {
      return undefined
    }
  }

  // Para cargar datos: sin bloqueo de doble toque (varias consultas pueden ir en paralelo)
  async function quiet(action) {
    try {
      return await action()
    } catch (error) {
      toast.error(error.message)
      return undefined
    }
  }

  return { busy, run, attempt, quiet }
}
