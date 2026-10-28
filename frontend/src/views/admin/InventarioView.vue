<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { formatMoney, formatDateTime, formatDate, isoDate } from '@/utils/format'
import { formatCantidad, UNIDADES } from '@/utils/inventario'
import AppModal from '@/components/AppModal.vue'
import MovimientoDialog from '@/components/MovimientoDialog.vue'

/*
  Existencias del restaurante (doc 22): cuánto hay, cuánto vale y cómo se movió.
  El stock no se edita: cambia solo con entradas, consumos, mermas, ajustes y producción (RN-INV-01).
*/
const auth = useAuthStore()
const { busy, attempt, quiet } = useAction()

const TIPOS = {
  entrada: 'Entrada', compra: 'Compra', anulacion_compra: 'Anulación de compra', consumo: 'Consumo por venta', reverso_consumo: 'Reverso de consumo',
  merma: 'Merma', ajuste: 'Ajuste', produccion: 'Producción', devolucion: 'Devolución',
}

const vista = ref('existencias')
const estado = ref(null)
const insumos = ref([])
const categoria = ref('')
const buscar = ref('')
const soloAlertas = ref(false)
const form = ref(null)
const movimiento = ref(null)

const hoy = isoDate(new Date())
const hace7 = isoDate(new Date(Date.now() - 6 * 86400000))
const filtros = ref({ insumo_id: '', tipo: '', desde: hace7, hasta: hoy })
const movimientos = ref([])

const categorias = computed(() => [...new Set(insumos.value.map((i) => i.categoria).filter(Boolean))].sort())
const visibles = computed(() => insumos.value.filter((i) =>
  (!categoria.value || i.categoria === categoria.value) &&
  (!buscar.value || i.nombre.toLowerCase().includes(buscar.value.toLowerCase())) &&
  (!soloAlertas.value || i.alerta)))

const puedeGestionar = computed(() => auth.can('inventario.gestionar'))

async function load() {
  const [e, i] = await Promise.all([
    quiet(() => postData('/inventario/estado')),
    quiet(() => postData('/insumo/list', { todos: true })),
  ])
  estado.value = e
  insumos.value = i || []
}

async function loadMovimientos() {
  const body = Object.fromEntries(Object.entries(filtros.value).filter(([, v]) => v))
  movimientos.value = (await quiet(() => postData('/inventario/movimientos', body))) || []
}

watch(vista, (v) => { if (v === 'movimientos') loadMovimientos() })

function verMovimientos(insumo) {
  filtros.value = { insumo_id: insumo.id, tipo: '', desde: '', hasta: '' }
  vista.value = 'movimientos'
  loadMovimientos()
}

function nuevo() {
  form.value = { nombre: '', codigo: '', categoria: categoria.value || '', unidad: 'g', es_preparacion: false,
    stock_minimo: 0, ubicacion: '', presentaciones: [] }
}

function editar(insumo) {
  form.value = { ...insumo, insumo_id: insumo.id, presentaciones: insumo.presentaciones.map((p) => ({ ...p })) }
}

async function guardar() {
  const editando = !!form.value.insumo_id
  const body = { ...form.value, presentaciones: form.value.presentaciones.filter((p) => p.nombre?.trim()) }
  const ok = await attempt(() => postData(editando ? '/insumo/update' : '/insumo/create', body),
    { success: editando ? 'Insumo actualizado.' : 'Insumo creado.' })
  if (ok) {
    form.value = null
    load()
  }
}

async function cambiarEstado(insumo) {
  await attempt(() => postData('/insumo/change_status', { insumo_id: insumo.id, activo: !insumo.activo }),
    { success: insumo.activo ? 'Insumo inactivado.' : 'Insumo activado.' })
  load()
}

function onMovido() {
  movimiento.value = null
  load()
  if (vista.value === 'movimientos') loadMovimientos()
}

