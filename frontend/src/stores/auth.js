import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { configureApi, post } from '@/services/api'
import router from '@/router'

const STORAGE_KEY = 'restaurant.session'
const DEVICE_KEY = 'restaurant.dispositivo'

function readDevice() {
  try {
    return localStorage.getItem(DEVICE_KEY)
  } catch {
    return null
  }
}

function readSession() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || null
  } catch {
    return null
  }
}

// Fecha de expiración (ms) guardada dentro del JWT
function tokenExpiration(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
    return payload.exp * 1000
  } catch {
    return 0
  }
}

// Pantallas de trabajo y el permiso que abre cada una
export const APPS = [
  { name: 'plataforma', label: 'Plataforma', permiso: 'plataforma.gestionar' },
  { name: 'mesero', label: 'Mesas', permiso: 'ordenes.crear_mesa' },
  { name: 'mostrador', label: 'Mostrador', permiso: 'ordenes.crear_externa' },
  { name: 'caja', label: 'Caja', permiso: ['caja.cobrar', 'caja.cobrar_externas', 'caja.turno'] },
  { name: 'cocina', label: 'Producción', permiso: 'cocina.operar' },
  { name: 'entregas', label: 'Domicilios', permiso: ['domicilios.despachar', 'domicilios.entregar'] },
  { name: 'bodega', label: 'Inventario', permiso: ['inventario.movimientos', 'inventario.contar', 'compras.recibir'] },
  { name: 'admin', label: 'Administración', permiso: ['catalogo.gestionar', 'estructura.gestionar', 'usuarios.gestionar', 'datos.exportar'] },
  { name: 'mi-informe', label: 'Mi informe del día', permiso: 'reportes.propio' },
  { name: 'mis-liquidaciones', label: 'Mis propinas y pagos', permiso: 'liquidaciones.ver_propia' },
]

export const useAuthStore = defineStore('auth', () => {
  const session = ref(readSession())
  // Secreto de la tablet o pantalla autorizada; sobrevive a cerrar la sesión de cada persona
  const deviceToken = ref(readDevice())

  const token = computed(() => session.value?.token || null)
  const user = computed(() => session.value?.usuario || null)
  const restaurante = computed(() => session.value?.restaurante || null)
  const restaurantes = computed(() => session.value?.restaurantes || [])
  const zonas = computed(() => session.value?.zonas || [])
  const dispositivo = computed(() => session.value?.dispositivo || null)
  // completo, lectura (suspendido) o exportacion (cancelado), con su mensaje
  const acceso = computed(() => session.value?.acceso || null)
  const roles = computed(() => session.value?.roles || [])
  const puntos = computed(() => session.value?.puntos || [])
  const isAuthenticated = computed(() => !!token.value && tokenExpiration(token.value) > Date.now())

  const permisos = computed(() => new Set(session.value?.permisos || []))
  const modulos = computed(() => new Set(session.value?.modulos || []))
  function can(permiso) {
    const lista = Array.isArray(permiso) ? permiso : [permiso]
    return lista.some((p) => permisos.value.has(p))
  }

  const apps = computed(() => APPS.filter((app) => can(app.permiso)))

  function save(value) {
    session.value = value
    try {
      if (value) localStorage.setItem(STORAGE_KEY, JSON.stringify(value))
      else localStorage.removeItem(STORAGE_KEY)
    } catch {
      // Sin almacenamiento la sesión dura hasta recargar la página
    }
  }

  function setDeviceToken(value) {
    deviceToken.value = value
    try {
      if (value) localStorage.setItem(DEVICE_KEY, value)
      else localStorage.removeItem(DEVICE_KEY)
    } catch {
      // Sin almacenamiento hay que volver a emparejar al recargar
    }
  }

  async function loginWithPin(pin) {
    const { data } = await post('/dispositivo/pin', { token: deviceToken.value, pin })
    save(data)
  }

  async function login(usuario, password) {
    const { data } = await post('/login', { usuario, password })
    save(data)
  }

  // Recarga permisos, zonas y puntos: un cambio de rol aplica sin volver a ingresar
  async function refresh() {
    const { data } = await post('/auth/sesion')
    save({ ...session.value, ...data })
  }

  async function changeRestaurant(restauranteId) {
    const { data } = await post('/auth/cambiar_restaurante', { restaurante_id: restauranteId })
    save(data)
  }

  // En un dispositivo autorizado se vuelve al teclado de PIN; si no, al ingreso con usuario
  function logout() {
    const destino = deviceToken.value ? 'dispositivo' : 'login'
    save(null)
    if (router.currentRoute.value.name !== destino) {
      router.push({ name: destino })
    }
  }

  configureApi({
    getToken: () => token.value,
    onUnauthorized: logout,
    onAccessChanged: () => refresh().catch(() => {}),
  })

  return {
    token, user, restaurante, restaurantes, zonas, puntos, isAuthenticated, apps, modulos, dispositivo, deviceToken, roles, acceso,
    can, login, loginWithPin, setDeviceToken, refresh, changeRestaurant, logout,
  }
})
