import { ref, onMounted, onBeforeUnmount, watch, isRef } from 'vue'
import { API_URL } from '@/services/api'
import { useAuthStore } from '@/stores/auth'

const PING_MS = 25000
const POLL_MS = 15000
const MAX_BACKOFF_MS = 15000

/*
  Conexión WebSocket a los canales de una pantalla (cocina, zona, vista general).
  - Los eventos son avisos: al recibir uno, la pantalla vuelve a pedir el estado (onEvent).
  - Al reconectar se recarga todo (onSync), porque pudo perderse algún aviso.
  - Si el WebSocket no conecta, se consulta cada POLL_MS como respaldo (doc 18, sección 9).
*/
export function useRealtime(channels, { onEvent, onSync }) {
  const auth = useAuthStore()
  const status = ref('conectando') // conectando | conectado | sin_conexion
  const online = ref(navigator.onLine)

  let socket = null
  let pingTimer = null
  let pollTimer = null
  let retryTimer = null
  let attempts = 0
  let closed = false

  function currentChannels() {
    const value = isRef(channels) ? channels.value : typeof channels === 'function' ? channels() : channels
    return (value || []).filter(Boolean)
  }

  function wsUrl() {
    const base = API_URL.startsWith('http') ? API_URL : `${location.origin}${API_URL}`
    const url = new URL(`${base.replace(/^http/, 'ws')}/ws`)
    url.searchParams.set('token', auth.token || '')
    url.searchParams.set('canales', currentChannels().join(','))
    return url.toString()
  }

  function startPolling() {
    if (pollTimer) return
    pollTimer = setInterval(() => onSync?.(), POLL_MS)
  }

  function stopPolling() {
    clearInterval(pollTimer)
    pollTimer = null
  }

  function connect() {
    if (closed || !currentChannels().length || !auth.token) return
    clearTimeout(retryTimer)
    status.value = attempts ? 'sin_conexion' : 'conectando'

    socket = new WebSocket(wsUrl())

    socket.onopen = () => {
      const reconnecting = attempts > 0
      attempts = 0
      status.value = 'conectado'
      stopPolling()
      clearInterval(pingTimer)
      pingTimer = setInterval(() => socket?.readyState === 1 && socket.send('ping'), PING_MS)
      if (reconnecting) onSync?.()
    }

    socket.onmessage = (message) => {
      if (message.data === 'pong') return
      try {
        const event = JSON.parse(message.data)
        if (event.tipo !== 'conectado') onEvent?.(event)
      } catch {
        // Mensaje sin formato: se ignora
      }
    }

    socket.onclose = (event) => {
      clearInterval(pingTimer)
      socket = null
      if (closed) return
      status.value = 'sin_conexion'
      startPolling()
      // 4401: sesión inválida, 4403: sin permiso para el canal. No tiene sentido reintentar rápido.
      const delay = [4401, 4403].includes(event.code) ? MAX_BACKOFF_MS * 2 : Math.min(1000 * 2 ** attempts, MAX_BACKOFF_MS)
      attempts += 1
      retryTimer = setTimeout(connect, delay)
    }
  }

  function reconnect() {
    attempts = Math.max(attempts, 1)
    socket?.close()
    if (!socket) connect()
  }

  function onOnline() {
    online.value = true
    reconnect()
    onSync?.()
  }

  function onOffline() {
    online.value = false
    status.value = 'sin_conexion'
  }

  // Al volver a la pestaña (tablet que se apagó) se resincroniza
  function onVisible() {
    if (document.visibilityState === 'visible') {
      onSync?.()
      if (!socket) reconnect()
    }
  }

  onMounted(() => {
    window.addEventListener('online', onOnline)
    window.addEventListener('offline', onOffline)
    document.addEventListener('visibilitychange', onVisible)
    connect()
  })

  onBeforeUnmount(() => {
    closed = true
    window.removeEventListener('online', onOnline)
    window.removeEventListener('offline', onOffline)
    document.removeEventListener('visibilitychange', onVisible)
    clearInterval(pingTimer)
    clearTimeout(retryTimer)
    stopPolling()
    socket?.close()
  })

  if (isRef(channels)) {
    watch(channels, () => {
      attempts = 0
      if (socket) socket.close()
      else connect()
    })
  }

  return { status, online, reconnect }
}
