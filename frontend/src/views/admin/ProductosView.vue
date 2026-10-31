<script setup>
import { ref, computed, onMounted } from 'vue'
import { post, postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { formatMoney } from '@/utils/format'
import AppModal from '@/components/AppModal.vue'
import ImportarProductos from '@/components/ImportarProductos.vue'

const auth = useAuthStore()
const { busy, attempt, quiet } = useAction()

const productos = ref([])
const categorias = ref([])
const puntos = ref([])
const cartas = ref([])
const grupos = ref([])
const impuestos = ref([])
const buscar = ref('')
const categoriaId = ref('')
const form = ref(null)
const cargado = ref(false)
const importando = ref(false)
const copia = ref(null)
const otrasSedes = computed(() => (auth.roles.includes('admin_empresa') ? auth.restaurantes.filter((r) => r.id !== auth.restaurante?.id) : []))

function normalize(text) {
  return String(text || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
}

const visibles = computed(() => productos.value.filter((p) =>
  (!categoriaId.value || p.categoria_id === Number(categoriaId.value)) &&
  (!buscar.value || normalize(p.nombre).includes(normalize(buscar.value)))))

async function load() {
  const [p, c, pp, ca, g, imp] = await Promise.all([
    quiet(() => postData('/producto/list', { todos: true })),
    quiet(() => postData('/categoria/list')),
    auth.modulos.has('pedidos') ? quiet(() => postData('/punto_produccion/list')) : [],
    quiet(() => postData('/carta/list')),
    quiet(() => postData('/modificador/list')),
    quiet(() => postData('/impuesto/list')),
  ])
  productos.value = p || []
  categorias.value = c || []
  puntos.value = pp || []
  cartas.value = ca || []
  grupos.value = g || []
  impuestos.value = imp || []
  cargado.value = true
}

function nuevo() {
  form.value = {
    nombre: '', descripcion: '', precio: null, categoria_id: Number(categoriaId.value) || categorias.value[0]?.id,
    punto_produccion_id: null, impuesto_id: null, orden: 0, cartas: cartas.value.map((c) => c.id), grupos: [],
  }
}

function editar(producto) {
  form.value = { ...producto, producto_id: producto.id }
}

async function duplicar(producto) {
  const data = await attempt(() => postData('/producto/duplicar', { producto_id: producto.id }), { success: (d) => `Se creó ${d.nombre}.` })
  if (data) {
    await load()
    editar(data)
  }
}

// Copia lo que se ve en la lista filtrada, para poder pasar una sola categoría
async function copiarASede() {
  const json = await attempt(() => post('/producto/copiar', { restaurante_id: Number(copia.value.restaurante_id), productos: visibles.value.map((p) => p.id) }),
    { success: (r) => r?.message })
  if (json) copia.value = null
}

async function guardar() {
  const editando = !!form.value.producto_id
  const ok = await attempt(() => postData(editando ? '/producto/update' : '/producto/create', form.value),
    { success: 'Producto guardado.' })
  if (ok) {
    form.value = null
    load()
  }
}

async function agotado(producto) {
  await attempt(() => postData('/producto/agotado', { producto_id: producto.id, agotado: !producto.agotado }),
    { success: producto.agotado ? `${producto.nombre} disponible de nuevo.` : `${producto.nombre} marcado como agotado.` })
  load()
}

async function cambiarEstado(producto) {
  await attempt(() => postData('/producto/change_status', { producto_id: producto.id, activo: !producto.activo }),
    { success: producto.activo ? 'Producto retirado de la carta.' : 'Producto activo de nuevo.' })
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Productos</h1>
        <p>El precio es el que ve el cliente, con impuestos incluidos.</p>
      </div>
      <div class="actions">
        <button v-if="otrasSedes.length" class="btn btn-secundario" type="button" :disabled="!visibles.length"
                @click="copia = { restaurante_id: otrasSedes[0].id }">Copiar a otra sede</button>
        <button class="btn btn-secundario" type="button" @click="importando = true">Importar</button>
        <button class="btn" type="button" :disabled="!categorias.length" @click="nuevo">Crear producto</button>
      </div>
    </header>
    <ImportarProductos :open="importando" @close="importando = false" @imported="load" />
    <AppModal :open="!!copia" title="Copiar a otra sede" width="30rem" @close="copia = null">
      <form v-if="copia" @submit.prevent="copiarASede">
        <p>Se copian los <strong>{{ visibles.length }}</strong> productos de la lista actual. Usa los filtros para pasar solo una categoría.</p>
        <div class="field copia-sede">
          <label for="copia-sede">Hacia</label>
          <select id="copia-sede" v-model="copia.restaurante_id" class="select">
            <option v-for="r in otrasSedes" :key="r.id" :value="r.id">{{ r.nombre }}</option>
          </select>
        </div>
        <p class="muted">Lo que ya existe allá con el mismo nombre no se toca. Las recetas no se copian, porque dependen de los insumos de cada local.</p>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="copia = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy">Copiar</button>
        </div>
      </form>
    </AppModal>

    <div class="filtros">
      <input v-model="buscar" class="input" type="search" placeholder="Buscar producto" aria-label="Buscar producto">
      <select v-model="categoriaId" class="select" aria-label="Categoría">
        <option value="">Todas las categorías</option>
        <option v-for="categoria in categorias" :key="categoria.id" :value="categoria.id">{{ categoria.nombre }}</option>
      </select>
    </div>

    <p v-if="!cargado" class="empty">Cargando productos…</p>
    <div v-else-if="!categorias.length" class="empty">
      <p>Primero crea una categoría para poder agregar productos.</p>
      <RouterLink class="btn" :to="{ name: 'admin-categorias' }">Ir a categorías</RouterLink>
    </div>

    <div v-else class="panel table-wrap">
      <table class="table">
        <thead><tr><th>Producto</th><th>Categoría</th><th>Se prepara en</th><th class="num">Precio</th><th>Disponible</th><th></th></tr></thead>
        <tbody>
          <tr v-for="producto in visibles" :key="producto.id" :class="{ muted: !producto.activo }">
            <td><strong>{{ producto.nombre }}</strong><span v-if="!producto.activo"> (inactivo)</span></td>
            <td>{{ producto.categoria }}</td>
            <td>{{ producto.punto_produccion || 'El de la categoría' }}</td>
            <td class="num">{{ formatMoney(producto.precio) }}</td>
            <td>
              <button class="btn btn-secundario btn-sm" type="button" :disabled="busy" :aria-pressed="producto.agotado"
                      @click="agotado(producto)">{{ producto.agotado ? 'Agotado' : 'Disponible' }}</button>
            </td>
            <td class="actions">
              <button class="btn btn-secundario btn-sm" type="button" @click="editar(producto)">Editar</button>
              <button class="btn btn-secundario btn-sm" type="button" :disabled="busy" :aria-label="`Duplicar ${producto.nombre}`" @click="duplicar(producto)">Duplicar</button>
              <button class="btn btn-secundario btn-sm" type="button" :disabled="busy" @click="cambiarEstado(producto)">
                {{ producto.activo ? 'Desactivar' : 'Activar' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!visibles.length" class="empty">Ningún producto coincide.</p>
    </div>

    <AppModal :open="!!form" :title="form?.producto_id ? `Editar ${form.nombre}` : 'Crear producto'" @close="form = null">
      <form v-if="form" @submit.prevent="guardar">
        <div class="form-grid">
          <div class="field">
            <label for="p-nombre">Nombre</label>
            <input id="p-nombre" v-model="form.nombre" class="input" required maxlength="100">
          </div>
          <div class="field">
            <label for="p-precio">Precio de carta</label>
            <input id="p-precio" v-model.number="form.precio" class="input" type="number" min="0" step="100" required inputmode="numeric"
                   :disabled="!!form.producto_id && !auth.can('catalogo.precios')">
          </div>
          <div class="field">
            <label for="p-cat">Categoría</label>
            <select id="p-cat" v-model="form.categoria_id" class="select" required>
              <option v-for="categoria in categorias" :key="categoria.id" :value="categoria.id">{{ categoria.nombre }}</option>
            </select>
          </div>
          <div class="field">
            <label for="p-punto">Se prepara en</label>
            <select id="p-punto" v-model="form.punto_produccion_id" class="select">
              <option :value="null">El de la categoría o la zona</option>
              <option v-for="punto in puntos" :key="punto.id" :value="punto.id">{{ punto.nombre }}</option>
            </select>
          </div>
          <div v-if="impuestos.length" class="field">
            <label for="p-impuesto">Impuesto</label>
            <select id="p-impuesto" v-model="form.impuesto_id" class="select">
              <option :value="null">El de la categoría o el por defecto</option>
              <option v-for="imp in impuestos" :key="imp.id" :value="imp.id">{{ imp.nombre }} · {{ imp.porcentaje_texto }}</option>
            </select>
          </div>
        </div>
        <div class="field descripcion">
          <label for="p-desc">Descripción</label>
          <textarea id="p-desc" v-model="form.descripcion" class="textarea" maxlength="500" placeholder="Opcional: ingredientes, tamaño…"></textarea>
        </div>
        <fieldset v-if="cartas.length > 1" class="cartas">
          <legend>Aparece en</legend>
          <label v-for="carta in cartas" :key="carta.id" class="check">
            <input v-model="form.cartas" type="checkbox" :value="carta.id"> {{ carta.nombre }}
          </label>
        </fieldset>
        <fieldset v-if="grupos.length" class="cartas">
          <legend>Opciones que se pueden elegir</legend>
          <label v-for="grupo in grupos" :key="grupo.id" class="check">
            <input v-model="form.grupos" type="checkbox" :value="grupo.id">
            {{ grupo.nombre }} <span class="muted">({{ grupo.opciones.map((o) => o.nombre).join(', ') }})</span>
          </label>
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
.filtros {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.descripcion {
  margin-top: var(--space-4);
}

.cartas {
  margin: var(--space-4) 0 0;
  padding: var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
}

[aria-pressed='true'] {
  background: var(--estado-cancelado-suave);
  border-color: var(--estado-cancelado);
}

@media (max-width: 34rem) {
  .filtros {
    grid-template-columns: 1fr;
  }
}
</style>
