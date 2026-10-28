<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { formatMoney, isoDate } from '@/utils/format'
import { formatCantidad } from '@/utils/inventario'
import AppModal from '@/components/AppModal.vue'

/*
  Compra rápida (plaza, tienda: se registra ya recibida) u orden de compra al proveedor (doc 23, sección 1).
  En la rápida se escribe lo que se pagó por cada insumo; en la orden, el precio por unidad de compra.
*/
const props = defineProps({
  modo: { type: String, default: 'rapida' }, // rapida | orden
  compra: { type: Object, default: null }, // compra a editar o datos iniciales (lista sugerida)
  insumos: { type: Array, required: true },
  proveedores: { type: Array, required: true },
})
const emit = defineEmits(['close', 'saved'])

const auth = useAuthStore()
const { busy, attempt } = useAction()
const rapida = computed(() => props.modo === 'rapida')
const editando = computed(() => !!props.compra?.id)

const form = ref({
  proveedor_id: props.compra?.proveedor_id || '',
  proveedor_nombre: props.compra?.proveedor_id ? '' : (props.compra?.proveedor || ''),
  forma_pago: props.compra?.forma_pago || (rapida.value && auth.can('caja.movimientos') ? 'caja' : 'contado'),
  fecha: props.compra?.fecha || isoDate(new Date()),
  entrega_esperada: props.compra?.entrega_esperada || '',
  factura_proveedor: '',
  notas: props.compra?.notas || '',
})
const lineas = ref((props.compra?.lineas || []).map((l) => ({
  insumo_id: l.insumo_id, presentacion_id: l.presentacion_id || '', cantidad: l.cantidad,
  monto: rapida.value ? l.total : (l.precio_unitario ?? null), impuesto_porcentaje: l.impuesto_porcentaje || 0,
})))
const delProveedor = ref({})

const comprables = computed(() => props.insumos.filter((i) => i.activo && !i.es_preparacion))
const porId = computed(() => Object.fromEntries(props.insumos.map((i) => [i.id, i])))
const activos = computed(() => props.proveedores.filter((p) => p.activo || p.id === form.value.proveedor_id))
const proveedor = computed(() => props.proveedores.find((p) => p.id === Number(form.value.proveedor_id)))

function factor(l) {
  return porId.value[l.insumo_id]?.presentaciones.find((p) => p.id === Number(l.presentacion_id))?.factor || 1
}
function totalLinea(l) {
  const monto = Number(l.monto) || 0
  return rapida.value ? monto : Math.round(monto * (Number(l.cantidad) || 0))
}
const total = computed(() => lineas.value.reduce((s, l) => s + totalLinea(l), 0))
const listo = computed(() => lineas.value.length > 0 &&
  lineas.value.every((l) => l.insumo_id && Number(l.cantidad) > 0 && l.monto !== null && l.monto !== '' && Number(l.monto) >= 0))
const bajoMinimo = computed(() => !rapida.value && proveedor.value?.pedido_minimo && total.value < proveedor.value.pedido_minimo)

// Lo que este proveedor ya surte: presentación habitual y último precio
async function cargarProveedor() {
  delProveedor.value = {}
  if (!form.value.proveedor_id) return
  const data = await attempt(() => postData('/proveedor/get', { proveedor_id: Number(form.value.proveedor_id) }))
  if (data) delProveedor.value = Object.fromEntries(data.insumos.map((i) => [i.insumo_id, i]))
  if (!editando.value && data && !props.compra) form.value.forma_pago = rapida.value && form.value.forma_pago === 'caja' ? 'caja' : data.forma_pago
}
watch(() => form.value.proveedor_id, cargarProveedor)

function elegirInsumo(l) {
  const habitual = delProveedor.value[l.insumo_id]
  l.presentacion_id = habitual?.presentacion_id || ''
  if (!rapida.value && habitual?.ultimo_precio != null && (l.monto === null || l.monto === '')) l.monto = habitual.ultimo_precio
}

function agregar() {
  lineas.value.push({ insumo_id: '', presentacion_id: '', cantidad: null, monto: null, impuesto_porcentaje: 0 })
}

function ultimoPrecio(l) {
  const habitual = delProveedor.value[l.insumo_id]
  if (!habitual?.ultimo_precio || Number(habitual.presentacion_id || 0) !== Number(l.presentacion_id || 0)) return null
  return habitual.ultimo_precio
}

