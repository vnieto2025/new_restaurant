<script setup>
import { ref, computed } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'
import { formatMoney } from '@/utils/format'
import { formatCantidad } from '@/utils/inventario'
import AppModal from '@/components/AppModal.vue'

/*
  Un movimiento de inventario sobre un insumo: entrada, merma, ajuste a lo contado o producción
  de una preparación. Merma y ajuste exigen motivo (RN-INV-02).
*/
const props = defineProps({
  tipo: { type: String, required: true }, // entrada | merma | ajuste | producir
  insumo: { type: Object, required: true },
  motivos: { type: Array, default: () => [] },
})
const emit = defineEmits(['close', 'done'])

const { busy, attempt } = useAction()

const TITULOS = { entrada: 'Entrada', merma: 'Registrar merma', ajuste: 'Ajustar existencia', producir: 'Producir' }
const RUTAS = { entrada: '/inventario/entrada', merma: '/inventario/merma', ajuste: '/inventario/ajuste', producir: '/inventario/producir' }

const form = ref({ cantidad: null, presentacion_id: '', costo_total: null, existencia_real: props.insumo.stock, motivo: '' })

const factor = computed(() => props.insumo.presentaciones.find((p) => p.id === Number(form.value.presentacion_id))?.factor || 1)
const enBase = computed(() => (Number(form.value.cantidad) || 0) * factor.value)
const diferencia = computed(() => (Number(form.value.existencia_real) || 0) - props.insumo.stock)
const pideMotivo = computed(() => props.tipo === 'merma' || props.tipo === 'ajuste')
const listo = computed(() => {
  if (pideMotivo.value && form.value.motivo.trim().length < 3) return false
  if (props.tipo === 'ajuste') return form.value.existencia_real !== '' && form.value.existencia_real !== null && diferencia.value !== 0
  return Number(form.value.cantidad) > 0
})

async function guardar() {
  const f = form.value
  const body = { insumo_id: props.insumo.id, motivo: f.motivo.trim() || null }
  if (props.tipo === 'ajuste') body.existencia_real = Number(f.existencia_real)
  else {
    body.cantidad = Number(f.cantidad)
    if (f.presentacion_id) body.presentacion_id = Number(f.presentacion_id)
  }
  if (props.tipo === 'entrada' && f.costo_total) body.costo_total = Number(f.costo_total)
  const data = await attempt(() => postData(RUTAS[props.tipo], body), { success: (r) => r && 'Movimiento registrado.' })
  if (data) emit('done', data)
}
</script>

<template>
  <AppModal :open="true" :title="`${TITULOS[tipo]}: ${insumo.nombre}`" width="30rem" @close="emit('close')">
    <form @submit.prevent="guardar">
      <p class="muted">Hay {{ formatCantidad(insumo.stock, insumo.unidad) }}.</p>

      <template v-if="tipo === 'ajuste'">
        <div class="field">
          <label for="mv-real">Existencia real contada ({{ insumo.unidad }})</label>
          <input id="mv-real" v-model.number="form.existencia_real" class="input" type="number" min="0" step="any" required inputmode="decimal">
        </div>
        <p v-if="diferencia" class="resumen">Se {{ diferencia > 0 ? 'suman' : 'restan' }} {{ formatCantidad(Math.abs(diferencia), insumo.unidad) }}.</p>
      </template>

      <template v-else>
        <div class="fila">
          <div class="field">
            <label for="mv-cant">Cantidad</label>
            <input id="mv-cant" v-model.number="form.cantidad" class="input" type="number" min="0" step="any" required inputmode="decimal">
          </div>
          <div v-if="tipo !== 'producir' && insumo.presentaciones.length" class="field">
            <label for="mv-pres">En</label>
            <select id="mv-pres" v-model="form.presentacion_id" class="select">
              <option value="">{{ insumo.unidad }}</option>
              <option v-for="p in insumo.presentaciones" :key="p.id" :value="p.id">{{ p.nombre }}</option>
            </select>
          </div>
          <span v-else class="unidad">{{ insumo.unidad }}</span>
        </div>
        <p v-if="form.presentacion_id && enBase" class="resumen">= {{ formatCantidad(enBase, insumo.unidad) }}</p>
      </template>

      <div v-if="tipo === 'entrada'" class="field espacio">
        <label for="mv-costo">Valor pagado por todo (sin IVA descontable)</label>
        <input id="mv-costo" v-model.number="form.costo_total" class="input" type="number" min="0" inputmode="numeric">
        <span v-if="form.costo_total && enBase" class="hint">{{ formatMoney(Math.round(form.costo_total / enBase * (insumo.unidad === 'und' ? 1 : 1000))) }}
          por {{ insumo.unidad === 'und' ? 'unidad' : insumo.unidad === 'g' ? 'kg' : 'litro' }}. Recalcula el costo promedio.</span>
      </div>
      <p v-if="tipo === 'producir'" class="muted espacio">Se descuentan los ingredientes de su receta y entra la preparación a ese costo.</p>

      <div v-if="pideMotivo" class="espacio">
        <div v-if="tipo === 'merma' && motivos.length" class="motivos" role="group" aria-label="Motivos frecuentes">
          <button v-for="m in motivos" :key="m" type="button" class="opcion" :aria-pressed="form.motivo === m" @click="form.motivo = m">{{ m }}</button>
        </div>
        <div class="field">
          <label for="mv-motivo">Motivo</label>
          <input id="mv-motivo" v-model="form.motivo" class="input" maxlength="200" required>
        </div>
      </div>
      <div v-else class="field espacio">
        <label for="mv-nota">Nota</label>
        <input id="mv-nota" v-model="form.motivo" class="input" maxlength="200" :placeholder="tipo === 'entrada' ? 'Inventario inicial, llegó sin factura…' : 'Opcional'">
      </div>

      <div class="form-actions">
        <button class="btn btn-secundario" type="button" @click="emit('close')">Cancelar</button>
        <button class="btn" type="submit" :disabled="busy || !listo">Registrar</button>
      </div>
    </form>
  </AppModal>
</template>

<style scoped>
.fila {
  display: flex;
  align-items: flex-end;
  gap: var(--space-3);
}

.fila .field {
  flex: 1;
  min-width: 0;
}

.unidad {
  padding-bottom: var(--space-3);
  font-weight: 700;
}

.resumen {
  margin-top: var(--space-2);
  font-weight: 700;
}

.espacio {
  margin-top: var(--space-3);
}

.motivos {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.opcion {
  min-height: var(--toque);
  padding: 0 var(--space-3);
  border: 1px solid var(--linea);
  border-radius: 999px;
  background: var(--papel);
  font-weight: 600;
  cursor: pointer;
}

.opcion[aria-pressed='true'] {
  border-color: var(--accion);
  background: var(--accion-suave);
}
</style>
