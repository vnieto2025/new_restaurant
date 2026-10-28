<script setup>
import { ref, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'
import { formatMoney } from '@/utils/format'
import AppModal from '@/components/AppModal.vue'

// Grupos de opciones que se reutilizan en varios productos: término, adicionales, quitar ingredientes
const { busy, attempt, quiet } = useAction()

const grupos = ref([])
const cargado = ref(false)
const form = ref(null)

async function load() {
  grupos.value = (await quiet(() => postData('/modificador/list', { todos: true }))) || []
  cargado.value = true
}

function nuevo() {
  form.value = { nombre: '', minimo: 0, maximo: 1, opciones: [{ nombre: '', precio_extra: 0 }] }
}

function editar(grupo) {
  form.value = { ...grupo, grupo_id: grupo.id, opciones: grupo.opciones.map((o) => ({ ...o })) }
}

function agregarOpcion() {
  form.value.opciones.push({ nombre: '', precio_extra: 0 })
}

function quitarOpcion(index) {
  form.value.opciones.splice(index, 1)
}

function regla(grupo) {
  if (grupo.minimo > 0) return grupo.minimo === grupo.maximo ? `Obligatorio: elegir ${grupo.minimo}` : `Obligatorio: de ${grupo.minimo} a ${grupo.maximo}`
  return grupo.maximo === 1 ? 'Opcional: una' : `Opcional: hasta ${grupo.maximo}`
}

async function guardar() {
  const editando = !!form.value.grupo_id
  const body = { ...form.value, opciones: form.value.opciones.filter((o) => o.nombre.trim()) }
  const ok = await attempt(() => postData(editando ? '/modificador/update' : '/modificador/create', body),
    { success: 'Grupo guardado. Asígnalo a los productos desde Productos.' })
  if (ok) {
    form.value = null
    load()
  }
}

async function cambiarEstado(grupo) {
  await attempt(() => postData('/modificador/change_status', { grupo_id: grupo.id, activo: !grupo.activo }),
    { success: grupo.activo ? 'Grupo desactivado.' : 'Grupo activado.' })
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Modificadores</h1>
        <p>Opciones que el cliente o el mesero eligen al pedir: término, adicionales, quitar ingredientes.</p>
      </div>
      <button class="btn" type="button" @click="nuevo">Crear grupo</button>
    </header>

    <p v-if="!cargado" class="empty">Cargando…</p>
    <div v-else-if="!grupos.length" class="empty">
      <p>Aún no hay grupos. Un grupo reúne opciones como "Queso extra" o "Sin cebolla".</p>
      <button class="btn" type="button" @click="nuevo">Crear el primero</button>
    </div>

    <div v-else class="panel table-wrap">
      <table class="table">
        <thead><tr><th>Grupo</th><th>Regla</th><th>Opciones</th><th class="num">Productos</th><th></th></tr></thead>
        <tbody>
          <tr v-for="grupo in grupos" :key="grupo.id" :class="{ muted: !grupo.activo }">
            <td><strong>{{ grupo.nombre }}</strong><span v-if="!grupo.activo"> (inactivo)</span></td>
            <td>{{ regla(grupo) }}</td>
            <td>{{ grupo.opciones.map((o) => o.precio_extra ? `${o.nombre} (+${formatMoney(o.precio_extra)})` : o.nombre).join(', ') }}</td>
            <td class="num">{{ grupo.productos }}</td>
            <td class="actions">
              <button class="btn btn-secundario btn-sm" type="button" @click="editar(grupo)">Editar</button>
              <button class="btn btn-secundario btn-sm" type="button" :disabled="busy" @click="cambiarEstado(grupo)">
                {{ grupo.activo ? 'Desactivar' : 'Activar' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <AppModal :open="!!form" :title="form?.grupo_id ? `Editar ${form.nombre}` : 'Crear grupo de modificadores'" width="36rem"
              @close="form = null">
      <form v-if="form" @submit.prevent="guardar">
        <div class="form-grid">
          <div class="field">
            <label for="g-nombre">Nombre del grupo</label>
            <input id="g-nombre" v-model="form.nombre" class="input" required maxlength="60" placeholder="Adicionales">
          </div>
          <div class="field">
            <label for="g-min">Mínimo a elegir</label>
            <input id="g-min" v-model.number="form.minimo" class="input" type="number" min="0">
            <span class="hint">Pon 1 si es obligatorio, como el término de la carne.</span>
          </div>
          <div class="field">
            <label for="g-max">Máximo a elegir</label>
            <input id="g-max" v-model.number="form.maximo" class="input" type="number" min="1">
          </div>
        </div>

        <fieldset class="opciones">
          <legend>Opciones</legend>
          <div v-for="(opcion, index) in form.opciones" :key="index" class="opcion">
            <input v-model="opcion.nombre" class="input" maxlength="60" placeholder="Nombre" :aria-label="`Opción ${index + 1}`">
            <input v-model.number="opcion.precio_extra" class="input precio" type="number" min="0" step="100"
                   :aria-label="`Precio extra de la opción ${index + 1}`" placeholder="0">
            <button class="btn btn-secundario btn-sm" type="button" :disabled="form.opciones.length === 1"
                    :aria-label="`Quitar opción ${index + 1}`" @click="quitarOpcion(index)">Quitar</button>
          </div>
          <button class="btn btn-secundario btn-sm" type="button" @click="agregarOpcion">Agregar opción</button>
          <p class="hint">El precio extra se suma al del producto. Déjalo en 0 si no cambia el precio.</p>
        </fieldset>

        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="form = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy" :aria-busy="busy">Guardar</button>
        </div>
      </form>
    </AppModal>
  </div>
</template>

<style scoped>
.opciones {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: var(--space-4) 0 0;
  padding: var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
}

.opciones legend {
  font-weight: 600;
  font-size: var(--text-sm);
}

.opcion {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 7rem auto;
  gap: var(--space-2);
  align-items: center;
}

.opciones > .btn {
  align-self: flex-start;
}

.hint {
  color: var(--acero);
  font-size: var(--text-sm);
}
</style>
