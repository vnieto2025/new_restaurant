<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { formatMoney, downloadCsv } from '@/utils/format'
import { formatCantidad } from '@/utils/inventario'
import AppModal from '@/components/AppModal.vue'
import RecetaEditor from '@/components/RecetaEditor.vue'

/*
  Recetas, costo y margen por plato (doc 14). Muestra qué parte de lo vendido tiene receta:
  sin cobertura, el inventario y los márgenes no son confiables (sección 6).
*/
const auth = useAuthStore()
const { busy, attempt, quiet } = useAction()

const vista = ref('costos')
const costos = ref(null)
const margenMinimo = ref(60)
const soloSinReceta = ref(false)
const insumos = ref([])
const grupos = ref([])
const opcionInsumos = ref({})
const editor = ref(null)
const opcion = ref(null)

const puedeEditar = computed(() => auth.can('inventario.gestionar'))
const productos = computed(() => (costos.value?.productos || []).filter((p) => !soloSinReceta.value || !p.tiene_receta))
const preparaciones = computed(() => insumos.value.filter((i) => i.es_preparacion))

async function loadCostos() {
  costos.value = await quiet(() => postData('/receta/costos', { margen_minimo: Number(margenMinimo.value) || 0 }))
}

async function loadInsumos() {
  insumos.value = (await quiet(() => postData('/insumo/list', { todos: true }))) || []
}

async function loadOpciones() {
  const [g, o] = await Promise.all([quiet(() => postData('/modificador/list')), quiet(() => postData('/receta/opcion/list'))])
  grupos.value = g || []
  opcionInsumos.value = Object.fromEntries((o || []).map((f) => [f.opcion_id, f.lineas]))
}

watch(vista, (v) => { if (v === 'modificadores' && !grupos.value.length) loadOpciones() })

function onSaved() {
  editor.value = null
  loadCostos()
  loadInsumos()
}

function editarOpcion(o) {
  opcion.value = { ...o, lineas: (opcionInsumos.value[o.id] || []).map((l) => ({ insumo_id: l.insumo_id, cantidad: l.cantidad })) }
  if (!opcion.value.lineas.length) opcion.value.lineas.push({ insumo_id: '', cantidad: null })
}

async function guardarOpcion() {
  const lineas = opcion.value.lineas.filter((l) => l.insumo_id && Number(l.cantidad))
    .map((l) => ({ insumo_id: Number(l.insumo_id), cantidad: Number(l.cantidad) }))
  const ok = await attempt(() => postData('/receta/opcion/save', { opcion_id: opcion.value.id, lineas }), { success: 'Guardado.' })
  if (ok) {
    opcion.value = null
    loadOpciones()
  }
}

function exportar() {
  downloadCsv('costos-y-margenes', [
    { titulo: 'Producto', campo: 'nombre' }, { titulo: 'Categoría', campo: 'categoria' }, { titulo: 'Precio', campo: 'precio' },
    { titulo: 'Precio sin impuesto', campo: 'precio_sin_impuesto' }, { titulo: 'Costo', campo: 'costo' },
    { titulo: 'Margen', campo: 'margen' }, { titulo: 'Margen %', campo: 'margen_porcentaje' },
    { titulo: 'Vendido 30 días', campo: 'vendido_30_dias' },
  ], productos.value)
}

function unidadDe(id) {
  return insumos.value.find((i) => i.id === Number(id))?.unidad || ''
}

