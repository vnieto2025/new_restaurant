<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { formatDateTime, formatMoney, formatDate } from '@/utils/format'
import { formatCantidad } from '@/utils/inventario'
import OpsBar from '@/components/OpsBar.vue'
import AppModal from '@/components/AppModal.vue'
import MovimientoDialog from '@/components/MovimientoDialog.vue'
import RecepcionDialog from '@/components/RecepcionDialog.vue'

/*
  Inventario en el día a día de cocina y bodega (doc 22): registrar lo que se daña, lo que se prepara
  y contar. Pensado para tablet: botones grandes y pocos pasos.
*/
const route = useRoute()
const auth = useAuthStore()
const { busy, attempt, quiet } = useAction()

const vistas = computed(() => [
  auth.can('inventario.movimientos') && { id: 'merma', label: 'Mermas' },
  auth.can('inventario.movimientos') && { id: 'producir', label: 'Producir' },
  auth.can('inventario.contar') && { id: 'conteos', label: 'Conteos' },
  auth.can('compras.recibir') && { id: 'recibir', label: 'Recibir' },
].filter(Boolean))
const vista = ref(route.query.vista || vistas.value[0]?.id)

const insumos = ref([])
const motivos = ref([])
const buscar = ref('')
const movimiento = ref(null)
const conteos = ref([])
const conteo = ref(null)
const nuevo = ref(null)
const compras = ref([])
const recibiendo = ref(null)

const visibles = computed(() => insumos.value.filter((i) => !buscar.value || i.nombre.toLowerCase().includes(buscar.value.toLowerCase())))
const preparaciones = computed(() => insumos.value.filter((i) => i.es_preparacion && i.tiene_receta))
const categorias = computed(() => [...new Set(insumos.value.map((i) => i.categoria).filter(Boolean))].sort())
const contados = computed(() => conteo.value?.lineas.filter((l) => l.contado !== null && l.contado !== '').length || 0)

async function load() {
  const [i, e] = await Promise.all([quiet(() => postData('/insumo/list')), quiet(() => postData('/inventario/estado'))])
  insumos.value = i || []
  motivos.value = e?.motivos_merma || []
}

async function loadConteos() {
  conteos.value = (await quiet(() => postData('/conteo/list'))) || []
}

// Compras pedidas que aún no llegan completas (doc 23, sección 4)
async function loadCompras() {
  compras.value = (await quiet(() => postData('/compra/list', { estado: 'pendientes' }))) || []
}

async function abrirCompra(c) {
  const data = await attempt(() => postData('/compra/get', { compra_id: c.id }))
  if (data) recibiendo.value = data
}

function onRecibida() {
  recibiendo.value = null
  loadCompras()
  load()
}

watch(vista, (v) => {
  if (v === 'conteos') loadConteos()
  if (v === 'recibir') loadCompras()
}, { immediate: true })

function onMovido() {
  movimiento.value = null
  load()
}

async function crearConteo() {
  const data = await attempt(() => postData('/conteo/create', { categoria: nuevo.value.categoria || null, nombre: nuevo.value.nombre || null }),
    { success: (c) => c && `Conteo con ${c.total} insumos.` })
  if (data) {
    nuevo.value = null
    conteo.value = data
    loadConteos()
  }
}

async function abrirConteo(c) {
  conteo.value = await attempt(() => postData('/conteo/get', { conteo_id: c.id }))
}

async function guardarConteo() {
  const lineas = conteo.value.lineas.map((l) => ({ linea_id: l.linea_id, contado: l.contado === '' ? null : l.contado, nota: l.nota || null }))
  const data = await attempt(() => postData('/conteo/save', { conteo_id: conteo.value.id, lineas }), { success: 'Conteo guardado.' })
  if (data) conteo.value = data
  return data
}

async function aplicarConteo() {
  if (!(await guardarConteo())) return
  const data = await attempt(() => postData('/conteo/aplicar', { conteo_id: conteo.value.id }), { success: (c) => c && 'Conteo aplicado al inventario.' })
  if (data) {
    conteo.value = data
    loadConteos()
    load()
  }
}

async function descartarConteo() {
  const ok = await attempt(() => postData('/conteo/descartar', { conteo_id: conteo.value.id }), { success: 'Conteo descartado.' })
  if (ok) {
    conteo.value = null
    loadConteos()
  }
}

function diferencia(l) {
  if (l.contado === null || l.contado === '') return null
  return Number(l.contado) - l.teorico
}

onMounted(load)
</script>

