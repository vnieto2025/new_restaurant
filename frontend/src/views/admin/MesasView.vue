<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'
import AppModal from '@/components/AppModal.vue'

const { busy, attempt, quiet } = useAction()

const zonas = ref([])
const mesas = ref([])
const zonaId = ref(null)
const form = ref(null)
const lote = ref(null)
const cargado = ref(false)

const zonasMesa = computed(() => zonas.value.filter((z) => !z.es_mostrador))
const visibles = computed(() => mesas.value.filter((m) => !zonaId.value || m.zona_id === zonaId.value))
const nombreZona = (id) => zonas.value.find((z) => z.id === id)?.nombre

async function load() {
  zonas.value = (await quiet(() => postData('/zona/list', { todas: true }))) || []
  mesas.value = (await quiet(() => postData('/mesa/list', { todas: true }))) || []
  if (!zonaId.value) zonaId.value = zonasMesa.value[0]?.id || null
  cargado.value = true
}

function nueva() {
  form.value = { zona_id: zonaId.value, nombre: '', capacidad: null }
}

function editar(mesa) {
  form.value = { mesa_id: mesa.id, zona_id: mesa.zona_id, nombre: mesa.nombre, capacidad: mesa.capacidad }
}

async function guardar() {
  const editando = !!form.value.mesa_id
  const ok = await attempt(() => postData(editando ? '/mesa/update' : '/mesa/create', form.value),
    { success: editando ? 'Mesa actualizada.' : 'Mesa creada con su QR.' })
  if (ok) {
    form.value = null
    load()
  }
}

async function crearLote() {
  const ok = await attempt(() => postData('/mesa/create_lote', lote.value), { success: (r) => `${r.creadas} mesas creadas con su QR.` })
  if (ok) {
    lote.value = null
    load()
  }
}

async function cambiar(mesa, campo) {
  const body = { mesa_id: mesa.id, [campo]: campo === 'activo' ? !mesa.activo : !mesa.bloqueada }
  await attempt(() => postData('/mesa/change_status', body), { success: 'Mesa actualizada.' })
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Mesas</h1>
        <p>Cada mesa nueva recibe su código QR automáticamente.</p>
      </div>
      <div class="actions">
        <button class="btn btn-secundario" type="button" :disabled="!zonasMesa.length"
                @click="lote = { zona_id: zonaId, desde: 1, hasta: 10, prefijo: 'Mesa' }">Crear varias</button>
        <button class="btn" type="button" :disabled="!zonasMesa.length" @click="nueva">Crear mesa</button>
      </div>
    </header>

    <div class="filtro">
      <button v-for="zona in zonasMesa" :key="zona.id" type="button" class="btn btn-secundario btn-sm"
              :aria-pressed="zonaId === zona.id" @click="zonaId = zona.id">{{ zona.nombre }}</button>
    </div>

    <div class="panel table-wrap">
      <table class="table">
        <thead><tr><th>Mesa</th><th>Zona</th><th>Capacidad</th><th>Estado</th><th></th></tr></thead>
        <tbody>
          <tr v-for="mesa in visibles" :key="mesa.id">
            <td><strong>{{ mesa.nombre }}</strong></td>
            <td>{{ nombreZona(mesa.zona_id) }}</td>
            <td>{{ mesa.capacidad || '—' }}</td>
            <td>{{ !mesa.activo ? 'Inactiva' : mesa.bloqueada ? 'Bloqueada' : mesa.estado === 'libre' ? 'Libre' : 'En uso' }}</td>
            <td class="actions">
              <button class="btn btn-secundario btn-sm" type="button" @click="editar(mesa)">Editar</button>
              <button class="btn btn-secundario btn-sm" type="button" :disabled="busy" @click="cambiar(mesa, 'bloqueada')">
                {{ mesa.bloqueada ? 'Desbloquear' : 'Bloquear' }}
              </button>
              <button class="btn btn-secundario btn-sm" type="button" :disabled="busy" @click="cambiar(mesa, 'activo')">
                {{ mesa.activo ? 'Desactivar' : 'Activar' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!cargado" class="empty">Cargando mesas…</p>
      <div v-else-if="!visibles.length" class="empty">
        <p>Aún no hay mesas en esta zona.</p>
        <button class="btn" type="button" @click="lote = { zona_id: zonaId, desde: 1, hasta: 10, prefijo: 'Mesa' }">Crear mesas 1 a 10</button>
      </div>
    </div>

    <AppModal :open="!!form" :title="form?.mesa_id ? `Editar ${form.nombre}` : 'Crear mesa'" width="28rem" @close="form = null">
      <form v-if="form" @submit.prevent="guardar">
        <div class="form-grid">
          <div class="field">
            <label for="m-nombre">Nombre</label>
            <input id="m-nombre" v-model="form.nombre" class="input" required maxlength="40" placeholder="Mesa 5, Barra 2…">
          </div>
          <div class="field">
            <label for="m-zona">Zona</label>
            <select id="m-zona" v-model="form.zona_id" class="select">
              <option v-for="zona in zonasMesa" :key="zona.id" :value="zona.id">{{ zona.nombre }}</option>
            </select>
          </div>
          <div class="field">
            <label for="m-cap">Capacidad</label>
            <input id="m-cap" v-model.number="form.capacidad" class="input" type="number" min="1" placeholder="Opcional">
          </div>
        </div>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="form = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy" :aria-busy="busy">Guardar</button>
        </div>
      </form>
    </AppModal>

    <AppModal :open="!!lote" title="Crear varias mesas" width="28rem" @close="lote = null">
      <form v-if="lote" @submit.prevent="crearLote">
        <div class="form-grid">
          <div class="field">
            <label for="l-zona">Zona</label>
            <select id="l-zona" v-model="lote.zona_id" class="select">
              <option v-for="zona in zonasMesa" :key="zona.id" :value="zona.id">{{ zona.nombre }}</option>
            </select>
          </div>
          <div class="field">
            <label for="l-prefijo">Nombre base</label>
            <input id="l-prefijo" v-model="lote.prefijo" class="input" maxlength="30">
          </div>
          <div class="field">
            <label for="l-desde">Desde</label>
            <input id="l-desde" v-model.number="lote.desde" class="input" type="number" min="1" required>
          </div>
          <div class="field">
            <label for="l-hasta">Hasta</label>
            <input id="l-hasta" v-model.number="lote.hasta" class="input" type="number" min="1" required>
          </div>
        </div>
        <p class="muted vista">Se crearán: {{ lote.prefijo }} {{ lote.desde }} a {{ lote.prefijo }} {{ lote.hasta }}. Las que ya existan se omiten.</p>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="lote = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy" :aria-busy="busy">Crear mesas</button>
        </div>
      </form>
    </AppModal>
  </div>
</template>

<style scoped>
.filtro {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.filtro [aria-pressed='true'] {
  background: var(--tinta);
  color: #fff;
  border-color: var(--tinta);
}

.vista {
  margin-top: var(--space-4);
}
</style>