async function guardar(solicitar = false) {
  const f = form.value
  const body = {
    proveedor_id: f.proveedor_id ? Number(f.proveedor_id) : null,
    proveedor_nombre: f.proveedor_id ? null : (f.proveedor_nombre.trim() || null),
    forma_pago: f.forma_pago, fecha: f.fecha || null, notas: f.notas.trim() || null,
    lineas: lineas.value.map((l) => ({
      insumo_id: Number(l.insumo_id), presentacion_id: l.presentacion_id ? Number(l.presentacion_id) : null,
      cantidad: Number(l.cantidad), impuesto_porcentaje: Number(l.impuesto_porcentaje) || 0,
      ...(rapida.value ? { total: Math.round(Number(l.monto)) } : { precio_unitario: Number(l.monto) }),
    })),
  }
  let ruta = '/compra/rapida'
  if (rapida.value) body.factura_proveedor = f.factura_proveedor.trim() || null
  else {
    body.entrega_esperada = f.entrega_esperada || null
    if (editando.value) {
      ruta = '/compra/update'
      body.compra_id = props.compra.id
    } else {
      ruta = '/compra/create'
      body.solicitar = solicitar
    }
  }
  const data = await attempt(() => postData(ruta, body), {
    success: (r) => r && (rapida.value ? `Compra ${r.numero} registrada.` : `Compra ${r.numero} guardada.`),
  })
  if (data) emit('saved', data)
}

onMounted(() => {
  if (!lineas.value.length) agregar()
  if (form.value.proveedor_id) cargarProveedor()
})
</script>

<template>
  <AppModal :open="true" width="62rem" @close="emit('close')"
            :title="rapida ? 'Compra rápida' : editando ? `Editar compra ${compra.numero}` : 'Orden de compra'">
    <form @submit.prevent="guardar(false)">
      <p v-if="rapida" class="muted intro">Para lo que ya se compró en la plaza o la tienda: entra de una vez al inventario.</p>
      <div class="form-grid">
        <div class="field">
          <label for="cp-prov">Proveedor</label>
          <select id="cp-prov" v-model="form.proveedor_id" class="select">
            <option value="">{{ rapida ? 'Compra de plaza (sin proveedor fijo)' : 'Sin proveedor registrado' }}</option>
            <option v-for="p in activos" :key="p.id" :value="p.id">{{ p.nombre }}</option>
          </select>
        </div>
        <div v-if="!form.proveedor_id" class="field">
          <label for="cp-lugar">¿Dónde se compró?</label>
          <input id="cp-lugar" v-model="form.proveedor_nombre" class="input" maxlength="100" placeholder="Plaza de mercado, tienda de la esquina…">
        </div>
        <div class="field">
          <label for="cp-pago">Forma de pago</label>
          <select id="cp-pago" v-model="form.forma_pago" class="select">
            <option value="contado">Contado</option>
            <option value="credito">Crédito</option>
            <option v-if="auth.can('caja.movimientos')" value="caja">Pagada con dinero de la caja</option>
          </select>
          <span v-if="form.forma_pago === 'caja'" class="hint">Queda como gasto del turno de caja {{ rapida ? 'al registrarla' : 'al recibirla' }}.</span>
        </div>
        <div class="field">
          <label for="cp-fecha">Fecha</label>
          <input id="cp-fecha" v-model="form.fecha" class="input" type="date" :max="isoDate(new Date())">
        </div>
        <div v-if="!rapida" class="field">
          <label for="cp-entrega">Entrega esperada</label>
          <input id="cp-entrega" v-model="form.entrega_esperada" class="input" type="date">
          <span v-if="proveedor?.dias_entrega" class="hint">Entrega: {{ proveedor.dias_entrega }}</span>
        </div>
        <div v-if="rapida" class="field">
          <label for="cp-factura">Factura o recibo</label>
          <input id="cp-factura" v-model="form.factura_proveedor" class="input" maxlength="40" placeholder="Opcional">
        </div>
      </div>

      <div class="table-wrap espacio">
        <table class="table lineas">
          <thead>
            <tr><th>Insumo</th><th class="num">Cantidad</th><th>En</th>
              <th class="num">{{ rapida ? 'Valor pagado' : 'Precio por unidad' }}</th><th class="num">IVA %</th>
              <th v-if="!rapida" class="num">Total</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="(l, i) in lineas" :key="i">
              <td data-label="Insumo">
                <select v-model="l.insumo_id" class="select insumo" :aria-label="`Insumo ${i + 1}`" required @change="elegirInsumo(l)">
                  <option value="" disabled>Elige un insumo</option>
                  <option v-for="ins in comprables" :key="ins.id" :value="ins.id">
                    {{ ins.nombre }}{{ delProveedor[ins.id] ? ' ★' : '' }}</option>
                </select>
              </td>
              <td class="num" data-label="Cantidad">
                <input v-model.number="l.cantidad" class="input corto" type="number" min="0.001" step="any" inputmode="decimal"
                       :aria-label="`Cantidad ${i + 1}`" required>
              </td>
              <td data-label="En">
                <select v-if="porId[l.insumo_id]?.presentaciones.length" v-model="l.presentacion_id" class="select presentacion"
                        :aria-label="`Presentación ${i + 1}`">
                  <option value="">{{ porId[l.insumo_id].unidad }}</option>
                  <option v-for="p in porId[l.insumo_id].presentaciones" :key="p.id" :value="p.id">{{ p.nombre }}</option>
                </select>
                <span v-else class="muted">{{ porId[l.insumo_id]?.unidad }}</span>
                <small v-if="l.presentacion_id && l.cantidad" class="muted bloque">= {{ formatCantidad(l.cantidad * factor(l), porId[l.insumo_id].unidad) }}</small>
              </td>
              <td class="num" :data-label="rapida ? 'Valor pagado' : 'Precio por unidad'">
                <input v-model.number="l.monto" class="input medio" type="number" min="0" step="any" inputmode="numeric"
                       :aria-label="`${rapida ? 'Valor pagado' : 'Precio'} ${i + 1}`" required>
                <small v-if="!rapida && ultimoPrecio(l) !== null" class="muted bloque">Última vez {{ formatMoney(ultimoPrecio(l)) }}</small>
              </td>
              <td class="num" data-label="IVA %">
                <input v-model.number="l.impuesto_porcentaje" class="input mini" type="number" min="0" max="100" step="any"
                       :aria-label="`IVA ${i + 1}`">
              </td>
              <td v-if="!rapida" class="num nowrap" data-label="Total">{{ formatMoney(totalLinea(l)) }}</td>
              <td>
                <button class="btn btn-secundario btn-sm quitar" type="button" :aria-label="`Quitar insumo ${i + 1}`" title="Quitar"
                        :disabled="lineas.length === 1" @click="lineas.splice(i, 1)">×</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pie-lineas">
        <button class="btn btn-secundario btn-sm" type="button" @click="agregar">Agregar insumo</button>
        <p class="total">Total <strong>{{ formatMoney(total) }}</strong></p>
      </div>
      <p v-if="bajoMinimo" class="aviso">El pedido mínimo de {{ proveedor.nombre }} es {{ formatMoney(proveedor.pedido_minimo) }}.</p>
      <p v-if="Object.keys(delProveedor).length" class="muted">★ Insumos que surte este proveedor.</p>
      <p class="muted">El valor va con impuestos incluidos y es el costo que entra al inventario. El IVA % solo se informa si el proveedor lo discrimina.</p>

      <div class="field espacio">
        <label for="cp-notas">Notas</label>
        <input id="cp-notas" v-model="form.notas" class="input" maxlength="500" placeholder="Calidad, acuerdos con el proveedor…">
      </div>

      <div class="form-actions">
        <button class="btn btn-secundario" type="button" @click="emit('close')">Cancelar</button>
        <template v-if="rapida">
          <button class="btn" type="submit" :disabled="busy || !listo">Registrar y sumar al inventario</button>
        </template>
        <template v-else-if="editando">
          <button class="btn" type="submit" :disabled="busy || !listo">Guardar cambios</button>
        </template>
        <template v-else>
          <button class="btn btn-secundario" type="submit" :disabled="busy || !listo">Guardar borrador</button>
          <button class="btn" type="button" :disabled="busy || !listo" @click="guardar(true)">Guardar como solicitada</button>
        </template>
      </div>
    </form>
  </AppModal>
