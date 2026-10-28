// Cliente HTTP del backend. Todos los endpoints son POST con JSON y responden { code, message, data }.
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export class ApiError extends Error {
  constructor(message, status, data, codigo) {
    super(message)
    this.status = status
    this.data = data
    this.codigo = codigo
  }
}

let getToken = () => null
let onUnauthorized = () => {}

// El store de sesión registra aquí cómo obtener el token y qué hacer si expira
export function configureApi(options) {
  getToken = options.getToken
  onUnauthorized = options.onUnauthorized
}

export async function post(path, body = {}) {
  // El backend solo procesa la petición si el header accept es exactamente application/json
  const headers = {
    accept: 'application/json',
    'Content-Type': 'application/json',
  }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let response
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    })
  } catch {
    throw new ApiError('Sin conexión con el servidor. Revisa el internet del local y vuelve a intentar.', 0)
  }

  const json = await response.json().catch(() => ({}))

  // 401 viene del middleware JWT: la sesión ya no sirve
  if (response.status === 401 && json.detail) {
    if (token) onUnauthorized()
    throw new ApiError(typeof json.detail === 'string' ? json.detail : 'Ingresa de nuevo.', 401)
  }

  // 403 del middleware: permiso o módulo no contratado (RN-API-03)
  if (response.status === 403 && json.detail) {
    const detail = typeof json.detail === 'object' ? json.detail : { mensaje: json.detail }
    throw new ApiError(detail.mensaje || 'No tienes permiso para esto.', 403, null, detail.codigo)
  }

  if (!response.ok) {
    throw new ApiError(json.message || 'No se pudo completar la acción.', response.status, json.data)
  }

  return json
}

// Atajo para los endpoints que solo interesa su data
export async function postData(path, body) {
  const json = await post(path, body)
  return json.data
}