<template>
  <div class="bodega">
    <OpsBar title="Inventario" />

    <div class="vistas" role="tablist">
      <button v-for="v in vistas" :key="v.id" role="tab" type="button" :aria-selected="vista === v.id" @click="vista = v.id; conteo = null">{{ v.label }}</button>
    </div>

    <main class="contenido">
      <!-- Mermas -->
      <section v-if="vista === 'merma'">
        <p class="ayuda">Toca lo que se dañó, venció o se perdió. Queda registrado con tu nombre.</p>
        <input v-model="buscar" class="input buscar" type="search" placeholder="Buscar insumo" aria-label="Buscar insumo">
        <div class="cuadricula">
          <button v-for="i in visibles" :key="i.id" type="button" class="tarjeta" @click="movimiento = { tipo: 'merma', insumo: i }">
            <strong>{{ i.nombre }}</strong>
            <span class="muted">Hay {{ formatCantidad(i.stock, i.unidad) }}</span>
          </button>
        </div>
      </section>

      <!-- Producción -->
      <section v-else-if="vista === 'producir'">
        <p class="ayuda">Registra lo que preparaste: se descuentan sus ingredientes y entra la preparación.</p>
        <div class="cuadricula">
          <button v-for="i in preparaciones" :key="i.id" type="button" class="tarjeta" @click="movimiento = { tipo: 'producir', insumo: i }">
            <strong>{{ i.nombre }}</strong>
            <span class="muted">Hay {{ formatCantidad(i.stock, i.unidad) }}</span>
          </button>
        </div>
        <p v-if="!preparaciones.length" class="empty">No hay preparaciones con receta.</p>
      </section>

      <!-- Recepción de compras -->
      <section v-else-if="vista === 'recibir'">
        <p class="ayuda">Cuando llegue un pedido, ábrelo y escribe lo que llegó de verdad.</p>
        <div class="lista-conteos">
          <button v-for="c in compras" :key="c.id" type="button" class="tarjeta fila" @click="abrirCompra(c)">
            <span><strong>{{ c.proveedor }}</strong>
              <span class="muted bloque">Compra {{ c.numero }}{{ c.entrega_esperada ? ` · llega ${formatDate(c.entrega_esperada)}` : '' }}</span></span>
            <span class="estado">{{ c.estado === 'parcial' ? 'Llegó en parte' : 'Por llegar' }}</span>
          </button>
        </div>
        <p v-if="!compras.length" class="empty">No hay pedidos por recibir.</p>
      </section>

      <!-- Conteos -->
      <section v-else-if="vista === 'conteos' && !conteo">
        <div class="barra">
          <p class="ayuda">Contar poco y seguido es más fácil que un inventario completo cada mes.</p>
          <button class="btn" type="button" @click="nuevo = { categoria: '', nombre: '' }">Nuevo conteo</button>
        </div>
        <div class="lista-conteos">
          <button v-for="c in conteos" :key="c.id" type="button" class="tarjeta fila" @click="abrirConteo(c)">
            <span><strong>{{ c.nombre }}</strong><span class="muted bloque">{{ formatDateTime(c.creado_en) }}</span></span>
            <span class="estado" :class="`estado-${c.estado}`">
              {{ c.estado === 'abierto' ? `Abierto · ${c.contados} de ${c.total}` : c.estado === 'aplicado' ? `Aplicado · ${c.con_diferencia} con diferencia` : 'Descartado' }}
            </span>
          </button>
        </div>
        <p v-if="!conteos.length" class="empty">Aún no hay conteos.</p>
      </section>

      <section v-else-if="vista === 'conteos' && conteo">
        <div class="barra">
          <div>
            <button class="enlace" type="button" @click="conteo = null; loadConteos()">‹ Conteos</button>
            <h2>{{ conteo.nombre }}</h2>
            <p class="muted">{{ conteo.estado === 'abierto' ? `Contados ${contados} de ${conteo.total}. Lo que no se cuente no se ajusta.` :
              conteo.estado === 'aplicado' ? 'Aplicado: las diferencias quedaron como ajustes.' : 'Descartado.' }}</p>
          </div>
        </div>
        <div class="panel table-wrap">
          <table class="table">
            <thead><tr><th>Insumo</th><th class="num">Sistema</th><th class="num">Contado</th><th class="num">Diferencia</th><th>Nota</th></tr></thead>
            <tbody>
              <tr v-for="l in conteo.lineas" :key="l.linea_id">
                <td><strong>{{ l.insumo }}</strong><small class="muted bloque">{{ l.categoria }}</small></td>
                <td class="num">{{ formatCantidad(l.teorico, l.unidad) }}</td>
                <td class="num">
                  <span v-if="conteo.estado === 'abierto'" class="con-unidad">
                    <input v-model="l.contado" class="input" type="number" min="0" step="any" inputmode="decimal" :aria-label="`Contado de ${l.insumo}`">
                    <span class="muted">{{ l.unidad }}</span>
                  </span>
                  <template v-else>{{ l.contado === null ? '—' : formatCantidad(l.contado, l.unidad) }}</template>
                </td>
                <td class="num" :class="{ falta: diferencia(l) < 0, sobra: diferencia(l) > 0 }">
                  <template v-if="diferencia(l) !== null">{{ diferencia(l) > 0 ? '+' : '' }}{{ formatCantidad(diferencia(l), l.unidad) }}
                    <small v-if="conteo.estado !== 'abierto' && l.valor_diferencia" class="bloque">{{ formatMoney(l.valor_diferencia) }}</small></template>
                </td>
                <td>
                  <input v-if="conteo.estado === 'abierto'" v-model="l.nota" class="input" maxlength="200" :aria-label="`Nota de ${l.insumo}`">
                  <template v-else>{{ l.nota }}</template>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="conteo.estado === 'abierto'" class="form-actions">
          <button v-if="auth.can('inventario.gestionar')" class="btn btn-secundario" type="button" :disabled="busy" @click="descartarConteo">Descartar</button>
          <button class="btn btn-secundario" type="button" :disabled="busy" @click="guardarConteo">Guardar</button>
          <button v-if="auth.can('inventario.gestionar')" class="btn" type="button" :disabled="busy || !contados" @click="aplicarConteo">Aplicar al inventario</button>
        </div>
        <p v-if="conteo.estado === 'abierto' && !auth.can('inventario.gestionar')" class="muted">Guarda lo contado; el administrador lo revisa y lo aplica.</p>
      </section>
    </main>

    <RecepcionDialog v-if="recibiendo" :compra="recibiendo" @close="recibiendo = null" @done="onRecibida" />
    <MovimientoDialog v-if="movimiento" :tipo="movimiento.tipo" :insumo="movimiento.insumo" :motivos="motivos"
                      @close="movimiento = null" @done="onMovido" />

    <AppModal :open="!!nuevo" title="Nuevo conteo" width="26rem" @close="nuevo = null">
      <form v-if="nuevo" @submit.prevent="crearConteo">
        <div class="field">
          <label for="ct-cat">Qué contar</label>
          <select id="ct-cat" v-model="nuevo.categoria" class="select">
            <option value="">Todo el inventario</option>
            <option v-for="c in categorias" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
        <div class="field espacio">
          <label for="ct-nombre">Nombre</label>
          <input id="ct-nombre" v-model="nuevo.nombre" class="input" maxlength="80" placeholder="Opcional">
        </div>
        <div class="form-actions">
          <button class="btn" type="submit" :disabled="busy">Empezar</button>
        </div>
      </form>
    </AppModal>
  </div>