onMounted(() => Promise.all([loadCostos(), loadInsumos()]))
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Recetas y costos</h1>
        <p>Lo que lleva cada plato, cuánto cuesta y cuánto deja. Basta con los insumos principales para empezar.</p>
      </div>
    </header>

    <div v-if="costos" class="resumen">
      <div class="dato">
        <span class="muted">Ventas con receta (30 días)</span>
        <strong>{{ costos.cobertura === null ? 'Sin ventas' : `${String(costos.cobertura).replace('.', ',')} %` }}</strong>
      </div>
      <div class="dato"><span class="muted">Productos con receta</span><strong>{{ costos.con_receta }}</strong></div>
      <div class="dato"><span class="muted">Sin receta</span><strong>{{ costos.sin_receta }}</strong></div>
      <div class="dato"><span class="muted">Bajo el margen meta</span><strong>{{ costos.productos.filter((p) => p.bajo_meta).length }}</strong></div>
    </div>

    <div class="vistas" role="tablist">
      <button role="tab" type="button" :aria-selected="vista === 'costos'" @click="vista = 'costos'">Platos</button>
      <button role="tab" type="button" :aria-selected="vista === 'preparaciones'" @click="vista = 'preparaciones'">Preparaciones</button>
      <button role="tab" type="button" :aria-selected="vista === 'modificadores'" @click="vista = 'modificadores'">Modificadores</button>
    </div>

    <section v-if="vista === 'costos'">
      <form class="filtros" @submit.prevent="loadCostos">
        <label class="meta">Margen meta
          <input v-model.number="margenMinimo" class="input" type="number" min="0" max="100" aria-label="Margen meta en porcentaje"> %</label>
        <button class="btn btn-secundario" type="submit">Recalcular</button>
        <label class="check"><input v-model="soloSinReceta" type="checkbox"> Solo sin receta</label>
        <button class="btn btn-secundario" type="button" :disabled="!productos.length" @click="exportar">Descargar CSV</button>
      </form>
      <div class="panel table-wrap">
        <table class="table">
          <thead><tr><th>Producto</th><th class="num">Precio</th><th class="num">Sin impuesto</th><th class="num">Costo</th><th class="num">Margen</th><th class="num">Vendido 30 días</th><th></th></tr></thead>
          <tbody>
            <tr v-for="p in productos" :key="p.producto_id">
              <td><strong>{{ p.nombre }}</strong><small class="muted bloque">{{ p.categoria }}</small></td>
              <td class="num">{{ formatMoney(p.precio) }}</td>
              <td class="num">{{ formatMoney(p.precio_sin_impuesto) }}</td>
              <td class="num">{{ p.costo === null ? '—' : formatMoney(p.costo) }}</td>
              <td class="num">
                <template v-if="p.margen !== null">
                  {{ formatMoney(p.margen) }}
                  <span class="porcentaje" :class="{ bajo: p.bajo_meta }">{{ String(p.margen_porcentaje).replace('.', ',') }} %<template v-if="p.bajo_meta"> · bajo meta</template></span>
                </template>
                <span v-else class="muted">Sin receta</span>
              </td>
              <td class="num">{{ formatMoney(p.vendido_30_dias) }}<small class="muted bloque">{{ p.unidades_30_dias }} und</small></td>
              <td><button class="btn btn-secundario btn-sm" type="button" @click="editor = { productoId: p.producto_id }">
                {{ p.tiene_receta ? (puedeEditar ? 'Editar receta' : 'Ver receta') : 'Crear receta' }}</button></td>
            </tr>
          </tbody>
        </table>
        <p v-if="!productos.length" class="empty">No hay productos que mostrar.</p>
      </div>
      <p class="muted nota">El margen se calcula sobre el precio sin impuesto, con el costo actual de los insumos. Una bebida de reventa es una receta de un solo insumo.</p>
    </section>

    <section v-else-if="vista === 'preparaciones'">
      <p class="muted nota-arriba">Salsas, masas y caldos que se hacen en la casa. Se crean como insumo marcado «preparación» en Inventario.</p>
      <div class="panel table-wrap">
        <table class="table">
          <thead><tr><th>Preparación</th><th class="num">Existencia</th><th class="num">Costo</th><th></th></tr></thead>
          <tbody>
            <tr v-for="i in preparaciones" :key="i.id">
              <td><strong>{{ i.nombre }}</strong><span v-if="!i.tiene_receta" class="muted"> · sin receta</span></td>
              <td class="num">{{ formatCantidad(i.stock, i.unidad) }}</td>
              <td class="num">{{ formatMoney(Math.round(i.costo_unitario * (i.unidad === 'und' ? 1 : 1000))) }}
                <small class="muted">/{{ i.unidad === 'und' ? 'und' : i.unidad === 'g' ? 'kg' : 'l' }}</small></td>
              <td><button class="btn btn-secundario btn-sm" type="button" @click="editor = { insumoId: i.id }">
                {{ i.tiene_receta ? 'Editar receta' : 'Crear receta' }}</button></td>
            </tr>
          </tbody>
        </table>
        <p v-if="!preparaciones.length" class="empty">Aún no hay preparaciones.</p>
      </div>
    </section>

    <section v-else>
      <p class="muted nota-arriba">Lo que suma o resta cada opción al inventario: «Queso extra» = +30 g de queso; «Sin tomate» = −30 g de tomate.</p>
      <div v-for="g in grupos" :key="g.id" class="panel grupo">
        <h2>{{ g.nombre }}</h2>
        <p v-for="o in g.opciones" :key="o.id" class="opcion-fila">
          <span>
            <strong>{{ o.nombre }}</strong>
            <span class="muted"> · {{ (opcionInsumos[o.id] || []).map((l) => `${l.cantidad > 0 ? '+' : ''}${formatCantidad(l.cantidad, l.unidad)} ${l.insumo}`).join(', ') || 'no mueve inventario' }}</span>
          </span>
          <button v-if="puedeEditar" class="btn btn-secundario btn-sm" type="button" @click="editarOpcion(o)">Editar</button>
        </p>
      </div>
      <p v-if="!grupos.length" class="empty">No hay modificadores.</p>
    </section>

    <RecetaEditor v-if="editor" :producto-id="editor.productoId || null" :insumo-id="editor.insumoId || null" :insumos="insumos"
                  @close="editor = null" @saved="onSaved" />

    <AppModal :open="!!opcion" :title="`Insumos de «${opcion?.nombre || ''}»`" width="32rem" @close="opcion = null">
      <form v-if="opcion" @submit.prevent="guardarOpcion">
        <p class="muted">Usa un número negativo para restar (opciones como «Sin cebolla»).</p>
        <div v-for="(l, i) in opcion.lineas" :key="i" class="linea-opcion">
          <select v-model="l.insumo_id" class="select" :aria-label="`Insumo ${i + 1}`">
            <option value="">Elige un insumo</option>
            <option v-for="ins in insumos.filter((x) => x.activo)" :key="ins.id" :value="ins.id">{{ ins.nombre }}</option>
          </select>
          <input v-model.number="l.cantidad" class="input" type="number" step="any" :aria-label="`Cantidad ${i + 1}`">
          <span class="muted">{{ unidadDe(l.insumo_id) }}</span>
          <button class="btn btn-secundario btn-sm" type="button" @click="opcion.lineas.splice(i, 1)">Quitar</button>
        </div>
        <button class="btn btn-secundario btn-sm" type="button" @click="opcion.lineas.push({ insumo_id: '', cantidad: null })">Agregar insumo</button>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="opcion = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy">Guardar</button>
        </div>
      </form>
    </AppModal>
  </div>