onMounted(load)
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Inventario</h1>
        <p v-if="estado">
          {{ estado.insumos }} insumos · valor {{ formatMoney(estado.valor) }} ·
          {{ estado.ultimo_conteo ? `último conteo ${formatDate(estado.ultimo_conteo.slice(0, 10))}` : 'aún sin conteos físicos' }}
        </p>
      </div>
      <div class="actions">
        <RouterLink v-if="auth.can('inventario.contar')" :to="{ name: 'bodega', query: { vista: 'conteos' } }" class="btn btn-secundario">Conteos</RouterLink>
        <button v-if="puedeGestionar" class="btn" type="button" @click="nuevo">Crear insumo</button>
      </div>
    </header>

    <ul v-if="estado && (estado.negativos.length || estado.bajos.length)" class="alertas" aria-label="Alertas de inventario">
      <li v-if="estado.negativos.length" class="alerta-critico">
        <strong>Existencia negativa:</strong> {{ estado.negativos.map((i) => i.nombre).join(', ') }}.
        Falta registrar una entrada o una receta descuenta de más.
      </li>
      <li v-if="estado.bajos.length">
        <strong>Por debajo del mínimo:</strong> {{ estado.bajos.map((i) => i.nombre).join(', ') }}.
      </li>
    </ul>

    <div class="vistas" role="tablist">
      <button role="tab" type="button" :aria-selected="vista === 'existencias'" @click="vista = 'existencias'">Existencias</button>
      <button role="tab" type="button" :aria-selected="vista === 'movimientos'" @click="vista = 'movimientos'">Movimientos</button>
    </div>

    <section v-if="vista === 'existencias'">
      <div class="filtros">
        <input v-model="buscar" class="input" type="search" placeholder="Buscar insumo" aria-label="Buscar insumo">
        <select v-model="categoria" class="select" aria-label="Categoría">
          <option value="">Todas las categorías</option>
          <option v-for="c in categorias" :key="c" :value="c">{{ c }}</option>
        </select>
        <label class="check"><input v-model="soloAlertas" type="checkbox"> Solo con alerta</label>
      </div>

      <div class="panel table-wrap">
        <table class="table">
          <thead><tr><th>Insumo</th><th class="num">Existencia</th><th class="num">Mínimo</th><th class="num">Costo</th><th class="num">Valor</th><th></th></tr></thead>
          <tbody>
            <tr v-for="insumo in visibles" :key="insumo.id" :class="{ muted: !insumo.activo }">
              <td>
                <strong>{{ insumo.nombre }}</strong>
                <span v-if="insumo.es_preparacion" class="etiqueta">Preparación</span>
                <span v-if="!insumo.activo"> (inactivo)</span>
                <small class="muted bloque">{{ insumo.categoria || 'Sin categoría' }}<template v-if="insumo.ubicacion"> · {{ insumo.ubicacion }}</template></small>
              </td>
              <td class="num">
                <strong :class="{ negativo: insumo.alerta === 'negativo' }">{{ formatCantidad(insumo.stock, insumo.unidad) }}</strong>
                <span v-if="insumo.alerta === 'bajo'" class="aviso-bajo">Bajo</span>
                <span v-else-if="insumo.alerta === 'negativo'" class="aviso-negativo">Negativo</span>
              </td>
              <td class="num">{{ insumo.stock_minimo ? formatCantidad(insumo.stock_minimo, insumo.unidad) : '—' }}</td>
              <td class="num nowrap">{{ formatMoney(Math.round(insumo.costo_unitario * (insumo.unidad === 'und' ? 1 : 1000))) }}
                <small class="muted">/{{ insumo.unidad === 'und' ? 'und' : insumo.unidad === 'g' ? 'kg' : 'l' }}</small></td>
              <td class="num">{{ formatMoney(insumo.valor_stock) }}</td>
              <td class="actions">
                <button v-if="puedeGestionar" class="btn btn-secundario btn-sm" type="button" :disabled="!insumo.activo"
                        @click="movimiento = { tipo: 'entrada', insumo }">Entrada</button>
                <button v-if="auth.can('inventario.movimientos')" class="btn btn-secundario btn-sm" type="button" :disabled="!insumo.activo"
                        @click="movimiento = { tipo: 'merma', insumo }">Merma</button>
                <button v-if="puedeGestionar" class="btn btn-secundario btn-sm" type="button" :disabled="!insumo.activo"
                        @click="movimiento = { tipo: 'ajuste', insumo }">Ajustar</button>
                <button v-if="insumo.es_preparacion && insumo.tiene_receta && auth.can('inventario.movimientos')" class="btn btn-secundario btn-sm"
                        type="button" :disabled="!insumo.activo" @click="movimiento = { tipo: 'producir', insumo }">Producir</button>
                <button class="btn btn-secundario btn-sm" type="button" @click="verMovimientos(insumo)">Movimientos</button>
                <button v-if="puedeGestionar" class="btn btn-secundario btn-sm" type="button" @click="editar(insumo)">Editar</button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="!visibles.length" class="empty">
          {{ insumos.length ? 'Ningún insumo coincide con el filtro.' : 'Crea los insumos que compras: carne, pan, gaseosas, empaques…' }}
        </p>
      </div>
    </section>

    <section v-else>
      <form class="filtros" @submit.prevent="loadMovimientos">
        <select v-model="filtros.insumo_id" class="select" aria-label="Insumo">
          <option value="">Todos los insumos</option>
          <option v-for="i in insumos" :key="i.id" :value="i.id">{{ i.nombre }}</option>
        </select>
        <select v-model="filtros.tipo" class="select" aria-label="Tipo de movimiento">
          <option value="">Todos los tipos</option>
          <option v-for="(label, valor) in TIPOS" :key="valor" :value="valor">{{ label }}</option>
        </select>
        <input v-model="filtros.desde" class="input" type="date" aria-label="Desde">
        <input v-model="filtros.hasta" class="input" type="date" aria-label="Hasta">
        <button class="btn btn-secundario" type="submit">Filtrar</button>
      </form>
      <div class="panel table-wrap">
        <table class="table">
          <thead><tr><th>Fecha</th><th>Insumo</th><th>Tipo</th><th class="num">Cantidad</th><th class="num">Costo</th><th class="num">Queda</th><th>Detalle</th></tr></thead>
          <tbody>
            <tr v-for="m in movimientos" :key="m.id">
              <td>{{ formatDateTime(m.hora_local || m.creado_en) }}</td>
              <td>{{ m.insumo }}</td>
              <td>{{ m.tipo_texto }}</td>
              <td class="num" :class="{ salida: m.cantidad < 0 }">{{ m.cantidad > 0 ? '+' : '' }}{{ formatCantidad(m.cantidad, m.unidad) }}</td>
              <td class="num">{{ formatMoney(m.costo_total) }}</td>
              <td class="num">{{ formatCantidad(m.stock_resultante, m.unidad) }}</td>
              <td>{{ m.motivo }}<small class="muted bloque">{{ m.usuario }}</small></td>
            </tr>
          </tbody>
        </table>
        <p v-if="!movimientos.length" class="empty">No hay movimientos con ese filtro.</p>
      </div>
    </section>

    <MovimientoDialog v-if="movimiento" :tipo="movimiento.tipo" :insumo="movimiento.insumo" :motivos="estado?.motivos_merma || []"
                      @close="movimiento = null" @done="onMovido" />

    <AppModal :open="!!form" :title="form?.insumo_id ? `Editar ${form.nombre}` : 'Crear insumo'" width="38rem" @close="form = null">
      <form v-if="form" @submit.prevent="guardar">
        <div class="form-grid">
          <div class="field"><label for="in-nombre">Nombre</label>
            <input id="in-nombre" v-model="form.nombre" class="input" required maxlength="100"></div>
          <div class="field"><label for="in-cat">Categoría</label>
            <input id="in-cat" v-model="form.categoria" class="input" maxlength="40" list="categorias-insumo" placeholder="Carnes, Bebidas…">
            <datalist id="categorias-insumo"><option v-for="c in categorias" :key="c" :value="c" /></datalist></div>
          <div class="field"><label for="in-unidad">Se controla en</label>
            <select id="in-unidad" v-model="form.unidad" class="select">
              <option v-for="(label, valor) in UNIDADES" :key="valor" :value="valor">{{ label }}</option>
            </select></div>
          <div class="field"><label for="in-min">Existencia mínima ({{ form.unidad }})</label>
            <input id="in-min" v-model.number="form.stock_minimo" class="input" type="number" min="0" step="any"></div>
          <div class="field"><label for="in-ubic">Ubicación</label>
            <input id="in-ubic" v-model="form.ubicacion" class="input" maxlength="40" placeholder="Nevera, bodega, barra"></div>
          <div class="field"><label for="in-cod">Código</label>
            <input id="in-cod" v-model="form.codigo" class="input" maxlength="30" placeholder="Opcional"></div>
        </div>
        <label class="check espacio"><input v-model="form.es_preparacion" type="checkbox"> Es una preparación de la casa (salsa, masa, caldo) con su propia receta</label>

        <fieldset class="presentaciones">
          <legend>Presentaciones de compra</legend>
          <p class="muted">Cómo llega: «Bulto 25 kg» equivale a 25000 g. Sirven para registrar entradas sin hacer cuentas.</p>
          <div v-for="(p, i) in form.presentaciones" :key="i" class="presentacion">
            <input v-model="p.nombre" class="input" maxlength="60" placeholder="Nombre" :aria-label="`Nombre de la presentación ${i + 1}`">
            <input v-model.number="p.factor" class="input" type="number" min="0.001" step="any" :aria-label="`Equivale en ${form.unidad}`">
            <span class="muted">{{ form.unidad }}</span>
            <button class="btn btn-secundario btn-sm" type="button" @click="form.presentaciones.splice(i, 1)">Quitar</button>
          </div>
          <button v-if="form.presentaciones.length < 6" class="btn btn-secundario btn-sm" type="button"
                  @click="form.presentaciones.push({ nombre: '', factor: null })">Agregar presentación</button>
        </fieldset>

        <div class="form-actions">
          <button v-if="form.insumo_id" class="btn btn-secundario" type="button" :disabled="busy" @click="cambiarEstado(form); form = null">
            {{ form.activo ? 'Inactivar' : 'Activar' }}</button>
          <button class="btn btn-secundario" type="button" @click="form = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy">Guardar</button>
        </div>
      </form>
    </AppModal>
  </div>