</template>

<style scoped>
.bodega {
  min-height: 100dvh;
}

.vistas {
  display: flex;
  background: var(--superficie);
  border-bottom: 1px solid var(--linea);
  overflow-x: auto;
}

.vistas [role='tab'] {
  flex: 1 0 auto;
  min-height: var(--toque-grande);
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

.contenido {
  max-width: 70rem;
  margin: 0 auto;
  padding: var(--space-4);
}

.ayuda {
  margin-bottom: var(--space-3);
  color: var(--acero);
}

.buscar {
  margin-bottom: var(--space-3);
}

.cuadricula {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(9.5rem, 1fr));
  gap: var(--space-3);
}

.tarjeta {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-1);
  min-height: var(--toque-grande);
  padding: var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio-sm);
  background: var(--papel);
  text-align: left;
  cursor: pointer;
}

.tarjeta.fila {
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.lista-conteos {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.barra {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-end;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.barra h2 {
  font-size: var(--text-xl);
}

.bloque {
  display: block;
}

.estado {
  font-size: var(--text-sm);
  font-weight: 700;
  text-align: right;
}

.estado-abierto {
  color: var(--accion);
}

.con-unidad {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.con-unidad .input {
  width: 7rem;
}

.falta {
  color: var(--estado-cancelado);
  font-weight: 700;
}

.sobra {
  font-weight: 700;
}

.enlace {
  border: none;
  background: none;
  padding: 0;
  color: var(--accion);
  font-weight: 700;
  cursor: pointer;
}

.espacio {
  margin-top: var(--space-3);
}
</style>