</template>

<style scoped>
.resumen {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.dato {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3) var(--space-4);
  background: var(--superficie);
  border: 1px solid var(--linea);
  border-radius: var(--radio-sm);
}

.dato strong {
  font-size: var(--text-2xl);
  font-stretch: 68%;
}

.vistas {
  display: flex;
  margin-bottom: var(--space-4);
  border-bottom: 1px solid var(--linea);
  overflow-x: auto;
}

.vistas [role='tab'] {
  flex: 0 0 auto;
  min-height: var(--toque);
  padding: 0 var(--space-4);
  border: none;
  border-bottom: 3px solid transparent;
  background: transparent;
  font-weight: 700;
  cursor: pointer;
}

.vistas [aria-selected='true'] {
  border-bottom-color: var(--accion);
}

.filtros {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: 600;
}

.meta .input {
  width: 5rem;
}

.bloque {
  display: block;
}

.porcentaje {
  display: block;
  font-size: var(--text-sm);
}

.porcentaje.bajo {
  color: var(--estado-cancelado);
  font-weight: 700;
}

.nota {
  margin-top: var(--space-3);
  font-size: var(--text-sm);
}

.nota-arriba {
  margin-bottom: var(--space-3);
}

.grupo {
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-3);
}

.grupo h2 {
  font-size: var(--text-base);
  margin-bottom: var(--space-2);
}

.opcion-fila {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) 0;
  border-top: 1px solid var(--linea);
}

.linea-opcion {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr) 2.5rem auto;
  align-items: center;
  gap: var(--space-2);
  margin: var(--space-2) 0;
}
</style>
