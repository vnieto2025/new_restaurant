<script setup>
import { ref, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'
import { useAuthStore } from '@/stores/auth'
import AppModal from '@/components/AppModal.vue'

const { busy, attempt, quiet } = useAction()
const auth = useAuthStore()

const categorias = ref([])
const puntos = ref([])
const impuestos = ref([])
const form = ref(null)
const cargado = ref(false)

async function load() {
  categorias.value = (await quiet(() => postData('/categoria/list', { todas: true }))) || []
  // Los puntos de producción son del módulo de pedidos (plan Gestión sin cocina)
  if (auth.modulos.has('pedidos')) puntos.value = (await quiet(() => postData('/punto_produccion/list'))) || []
  impuestos.value = (await quiet(() => postData('/impuesto/list'))) || []
  cargado.value = true
}

function nueva() {
  form.value = { nombre: '', orden: categorias.value.length + 1, punto_produccion_id: null, impuesto_id: null }
}

function editar(categoria) {
  form.value = { ...categoria, categoria_id: categoria.id }
}

async function guardar() {
  const editando = !!form.value.categoria_id
  const ok = await attempt(() => postData(editando ? '/categoria/update' : '/categoria/create', form.value),
    { success: 'Categoría guardada.' })
  if (ok) {
    form.value = null
    load()
  }
}

async function cambiarEstado(categoria) {
  await attempt(() => postData('/categoria/change_status', { categoria_id: categoria.id, activo: !categoria.activo }),
    { success: categoria.activo ? 'Categoría oculta de la carta.' : 'Categoría visible de nuevo.' })
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Categorías</h1>
        <p>Agrupan la carta. Si una categoría tiene punto de producción, sus productos van allí.</p>
      </div>
      <button class="btn" type="button" @click="nueva">Crear categoría</button>
    </header>

    <div class="panel table-wrap">
      <table class="table">
        <thead><tr><th>Orden</th><th>Categoría</th><th>Se prepara en</th><th class="num">Productos</th><th></th></tr></thead>
        <tbody>
          <tr v-for="categoria in categorias" :key="categoria.id" :class="{ muted: !categoria.activo }">
            <td>{{ categoria.orden }}</td>
            <td><strong>{{ categoria.nombre }}</strong><span v-if="!categoria.activo"> (oculta)</span></td>
            <td>{{ categoria.punto_produccion || 'El de la zona' }}</td>
            <td class="num">{{ categoria.productos }}</td>
            <td class="actions">
              <button class="btn btn-secundario btn-sm" type="button" @click="editar(categoria)">Editar</button>
              <button class="btn btn-secundario btn-sm" type="button" :disabled="busy" @click="cambiarEstado(categoria)">
                {{ categoria.activo ? 'Ocultar' : 'Mostrar' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="cargado && !categorias.length" class="empty">Crea la primera categoría: Entradas, Platos fuertes, Bebidas…</p>
    </div>

    <AppModal :open="!!form" :title="form?.categoria_id ? `Editar ${form.nombre}` : 'Crear categoría'" width="28rem"
              @close="form = null">
      <form v-if="form" @submit.prevent="guardar">
        <div class="form-grid">
          <div class="field">
            <label for="c-nombre">Nombre</label>
            <input id="c-nombre" v-model="form.nombre" class="input" required maxlength="60">
          </div>
          <div class="field">
            <label for="c-orden">Orden en la carta</label>
            <input id="c-orden" v-model.number="form.orden" class="input" type="number" min="0">
          </div>
          <div class="field">
            <label for="c-punto">Se prepara en</label>
            <select id="c-punto" v-model="form.punto_produccion_id" class="select">
              <option :value="null">El punto de la zona</option>
              <option v-for="punto in puntos" :key="punto.id" :value="punto.id">{{ punto.nombre }}</option>
            </select>
          </div>
          <div v-if="impuestos.length" class="field">
            <label for="c-impuesto">Impuesto de sus productos</label>
            <select id="c-impuesto" v-model="form.impuesto_id" class="select">
              <option :value="null">El impuesto por defecto</option>
              <option v-for="imp in impuestos" :key="imp.id" :value="imp.id">{{ imp.nombre }} · {{ imp.porcentaje_texto }}</option>
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
