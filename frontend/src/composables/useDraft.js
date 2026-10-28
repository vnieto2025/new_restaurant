import { ref, computed } from 'vue'
import { newKey } from '@/utils/format'

// Borradores en memoria por mesa: salir a la cuadrícula y volver no borra lo que se estaba tomando
const drafts = new Map()

/*
  Orden en preparación antes de enviarla. La clave de idempotencia se crea con el borrador y solo
  cambia cuando el servidor confirma: si el envío falla por red, el reintento usa la misma clave
  y no se duplica la orden (RG-20, doc 17 sección 6).
*/
export function useDraft(id) {
  if (!drafts.has(id)) drafts.set(id, { lineas: [], notas: '', cliente_nombre: '', cliente_telefono: '', acepta_datos: false, clave: newKey() })
  const draft = ref(drafts.get(id))
  let uid = Date.now()

  const lineas = computed(() => draft.value.lineas)
  const cantidades = computed(() => {
    const result = {}
    for (const linea of draft.value.lineas) result[linea.producto_id] = (result[linea.producto_id] || 0) + linea.cantidad
    return result
  })

  // Misma combinación de producto y opciones = misma línea
  function firma(productoId, opciones) {
    return `${productoId}:${opciones.map((o) => o.id).sort((a, b) => a - b).join(',')}`
  }

  function add(producto, opciones = []) {
    const clave = firma(producto.id, opciones)
    // Toques repetidos suman a la misma línea si no tiene nota propia
    const existente = draft.value.lineas.find((l) => l.firma === clave && !l.nota)
    if (existente) {
      existente.cantidad += 1
      return
    }
    draft.value.lineas.push({
      uid: uid++,
      firma: clave,
      producto_id: producto.id,
      nombre: producto.nombre,
      // Precio estimado; el definitivo lo calcula el servidor (RN-ORD-01)
      precio: producto.precio + opciones.reduce((sum, o) => sum + o.precio_extra, 0),
      modificadores: opciones.map((o) => ({ id: o.id, nombre: o.nombre })),
      cantidad: 1,
      nota: '',
    })
  }

  function change(linea) {
    const index = draft.value.lineas.findIndex((l) => l.uid === linea.uid)
    if (index >= 0) draft.value.lineas[index] = linea
  }

  function remove(linea) {
    draft.value.lineas = draft.value.lineas.filter((l) => l.uid !== linea.uid)
  }

  function items() {
    return draft.value.lineas.map((l) => ({
      producto_id: l.producto_id,
      cantidad: l.cantidad,
      nota: l.nota.trim() || null,
      modificadores: (l.modificadores || []).map((m) => m.id),
    }))
  }

  // Se llama solo cuando el servidor confirmó el envío
  function clear() {
    draft.value.lineas = []
    draft.value.notas = ''
    draft.value.cliente_nombre = ''
    draft.value.cliente_telefono = ''
    draft.value.acepta_datos = false
    draft.value.clave = newKey()
  }

  return { draft, lineas, cantidades, add, change, remove, items, clear }
}
