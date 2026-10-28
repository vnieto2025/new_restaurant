// Formatos del restaurante: pesos sin decimales (RG-25) y horas locales
const money = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  maximumFractionDigits: 0,
})

const time = new Intl.DateTimeFormat('es-CO', { hour: 'numeric', minute: '2-digit', hour12: true })
const dateTime = new Intl.DateTimeFormat('es-CO', {
  day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit', hour12: true,
})

export function formatMoney(value) {
  return money.format(Number(value) || 0)
}

// Montos cortos para ejes de gráficas: $80 mil, $1,3 M
export function formatMoneyShort(value) {
  const number = Number(value) || 0
  if (number >= 1_000_000) {
    const millions = number / 1_000_000
    return `$${millions.toLocaleString('es-CO', { maximumFractionDigits: millions < 10 ? 1 : 0 })} M`
  }
  if (number >= 1_000) return `$${Math.round(number / 1_000)} mil`
  return `$${number}`
}

const dayLabel = new Intl.DateTimeFormat('es-CO', { weekday: 'short', day: 'numeric' })
const dateLong = new Intl.DateTimeFormat('es-CO', { weekday: 'long', day: 'numeric', month: 'long' })

// "2026-11-22" se interpreta como fecha local, no UTC (si no, se corre un día)
export function parseDate(value) {
  if (!value) return null
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split('-').map(Number)
    return new Date(year, month - 1, day)
  }
  return new Date(value)
}

export function formatDay(value) {
  const date = parseDate(value)
  return date ? dayLabel.format(date) : ''
}

// 01/01/2026: vigencias, resoluciones, documentos
const dateShort = new Intl.DateTimeFormat('es-CO', { day: '2-digit', month: '2-digit', year: 'numeric' })
export function formatDate(value) {
  const date = parseDate(value)
  return date ? dateShort.format(date) : ''
}

export function formatDateLong(value) {
  const date = parseDate(value)
  return date ? dateLong.format(date) : ''
}

export function isoDate(date) {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

// Variación con flecha y texto: nunca solo color (RN-UI-05)
export function formatChange(percent) {
  if (percent === null || percent === undefined) return 'sin datos para comparar'
  if (percent === 0) return 'igual'
  return `${percent > 0 ? '▲' : '▼'} ${Math.abs(percent).toLocaleString('es-CO')} %`
}

// Descarga filas como CSV (separado por ; para que Excel en español lo abra bien)
export function downloadCsv(nombre, columnas, filas) {
  const escape = (valor) => `"${String(valor ?? '').replace(/"/g, '""')}"`
  const lineas = [columnas.map((c) => escape(c.titulo)).join(';')]
  for (const fila of filas) lineas.push(columnas.map((c) => escape(fila[c.campo])).join(';'))
  const blob = new Blob([`\uFEFF${lineas.join('\r\n')}`], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = `${nombre}.csv`
  enlace.click()
  URL.revokeObjectURL(url)
}

// "1 mesa", "3 mesas"
export function plural(cantidad, singular, pluralForm = `${singular}s`) {
  return `${cantidad} ${cantidad === 1 ? singular : pluralForm}`
}

export function formatTime(value) {
  return value ? time.format(new Date(value)) : ''
}

export function formatDateTime(value) {
  return value ? dateTime.format(new Date(value)) : ''
}

// Tiempo transcurrido como reloj: 4:05, 1:12:30
export function formatElapsed(seconds) {
  const total = Math.max(0, Math.floor(seconds))
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = String(total % 60).padStart(2, '0')
  return h ? `${h}:${String(m).padStart(2, '0')}:${s}` : `${m}:${s}`
}

// Minutos transcurridos desde una fecha, en texto corto
export function minutesAgo(value, nowMs = Date.now()) {
  if (!value) return ''
  const minutes = Math.floor((nowMs - new Date(value).getTime()) / 60000)
  if (minutes < 1) return 'ahora'
  if (minutes < 60) return `hace ${minutes} min`
  const hours = Math.floor(minutes / 60)
  return `hace ${hours} h ${minutes % 60} min`
}

// Clave de idempotencia (RG-20). randomUUID solo existe en contextos seguros (https o localhost).
export function newKey() {
  if (globalThis.crypto?.randomUUID) return crypto.randomUUID()
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
}

export const CANALES = {
  tablet: 'Mesa',
  qr_mesa: 'QR',
  qr_rapido: 'Para llevar',
  mostrador: 'Mostrador',
  domicilio: 'Domicilio',
  pos: 'Venta directa',
}

// Estados de ítems y órdenes: mismo texto en todas las pantallas (doc 33, sección 4)
export const ESTADOS = {
  pendiente_aprobacion: { label: 'Por aprobar', tono: 'pendiente' },
  nuevo: { label: 'Nuevo', tono: 'nuevo' },
  nueva: { label: 'Nueva', tono: 'nuevo' },
  en_proceso: { label: 'En proceso', tono: 'proceso' },
  despachado: { label: 'Listo', tono: 'despachado' },
  lista: { label: 'Lista', tono: 'despachado' },
  entregado: { label: 'Entregado', tono: 'entregado' },
  entregada: { label: 'Entregada', tono: 'entregado' },
  cancelado: { label: 'Cancelado', tono: 'cancelado' },
  cancelada: { label: 'Cancelada', tono: 'cancelado' },
  // Documentos de venta (doc 21, sección 4)
  pendiente: { label: 'En cola', tono: 'pendiente' },
  emitida: { label: 'Enviado', tono: 'proceso' },
  aceptada: { label: 'Aceptado', tono: 'entregado' },
  rechazada: { label: 'Rechazado', tono: 'cancelado' },
  anulada: { label: 'Anulado', tono: 'cancelado' },
  // Compras (doc 23, sección 2)
  borrador: { label: 'Borrador', tono: 'pendiente' },
  solicitada: { label: 'Solicitada', tono: 'nuevo' },
  parcial: { label: 'Recibida en parte', tono: 'proceso' },
  recibida: { label: 'Recibida', tono: 'despachado' },
  cerrada: { label: 'Cerrada', tono: 'entregado' },
  // Cupones (doc 25A, sección 2)
  activo: { label: 'Activo', tono: 'entregado' },
  programado: { label: 'Programado', tono: 'nuevo' },
  pausado: { label: 'Pausado', tono: 'pendiente' },
  vencido: { label: 'Vencido', tono: 'cancelado' },
  agotado: { label: 'Agotado', tono: 'cancelado' },
  anulado: { label: 'Anulado', tono: 'cancelado' },
}

export const TIPOS_IDENTIFICACION = { CC: 'Cédula', NIT: 'NIT', CE: 'Cédula de extranjería', PAS: 'Pasaporte', PPT: 'PPT', TI: 'Tarjeta de identidad' }

export const ROLES = {
  admin_empresa: 'Administrador de empresa',
  admin_restaurante: 'Administrador de restaurante',
  cajero: 'Cajero',
  encargado_externos: 'Encargado de pedidos externos',
  mesero: 'Mesero',
  cocina: 'Cocina / bar',
  domiciliario: 'Domiciliario',
}