</template>

<style scoped>
.intro {
  margin-bottom: var(--space-3);
}

.espacio {
  margin-top: var(--space-4);
}

.table .insumo {
  min-width: 11rem;
}

.table .presentacion {
  min-width: 8rem;
}

.corto {
  width: 5rem;
}

.medio {
  width: 7rem;
}

.quitar {
  min-width: 2.75rem;
  font-size: var(--text-lg);
}

.mini {
  width: 4.5rem;
}

.bloque {
  display: block;
}

.nowrap {
  white-space: nowrap;
}

.pie-lineas {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin: var(--space-3) 0;
}

.total {
  font-size: var(--text-lg);
}

.total strong {
  font-variant-numeric: tabular-nums;
}

/* En el celular cada insumo es una tarjeta con sus etiquetas, sin desplazamiento lateral */
@media (max-width: 40rem) {
  .lineas thead {
    display: none;
  }

  .lineas tr {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: var(--space-2) var(--space-3);
    padding: var(--space-3) 0;
    border-bottom: 1px solid var(--linea);
  }

  .lineas td {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    padding: 0;
    border: none;
    text-align: left;
  }

  .lineas td[data-label]::before {
    content: attr(data-label);
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--acero);
  }

  .lineas td:first-child {
    grid-column: 1 / -1;
  }

  .lineas .input,
  .lineas .select,
  .table .insumo,
  .table .presentacion {
    width: 100%;
    min-width: 0;
  }
}

.aviso {
  padding: var(--space-2) var(--space-3);
  border-left: 4px solid var(--estado-pendiente);
  border-radius: var(--radio-sm);
  background: var(--estado-pendiente-suave);
  margin-bottom: var(--space-2);
}
</style>
