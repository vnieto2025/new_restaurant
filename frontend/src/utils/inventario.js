// Unidades base del inventario (doc 22): todo se guarda en g, ml o unidades (RN-INV-03)
export const UNIDADES = { g: 'Gramos (g)', ml: 'Mililitros (ml)', und: 'Unidades' }

const numero = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 3 })

// 2500 g -> "2,5 kg"; 750 ml -> "750 ml"; 12 und -> "12 und"
export function formatCantidad(valor, unidad) {
  const n = Number(valor) || 0
  if (unidad === 'g' && Math.abs(n) >= 1000) return `${numero.format(n / 1000)} kg`
  if (unidad === 'ml' && Math.abs(n) >= 1000) return `${numero.format(n / 1000)} l`
  return `${numero.format(n)} ${unidad}`
}

// Costo por unidad base expresado como se piensa al comprar: por kg, por litro o por unidad
export function costoReferencia(costoUnitario, unidad) {
  const factor = unidad === 'und' ? 1 : 1000
  return { valor: Math.round((Number(costoUnitario) || 0) * factor), por: unidad === 'und' ? 'und' : unidad === 'g' ? 'kg' : 'l' }
}

// Enlace de WhatsApp con el mensaje prellenado (doc 31B). Números de 10 dígitos se toman como de Colombia.
export function enlaceWhatsapp(numero, texto) {
  let digitos = String(numero || '').replace(/\D/g, '')
  if (!digitos) return null
  if (digitos.length === 10) digitos = `57${digitos}`
  return `https://wa.me/${digitos}?text=${encodeURIComponent(texto || '')}`
}
