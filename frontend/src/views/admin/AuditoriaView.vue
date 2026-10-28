<script setup>
import { ref, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'
import { formatDateTime } from '@/utils/format'

// Quién hizo qué y cuándo (doc 30): anulaciones, reaperturas, precios, ingresos fallidos…
const { quiet } = useAction()
const registros = ref([])
const accion = ref('')

const ACCIONES = {
  item_cancelado: 'Ítem cancelado',
  item_agotado: 'Producto agotado en una orden',
  orden_rechazada: 'Orden de QR rechazada',
  comanda_reabierta: 'Comanda reabierta',
  tirilla_reimpresa: 'Tirilla reimpresa',
  precio_cambiado: 'Cambio de precio',
  producto_agotado: 'Producto marcado agotado',
  producto_disponible: 'Producto disponible',
  qr_regenerado: 'QR revocado y regenerado',
  mesa_estado: 'Mesa bloqueada o activada',
  mesa_cerrada: 'Mesa cerrada',
  restaurante_estado: 'Pausa o cierre del restaurante',
  restaurante_actualizado: 'Configuración cambiada',
  usuario_creado: 'Usuario creado',
  usuario_actualizado: 'Usuario modificado',
  usuario_estado: 'Usuario activado o desactivado',
  login_fallido: 'Ingreso fallido',
  cambio_password: 'Cambio de clave',
}

async function load() {
  registros.value = (await quiet(() => postData('/auditoria/list', { accion: accion.value || null, limite: 200 }))) || []
}

function detalle(registro) {
  const partes = []
  if (registro.motivo) partes.push(`Motivo: ${registro.motivo}`)
  if (registro.antes?.precio !== undefined) partes.push(`Precio: ${registro.antes.precio} → ${registro.despues.precio}`)
  if (registro.despues?.usuario && registro.accion === 'login_fallido') partes.push(`Usuario: ${registro.despues.usuario}`)
  return partes.join(' · ')
}

onMounted(load)
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Auditoría</h1>
        <p>Las acciones sensibles quedan registradas y no se pueden borrar.</p>
      </div>
      <select v-model="accion" class="select" aria-label="Tipo de acción" @change="load">
        <option value="">Todas las acciones</option>
        <option v-for="(label, value) in ACCIONES" :key="value" :value="value">{{ label }}</option>
      </select>
    </header>

    <div class="panel table-wrap">
      <table class="table">
        <thead><tr><th>Cuándo</th><th>Quién</th><th>Qué</th><th>Detalle</th></tr></thead>
        <tbody>
          <tr v-for="registro in registros" :key="registro.id">
            <td>{{ formatDateTime(registro.creado_en) }}</td>
            <td>{{ registro.usuario || 'Cliente o sistema' }}</td>
            <td>{{ ACCIONES[registro.accion] || registro.accion }}</td>
            <td class="muted">{{ detalle(registro) }}</td>
          </tr>
        </tbody>
      </table>
      <p v-if="!registros.length" class="empty">No hay registros para mostrar.</p>
    </div>
  </div>
</template>
