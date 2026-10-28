<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'
import { formatMoney } from '@/utils/format'
import AppModal from '@/components/AppModal.vue'

// Una carta es lo que ofrece una zona: el bar puede tener solo bebidas (doc 11)
const { busy, attempt, quiet } = useAction()

const cartas = ref([])
const productos = ref([])
const form = ref(null)

const porCategoria = computed(() => {
  const grupos = {}
  for (const producto of productos.value) (grupos[producto.categoria] ||= []).push(producto)
  return Object.entries(grupos)
})

async function load() {
  cartas.value = (await quiet(() => postData('/carta/list', { todas: true }))) || []
  productos.value = (await quiet(() => postData('/producto/list'))) || []
}

function nueva() {
  form.value = { nombre: '', productos: [] }
}

async function editar(carta) {
  const detalle = await attempt(() => postData('/carta/get', { carta_id: carta.id }))
  if (detalle) form.value = { carta_id: carta.id, nombre: detalle.nombre, productos: detalle.productos }
}

function toggleCategoria(lista) {
  const ids = lista.map((p) => p.id)
  const todos = ids.every((id) => form.value.productos.includes(id))
  form.value.productos = todos
    ? form.value.productos.filter((id) => !ids.includes(id))
    : [...new Set([...form.value.productos, ...ids])]
}

async function guardar() {
  const editando = !!form.value.carta_id
  const ok = await attempt(() => postData(editando ? '/carta/update' : '/carta/create', form.value), { success: 'Carta guardada.' })
  if (ok) {
    form.value = null
    load()
  }
}

async function cambiarEstado(carta) {
  await attempt(() => postData('/carta/change_status', { carta_id: carta.id, activo: !carta.activo }),
    { success: carta.activo ? 'Carta desactivada.' : 'Carta activada.' })
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Cartas</h1>
        <p>Asigna una carta a cada zona desde Zonas. Los productos nuevos entran en todas las cartas.</p>
      </div>
      <button class="btn" type="button" @click="nueva">Crear carta</button>
    </header>

    <div class="panel table-wrap">
      <table class="table">
        <thead><tr><th>Carta</th><th class="num">Productos</th><th>Zonas que la usan</th><th></th></tr></thead>
        <tbody>
          <tr v-for="carta in cartas" :key="carta.id" :class="{ muted: !carta.activo }">
            <td><strong>{{ carta.nombre }}</strong><span v-if="!carta.activo"> (inactiva)</span></td>
            <td class="num">{{ carta.productos_total }}</td>
            <td>{{ carta.zonas.join(', ') || 'Ninguna' }}</td>
            <td class="actions">
              <button class="btn btn-secundario btn-sm" type="button" @click="editar(carta)">Elegir productos</button>
              <button class="btn btn-secundario btn-sm" type="button" :disabled="busy" @click="cambiarEstado(carta)">
                {{ carta.activo ? 'Desactivar' : 'Activar' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <AppModal :open="!!form" :title="form?.carta_id ? `Carta: ${form.nombre}` : 'Crear carta'" width="40rem" @close="form = null">
      <form v-if="form" @submit.prevent="guardar">
        <div class="field">
          <label for="ca-nombre">Nombre</label>
          <input id="ca-nombre" v-model="form.nombre" class="input" required maxlength="80" placeholder="Bar, Almuerzos…">
        </div>
        <p class="muted contador">{{ form.productos.length }} productos elegidos</p>
        <div class="grupos">
          <fieldset v-for="[categoria, lista] in porCategoria" :key="categoria" class="grupo">
            <legend>
              <button type="button" class="todos" @click="toggleCategoria(lista)">{{ categoria }}</button>
            </legend>
            <label v-for="producto in lista" :key="producto.id" class="check">
              <input v-model="form.productos" type="checkbox" :value="producto.id">
              <span>{{ producto.nombre }}</span><span class="muted">{{ formatMoney(producto.precio) }}</span>
            </label>
          </fieldset>
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
.contador {
  margin: var(--space-3) 0;
}

.grupos {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  max-height: 50dvh;
  overflow-y: auto;
}

.grupo {
  margin: 0;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
}

.todos {
  border: none;
  background: none;
  font-weight: 700;
  text-decoration: underline;
  cursor: pointer;
}

.check span:first-of-type {
  flex: 1;
}
</style>
