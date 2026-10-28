<script setup>
import { ref, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'
import { formatDate, isoDate } from '@/utils/format'
import AppModal from '@/components/AppModal.vue'

/*
  Impuestos del restaurante (doc 21A, sección 2). Ninguna tasa está fija en el sistema (RG-06):
  se configuran aquí con fecha de inicio, y un cambio de tasa se programa sin tocar las ventas hechas.
*/
const { busy, attempt, quiet } = useAction()

const TIPOS = { consumo: 'Impuesto al consumo', iva: 'IVA', otro: 'Otro' }

const impuestos = ref([])
const cargado = ref(false)
const form = ref(null)
const tarifa = ref(null)

async function load() {
  impuestos.value = (await quiet(() => postData('/impuesto/list', { todos: true }))) || []
  cargado.value = true
}

function nuevo() {
  form.value = { nombre: '', tipo: 'consumo', codigo: '', porcentaje: null, vigente_desde: isoDate(new Date()),
    por_defecto: !impuestos.value.length }
}

function editar(impuesto) {
  form.value = { ...impuesto, impuesto_id: impuesto.id }
}

async function guardar() {
  const editando = !!form.value.impuesto_id
  const ok = await attempt(() => postData(editando ? '/impuesto/update' : '/impuesto/create', form.value),
    { success: editando ? 'Impuesto actualizado.' : 'Impuesto creado.' })
  if (ok) {
    form.value = null
    load()
  }
}

function programar(impuesto) {
  const manana = new Date()
  manana.setDate(manana.getDate() + 1)
  tarifa.value = { impuesto_id: impuesto.id, nombre: impuesto.nombre, porcentaje: impuesto.porcentaje,
    vigente_desde: isoDate(manana), motivo: '' }
}

async function guardarTarifa() {
  const ok = await attempt(() => postData('/impuesto/tarifa', tarifa.value), { success: 'Cambio de tasa programado.' })
  if (ok) {
    tarifa.value = null
    load()
  }
}

async function cambiarEstado(impuesto) {
  await attempt(() => postData('/impuesto/change_status', { impuesto_id: impuesto.id, activo: !impuesto.activo }),
    { success: impuesto.activo ? 'Impuesto desactivado.' : 'Impuesto activado.' })
  load()
}

async function porDefecto(impuesto) {
  await attempt(() => postData('/impuesto/update', { ...impuesto, impuesto_id: impuesto.id, por_defecto: true }),
    { success: `${impuesto.nombre} queda como impuesto por defecto.` })
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Impuestos</h1>
        <p>Los precios de la carta ya incluyen el impuesto; la factura lo desglosa. Confirma las tasas con tu contador.</p>
      </div>
      <button class="btn" type="button" @click="nuevo">Crear impuesto</button>
    </header>

    <p class="explicacion muted">
      Cada producto usa su propio impuesto; si no tiene, el de su categoría; si tampoco, el marcado <strong>por defecto</strong>.
      Se asignan al editar el producto o la categoría.
    </p>

    <div class="panel table-wrap">
      <table class="table">
        <thead><tr><th>Impuesto</th><th>Tipo</th><th class="num">Tasa hoy</th><th>Historial de tasas</th><th></th></tr></thead>
        <tbody>
          <tr v-for="impuesto in impuestos" :key="impuesto.id" :class="{ muted: !impuesto.activo }">
            <td>
              <strong>{{ impuesto.nombre }}</strong>
              <span v-if="impuesto.por_defecto" class="defecto">Por defecto</span>
              <span v-if="!impuesto.activo"> (inactivo)</span>
            </td>
            <td>{{ TIPOS[impuesto.tipo] }}<template v-if="impuesto.codigo"> · código {{ impuesto.codigo }}</template></td>
            <td class="num"><strong>{{ impuesto.porcentaje_texto }}</strong></td>
            <td>
              <ul class="tarifas">
                <li v-for="t in impuesto.tarifas" :key="t.vigente_desde">
                  {{ String(t.porcentaje).replace('.', ',') }} % desde {{ formatDate(t.vigente_desde) }}<template v-if="t.vigente_hasta"> hasta {{ formatDate(t.vigente_hasta) }}</template>
                </li>
              </ul>
            </td>
            <td class="actions">
              <button class="btn btn-secundario btn-sm" type="button" @click="programar(impuesto)">Cambiar tasa</button>
              <button class="btn btn-secundario btn-sm" type="button" @click="editar(impuesto)">Editar</button>
              <button v-if="!impuesto.por_defecto && impuesto.activo" class="btn btn-secundario btn-sm" type="button" :disabled="busy"
                      @click="porDefecto(impuesto)">Usar por defecto</button>
              <button v-if="!impuesto.por_defecto" class="btn btn-secundario btn-sm" type="button" :disabled="busy"
                      @click="cambiarEstado(impuesto)">{{ impuesto.activo ? 'Desactivar' : 'Activar' }}</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="cargado && !impuestos.length" class="empty">
        Aún no hay impuestos: las ventas salen sin impuesto desglosado. Crea el que te indique tu contador.
      </p>
    </div>

    <AppModal :open="!!form" :title="form?.impuesto_id ? `Editar ${form.nombre}` : 'Crear impuesto'" width="32rem" @close="form = null">
      <form v-if="form" @submit.prevent="guardar">
        <div class="form-grid">
          <div class="field"><label for="i-nombre">Nombre</label>
            <input id="i-nombre" v-model="form.nombre" class="input" required maxlength="60" placeholder="Impuesto al consumo"></div>
          <div class="field"><label for="i-tipo">Tipo</label>
            <select id="i-tipo" v-model="form.tipo" class="select">
              <option v-for="(label, valor) in TIPOS" :key="valor" :value="valor">{{ label }}</option>
            </select></div>
          <div class="field"><label for="i-codigo">Código ante el proveedor</label>
            <input id="i-codigo" v-model="form.codigo" class="input" maxlength="10" placeholder="Opcional"></div>
          <template v-if="!form.impuesto_id">
            <div class="field"><label for="i-porc">Tasa (%)</label>
              <input id="i-porc" v-model="form.porcentaje" class="input" type="number" min="0" max="99.999" step="0.001" required inputmode="decimal"></div>
            <div class="field"><label for="i-desde">Vigente desde</label>
              <input id="i-desde" v-model="form.vigente_desde" class="input" type="date" required></div>
          </template>
        </div>
        <p v-if="form.impuesto_id" class="muted espacio">La tasa no se edita: usa «Cambiar tasa» para programar una nueva desde una fecha.</p>
        <label v-if="!form.impuesto_id" class="check espacio"><input v-model="form.por_defecto" type="checkbox"> Usarlo por defecto en los productos sin impuesto propio</label>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="form = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy">Guardar</button>
        </div>
      </form>
    </AppModal>

    <AppModal :open="!!tarifa" :title="`Cambiar tasa de ${tarifa?.nombre || ''}`" width="28rem" @close="tarifa = null">
      <form v-if="tarifa" @submit.prevent="guardarTarifa">
        <div class="form-grid">
          <div class="field"><label for="t-porc">Nueva tasa (%)</label>
            <input id="t-porc" v-model="tarifa.porcentaje" class="input" type="number" min="0" max="99.999" step="0.001" required inputmode="decimal"></div>
          <div class="field"><label for="t-desde">Desde</label>
            <input id="t-desde" v-model="tarifa.vigente_desde" class="input" type="date" :min="isoDate(new Date())" required></div>
        </div>
        <div class="field espacio"><label for="t-motivo">Motivo</label>
          <input id="t-motivo" v-model="tarifa.motivo" class="input" maxlength="200" placeholder="Reforma tributaria, indicación del contador…"></div>
        <p class="muted espacio">Las ventas anteriores conservan la tasa con la que se hicieron. Queda en la auditoría.</p>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="tarifa = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy">Programar</button>
        </div>
      </form>
    </AppModal>
  </div>
</template>

<style scoped>
.explicacion {
  margin-bottom: var(--space-4);
  max-width: 60rem;
}

.defecto {
  display: inline-block;
  white-space: nowrap;
  margin-left: var(--space-2);
  padding: 0.1em 0.6em;
  border-radius: 999px;
  background: var(--accion-suave);
  font-size: var(--text-sm);
  font-weight: 600;
}

.tarifas {
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: var(--text-sm);
}

.espacio {
  margin-top: var(--space-3);
}
</style>
