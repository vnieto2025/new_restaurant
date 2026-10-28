<script setup>
import { ref, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'
import AppModal from '@/components/AppModal.vue'
import HorarioEditor from '@/components/HorarioEditor.vue'

const { busy, attempt, quiet } = useAction()

const zonas = ref([])
const cartas = ref([])
const puntos = ref([])
const form = ref(null)
const horario = ref(null)

const MODOS = {
  aprobacion: 'Con aprobación del mesero',
  libre: 'Libre: va directo a cocina',
}

async function load() {
  const [z, c, p] = await Promise.all([
    quiet(() => postData('/zona/list', { todas: true })),
    quiet(() => postData('/carta/list')),
    quiet(() => postData('/punto_produccion/list')),
  ])
  zonas.value = z || []
  cartas.value = c || []
  puntos.value = p || []
}

function nueva() {
  form.value = { nombre: '', codigo: '', orden: zonas.value.length + 1, carta_id: cartas.value[0]?.id || null,
    punto_produccion_id: puntos.value[0]?.id || null, modo_qr: 'aprobacion' }
}

function editar(zona) {
  form.value = { ...zona, zona_id: zona.id }
}

async function guardar() {
  const editando = !!form.value.zona_id
  const ok = await attempt(() => postData(editando ? '/zona/update' : '/zona/create', form.value),
    { success: editando ? 'Zona actualizada.' : 'Zona creada.' })
  if (ok) {
    form.value = null
    load()
  }
}

async function cambiarEstado(zona) {
  await attempt(() => postData('/zona/change_status', { zona_id: zona.id, activo: !zona.activo }),
    { success: zona.activo ? 'Zona desactivada.' : 'Zona activada.' })
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Zonas</h1>
        <p>Cada zona tiene su carta, su punto de producción y su forma de recibir pedidos por QR.</p>
      </div>
      <button class="btn" type="button" @click="nueva">Crear zona</button>
    </header>

    <div class="panel table-wrap">
      <table class="table">
        <thead>
          <tr><th>Zona</th><th>Carta</th><th>Prepara</th><th>Pedidos por QR</th><th class="num">Mesas</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="zona in zonas" :key="zona.id" :class="{ muted: !zona.activo }">
            <td><strong>{{ zona.nombre }}</strong><span v-if="zona.es_mostrador" class="muted"> · mostrador</span><span v-if="!zona.activo"> (inactiva)</span></td>
            <td>{{ zona.carta || 'Sin carta' }}</td>
            <td>{{ zona.punto_produccion || 'Despacho directo' }}</td>
            <td>{{ MODOS[zona.modo_qr] }}</td>
            <td class="num">{{ zona.es_mostrador ? '—' : zona.mesas }}</td>
            <td class="actions">
              <button class="btn btn-secundario btn-sm" type="button" @click="editar(zona)">Editar</button>
              <button class="btn btn-secundario btn-sm" type="button" @click="horario = zona">Horario</button>
              <button v-if="!zona.es_mostrador" class="btn btn-secundario btn-sm" type="button" :disabled="busy"
                      @click="cambiarEstado(zona)">{{ zona.activo ? 'Desactivar' : 'Activar' }}</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <AppModal :open="!!horario" :title="`Horario de ${horario?.nombre}`" width="44rem" @close="horario = null">
      <template v-if="horario">
        <h3 class="sub">Cuándo recibe órdenes</h3>
        <HorarioEditor tipo="atencion" :zona-id="horario.id" />
        <h3 class="sub">Carta según la hora</h3>
        <p class="muted">Por ejemplo, desayunos hasta las 11:00. Fuera de estas franjas se usa {{ horario.carta || 'su carta' }}.</p>
        <HorarioEditor tipo="carta" :zona-id="horario.id" :cartas="cartas" />
      </template>
    </AppModal>

    <AppModal :open="!!form" :title="form?.zona_id ? `Editar ${form.nombre}` : 'Crear zona'" @close="form = null">
      <form v-if="form" @submit.prevent="guardar">
        <div class="form-grid">
          <div class="field">
            <label for="z-nombre">Nombre</label>
            <input id="z-nombre" v-model="form.nombre" class="input" required maxlength="60" placeholder="Terraza, Bar…">
          </div>
          <div class="field">
            <label for="z-orden">Orden en pantalla</label>
            <input id="z-orden" v-model.number="form.orden" class="input" type="number" min="0">
          </div>
          <div class="field">
            <label for="z-carta">Carta</label>
            <select id="z-carta" v-model="form.carta_id" class="select">
              <option :value="null">Sin carta</option>
              <option v-for="carta in cartas" :key="carta.id" :value="carta.id">{{ carta.nombre }}</option>
            </select>
          </div>
          <div class="field">
            <label for="z-punto">Prepara por defecto</label>
            <select id="z-punto" v-model="form.punto_produccion_id" class="select">
              <option :value="null">Nadie (despacho directo)</option>
              <option v-for="punto in puntos" :key="punto.id" :value="punto.id">{{ punto.nombre }}</option>
            </select>
            <span class="hint">Se usa para los productos que no tienen punto propio.</span>
          </div>
          <div class="field">
            <label for="z-modo">Pedidos por QR de mesa</label>
            <select id="z-modo" v-model="form.modo_qr" class="select">
              <option v-for="(label, value) in MODOS" :key="value" :value="value">{{ label }}</option>
            </select>
          </div>
        </div>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="form = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy" :aria-busy="busy">Guardar</button>
        </div>
      </form>
    </AppModal>
  </div>
</template>

<style scoped>
.sub {
  margin: var(--space-4) 0 var(--space-2);
  font-size: var(--text-lg);
}
</style>