</template>

<style scoped>
.alertas {
  list-style: none;
  margin: 0 0 var(--space-4);
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.alertas li {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radio-sm);
  border-left: 4px solid var(--estado-pendiente);
  background: var(--estado-pendiente-suave);
}

.alertas .alerta-critico {
  border-left-color: var(--estado-cancelado);
  background: var(--estado-cancelado-suave);
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

.filtros .input,
.filtros .select {
  width: auto;
  min-width: 10rem;
  flex: 1 1 10rem;
  max-width: 18rem;
}

.bloque {
  display: block;
}

.nowrap {
  white-space: nowrap;
}

.etiqueta {
  margin-left: var(--space-2);
  padding: 0.1em 0.6em;
  border-radius: 999px;
  background: var(--accion-suave);
  font-size: var(--text-sm);
  font-weight: 600;
  white-space: nowrap;
}

.aviso-bajo,
.aviso-negativo {
  display: block;
  font-size: var(--text-sm);
  font-weight: 700;
}

.aviso-negativo,
.negativo {
  color: var(--estado-cancelado);
}

.salida {
  color: var(--acero);
}

.espacio {
  margin-top: var(--space-3);
}

.presentaciones {
  margin-top: var(--space-4);
  padding: var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio-sm);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.presentaciones legend {
  font-weight: 700;
  padding: 0 var(--space-1);
}

.presentacion {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr) auto auto;
  align-items: center;
  gap: var(--space-2);
}
</style>
