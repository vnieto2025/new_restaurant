<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'
import { formatMoney } from '@/utils/format'
import AppModal from '@/components/AppModal.vue'

/*
  Receta de un producto o de una preparación (doc 14). Basta con los insumos principales:
  una receta parcial ya permite descontar y costear (sección 6). Los cambios aplican a las
  órdenes que entren a producción desde ahora (RN-REC-03).
*/
const props = defineProps({
  productoId: { type: Number, default: null },
  insumoId: { type: Number, default: null },
  insumos: { type: Array, required: true },
})
const emit = defineEmits(['close', 'saved'])

const { busy, attempt } = useAction()
const receta = ref(null)
const rendimiento = ref(1)
const lineas = ref([])

const porId = computed(() => Object.fromEntries(props.insumos.map((i) => [i.id, i])))
// Una preparación no se usa a sí misma (RN-REC-02)
const disponibles = computed(() => props.insumos.filter((i) => i.activo && i.id !== props.insumoId))
const costo = computed(() => {
  const total = lineas.value.reduce((s, l) => {
    const insumo = porId.value[l.insumo_id]
    return s + (insumo ? (Number(l.cantidad) || 0) * (1 + (Number(l.merma) || 0) / 100) * insumo.costo_unitario : 0)
  }, 0)
  return total / (Number(rendimiento.value) || 1)
})
const margen = computed(() => receta.value?.precio_sin_impuesto ? receta.value.precio_sin_impuesto - costo.value : null)
const listo = computed(() => lineas.value.length > 0 && lineas.value.every((l) => l.insumo_id && Number(l.cantidad) > 0))

onMounted(async () => {
  const data = await attempt(() => postData('/receta/get', { producto_id: props.productoId, insumo_id: props.insumoId }))
  if (!data) return emit('close')
  receta.value = data
  rendimiento.value = data.rendimiento
  lineas.value = data.lineas.map((l) => ({ insumo_id: l.insumo_id, cantidad: l.cantidad, merma: l.merma }))
  if (!lineas.value.length) agregar()
})

function agregar() {
  lineas.value.push({ insumo_id: '', cantidad: null, merma: 0 })
}

function costoLinea(l) {
  const insumo = porId.value[l.insumo_id]
  return insumo ? (Number(l.cantidad) || 0) * (1 + (Number(l.merma) || 0) / 100) * insumo.costo_unitario : 0
}

async function guardar() {
  const data = await attempt(() => postData('/receta/save', {
    producto_id: props.productoId, insumo_id: props.insumoId, rendimiento: Number(rendimiento.value) || 1,
    lineas: lineas.value.map((l) => ({ insumo_id: Number(l.insumo_id), cantidad: Number(l.cantidad), merma: Number(l.merma) || 0 })),
  }), { success: 'Receta guardada.' })
  if (data) emit('saved', data)
}

async function eliminar() {
  const ok = await attempt(() => postData('/receta/delete', { producto_id: props.productoId, insumo_id: props.insumoId }),
    { success: 'Receta eliminada.' })
  if (ok) emit('saved', null)
}
</script>

<template>
  <AppModal :open="true" :title="receta ? `Receta: ${receta.nombre}` : 'Receta'" width="46rem" @close="emit('close')">
    <form v-if="receta" @submit.prevent="guardar">
      <div class="cabecera">
        <div class="field rendimiento">
          <label for="rc-rend">Rinde ({{ receta.unidad_rendimiento }})</label>
          <input id="rc-rend" v-model.number="rendimiento" class="input" type="number" min="0.001" step="any" required>
        </div>
        <p class="muted">
          {{ productoId ? 'Cantidades para esas porciones. Casi siempre es 1.' : 'Cuánto sale de preparar esta receta completa.' }}
        </p>
      </div>

      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>Insumo</th><th class="num">Cantidad</th><th class="num">Merma %</th><th class="num">Costo</th><th></th></tr></thead>
          <tbody>
            <tr v-for="(l, i) in lineas" :key="i">
              <td>
                <select v-model="l.insumo_id" class="select" :aria-label="`Insumo ${i + 1}`" required>
                  <option value="" disabled>Elige un insumo</option>
                  <option v-for="ins in disponibles" :key="ins.id" :value="ins.id">{{ ins.nombre }} ({{ ins.unidad }})</option>
                </select>
              </td>
              <td class="num">
                <span class="con-unidad">
                  <input v-model.number="l.cantidad" class="input" type="number" min="0.001" step="any" :aria-label="`Cantidad ${i + 1}`" required>
                  <span class="muted">{{ porId[l.insumo_id]?.unidad }}</span>
                </span>
              </td>
              <td class="num"><input v-model.number="l.merma" class="input corto" type="number" min="0" max="99" step="any" :aria-label="`Merma ${i + 1}`"></td>
              <td class="num">{{ formatMoney(Math.round(costoLinea(l))) }}</td>
              <td><button class="btn btn-secundario btn-sm" type="button" :aria-label="`Quitar ingrediente ${i + 1}`" @click="lineas.splice(i, 1)">Quitar</button></td>
            </tr>
          </tbody>
        </table>
      </div>
      <button class="btn btn-secundario btn-sm espacio" type="button" @click="agregar">Agregar ingrediente</button>

      <dl class="totales">
        <div><dt>Costo por {{ productoId ? 'porción' : receta.unidad_rendimiento.replace(/s$/, '') }}</dt>
          <dd>{{ formatMoney(Math.round(costo)) }}</dd></div>
        <template v-if="productoId && receta.precio_sin_impuesto">
          <div><dt>Precio sin impuesto</dt><dd>{{ formatMoney(receta.precio_sin_impuesto) }}</dd></div>
          <div class="total"><dt>Margen</dt>
            <dd>{{ formatMoney(Math.round(margen)) }} · {{ Math.round(margen * 1000 / receta.precio_sin_impuesto) / 10 }} %</dd></div>
        </template>
      </dl>
      <p class="muted">La merma es la pérdida normal al limpiar o cocinar: con 10 % se descuenta un 10 % más. La receta no cambia el precio.</p>

      <div class="form-actions">
        <button v-if="receta.existe" class="btn btn-secundario" type="button" :disabled="busy" @click="eliminar">Eliminar receta</button>
        <button class="btn btn-secundario" type="button" @click="emit('close')">Cancelar</button>
        <button class="btn" type="submit" :disabled="busy || !listo">Guardar</button>
      </div>
    </form>
  </AppModal>
</template>

<style scoped>
.cabecera {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.rendimiento {
  width: 10rem;
}

.cabecera p {
  flex: 1 1 14rem;
  padding-bottom: var(--space-2);
}

.con-unidad {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.con-unidad .input {
  width: 6.5rem;
}

.corto {
  width: 4.5rem;
}

.table .select {
  min-width: 15rem;
}

.espacio {
  margin-top: var(--space-3);
}

.totales {
  margin: var(--space-4) 0 var(--space-2) auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  max-width: 22rem;
}

.totales div {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
}

.totales dt {
  color: var(--acero);
}

.totales dd {
  margin: 0;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

.totales .total {
  font-size: var(--text-lg);
}
</style>
