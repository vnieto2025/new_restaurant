<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'
import { formatDateTime, formatTime } from '@/utils/format'
import AppModal from '@/components/AppModal.vue'

/*
  Tablets de zona y pantallas de cocina autorizadas (doc 08, sección 2).
  Se crea el dispositivo, se escribe el código en la tablet y desde ahí cada persona entra con su PIN.
*/
const { busy, attempt, quiet } = useAction()

const dispositivos = ref([])
const zonas = ref([])
const puntos = ref([])
const cargado = ref(false)
const form = ref(null)
const codigo = ref(null)

const destinos = computed(() => ({
  ...Object.fromEntries(zonas.value.map((z) => [`z${z.id}`, z.nombre])),
  ...Object.fromEntries(puntos.value.map((p) => [`p${p.id}`, p.nombre])),
}))

async function load() {
  const [d, z, p] = await Promise.all([
    quiet(() => postData('/dispositivo/list')),
    quiet(() => postData('/zona/list')),
    quiet(() => postData('/punto_produccion/list')),
  ])
  dispositivos.value = d || []
  zonas.value = (z || []).filter((zona) => !zona.es_mostrador)
  puntos.value = p || []
  cargado.value = true
}

function destino(d) {
  return d.zona_id ? `Tablet de ${destinos.value[`z${d.zona_id}`] || 'zona'}` : `Pantalla de ${destinos.value[`p${d.punto_produccion_id}`] || 'producción'}`
}

function nuevo() {
  form.value = { nombre: '', tipo: 'zona', zona_id: zonas.value[0]?.id, punto_produccion_id: puntos.value[0]?.id }
}

async function crear() {
  const data = await attempt(() => postData('/dispositivo/create', form.value))
  if (data) {
    form.value = null
    codigo.value = data
    load()
  }
}

async function nuevoCodigo(d) {
  const data = await attempt(() => postData('/dispositivo/codigo', { dispositivo_id: d.id }))
  if (data) {
    codigo.value = data
    load()
  }
}

async function desautorizar(d) {
  await attempt(() => postData('/dispositivo/change_status', { dispositivo_id: d.id, activo: false }),
    { success: `${d.nombre} desautorizado. Sus sesiones se cerraron.` })
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Dispositivos</h1>
        <p>Tablets de zona y pantallas de cocina. En ellas cada persona entra con su PIN (se asigna en Personal).</p>
      </div>
      <button class="btn" type="button" @click="nuevo">Autorizar dispositivo</button>
    </header>

    <p v-if="!cargado" class="empty">Cargando…</p>
    <div v-else-if="!dispositivos.length" class="empty">
      <p>Aún no hay dispositivos. Autoriza la tablet de cada zona y la pantalla de la cocina.</p>
      <button class="btn" type="button" @click="nuevo">Autorizar el primero</button>
    </div>
    <div v-else class="panel table-wrap">
      <table class="table">
        <thead><tr><th>Dispositivo</th><th>Uso</th><th>Estado</th><th>Último uso</th><th></th></tr></thead>
        <tbody>
          <tr v-for="d in dispositivos" :key="d.id" :class="{ muted: !d.activo }">
            <td><strong>{{ d.nombre }}</strong></td>
            <td>{{ destino(d) }}</td>
            <td>{{ !d.activo ? 'Desautorizado' : d.emparejado ? 'Autorizado' : d.codigo_pendiente ? 'Esperando código' : 'Sin emparejar' }}</td>
            <td>{{ d.ultimo_uso ? formatDateTime(d.ultimo_uso) : '—' }}</td>
            <td class="actions">
              <button class="btn btn-secundario btn-sm" type="button" :disabled="busy" @click="nuevoCodigo(d)">
                {{ d.emparejado ? 'Cambiar de tablet' : 'Nuevo código' }}
              </button>
              <button v-if="d.activo" class="btn btn-secundario btn-sm" type="button" :disabled="busy" @click="desautorizar(d)">Desautorizar</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <AppModal :open="!!form" title="Autorizar dispositivo" width="30rem" @close="form = null">
      <form v-if="form" @submit.prevent="crear">
        <div class="form-grid">
          <div class="field">
            <label for="d-nombre">Nombre</label>
            <input id="d-nombre" v-model="form.nombre" class="input" required maxlength="60" placeholder="Tablet Salón">
          </div>
          <div class="field">
            <label for="d-tipo">Se usa como</label>
            <select id="d-tipo" v-model="form.tipo" class="select">
              <option value="zona">Tablet de meseros</option>
              <option value="produccion">Pantalla de cocina o bar</option>
            </select>
          </div>
          <div v-if="form.tipo === 'zona'" class="field">
            <label for="d-zona">Zona</label>
            <select id="d-zona" v-model="form.zona_id" class="select">
              <option v-for="z in zonas" :key="z.id" :value="z.id">{{ z.nombre }}</option>
            </select>
          </div>
          <div v-else class="field">
            <label for="d-punto">Punto de producción</label>
            <select id="d-punto" v-model="form.punto_produccion_id" class="select">
              <option v-for="p in puntos" :key="p.id" :value="p.id">{{ p.nombre }}</option>
            </select>
          </div>
        </div>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="form = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy">Crear y ver código</button>
        </div>
      </form>
    </AppModal>

    <AppModal :open="!!codigo" :title="`Código para ${codigo?.nombre}`" width="28rem" @close="codigo = null">
      <div v-if="codigo" class="codigo">
        <p>En la tablet abre <strong>/dispositivo</strong> en el navegador y escribe:</p>
        <p class="numero"><span class="visually-hidden">Código de emparejamiento: </span>{{ codigo.codigo }}</p>
        <p class="muted">Sirve una sola vez y vence a las {{ formatTime(codigo.codigo_expira) }}</p>
      </div>
    </AppModal>
  </div>
</template>

<style scoped>
.codigo {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  text-align: center;
}

.numero {
  font-family: var(--font-papel);
  font-size: 3rem;
  font-weight: 600;
  letter-spacing: 0.3em;
}
</style>
