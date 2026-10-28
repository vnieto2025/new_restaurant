<script setup>
import { ref, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'
import AppModal from '@/components/AppModal.vue'

const { busy, attempt, quiet } = useAction()

const puntos = ref([])
const form = ref(null)

const TIPOS = { cocina: 'Cocina', bar: 'Bar', otro: 'Otro' }

async function load() {
  puntos.value = (await quiet(() => postData('/punto_produccion/list', { todos: true }))) || []
}

function nuevo() {
  form.value = { nombre: '', tipo: 'cocina', imprime_al_abrir: false, salta_en_proceso: false, tiempo_objetivo: null }
}

function editar(punto) {
  form.value = { ...punto, punto_produccion_id: punto.id }
}

async function guardar() {
  const editando = !!form.value.punto_produccion_id
  const ok = await attempt(() => postData(editando ? '/punto_produccion/update' : '/punto_produccion/create', form.value),
    { success: 'Punto de producción guardado.' })
  if (ok) {
    form.value = null
    load()
  }
}

async function cambiarEstado(punto) {
  await attempt(() => postData('/punto_produccion/change_status', { punto_produccion_id: punto.id, activo: !punto.activo }),
    { success: punto.activo ? 'Punto desactivado.' : 'Punto activado.' })
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Cocina y bar</h1>
        <p>Los lugares donde se prepara. Cada uno tiene su propia pantalla y recibe solo lo suyo.</p>
      </div>
      <button class="btn" type="button" @click="nuevo">Crear punto</button>
    </header>

    <div class="panel table-wrap">
      <table class="table">
        <thead>
          <tr><th>Punto</th><th>Tipo</th><th>Al abrir</th><th>Flujo</th><th>Tiempo objetivo</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="punto in puntos" :key="punto.id" :class="{ muted: !punto.activo }">
            <td><strong>{{ punto.nombre }}</strong><span v-if="!punto.activo"> (inactivo)</span></td>
            <td>{{ TIPOS[punto.tipo] }}</td>
            <td>{{ punto.imprime_al_abrir ? 'Imprime tirilla' : 'No imprime' }}</td>
            <td>{{ punto.salta_en_proceso ? 'Despacha sin "en proceso"' : 'Abrir y despachar' }}</td>
            <td>{{ punto.tiempo_objetivo ? `${punto.tiempo_objetivo} min` : '—' }}</td>
            <td class="actions">
              <button class="btn btn-secundario btn-sm" type="button" @click="editar(punto)">Editar</button>
              <button class="btn btn-secundario btn-sm" type="button" :disabled="busy" @click="cambiarEstado(punto)">
                {{ punto.activo ? 'Desactivar' : 'Activar' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <AppModal :open="!!form" :title="form?.punto_produccion_id ? `Editar ${form.nombre}` : 'Crear punto de producción'"
              @close="form = null">
      <form v-if="form" @submit.prevent="guardar">
        <div class="form-grid">
          <div class="field">
            <label for="p-nombre">Nombre</label>
            <input id="p-nombre" v-model="form.nombre" class="input" required maxlength="60" placeholder="Parrilla, Postres…">
          </div>
          <div class="field">
            <label for="p-tipo">Tipo</label>
            <select id="p-tipo" v-model="form.tipo" class="select">
              <option v-for="(label, value) in TIPOS" :key="value" :value="value">{{ label }}</option>
            </select>
          </div>
          <div class="field">
            <label for="p-tiempo">Tiempo objetivo (minutos)</label>
            <input id="p-tiempo" v-model.number="form.tiempo_objetivo" class="input" type="number" min="1" placeholder="Opcional">
            <span class="hint">Pasado este tiempo la comanda se marca como demorada.</span>
          </div>
        </div>
        <label class="check"><input v-model="form.imprime_al_abrir" type="checkbox"> Imprimir la tirilla al abrir la comanda</label>
        <label class="check"><input v-model="form.salta_en_proceso" type="checkbox"> Despachar sin pasar por "en proceso" (bebidas simples)</label>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="form = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy" :aria-busy="busy">Guardar</button>
        </div>
      </form>
    </AppModal>
  </div>
</template>
