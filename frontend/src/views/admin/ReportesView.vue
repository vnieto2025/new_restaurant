<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'
import { usePrintStore } from '@/stores/print'
import {
  formatMoney, formatMoneyShort, formatDay, formatDateLong, formatChange, formatDateTime, isoDate, parseDate, downloadCsv,
} from '@/utils/format'
import BarChart from '@/components/BarChart.vue'
import TablaDesglose from '@/components/TablaDesglose.vue'
import AnalisisOperacion from '@/components/AnalisisOperacion.vue'

/*
  Reportes del MVP (doc 26): ventas con comparativo, desgloses, meseros y cancelaciones.
  Cada número va con su comparativo para responder "¿es bueno o malo?".
*/
const { quiet } = useAction()
const printer = usePrintStore()

const periodo = ref('hoy')
const rango = ref({ desde: '', hasta: '' })
const reporte = ref(null)
const meseros = ref([])
const cancelaciones = ref(null)
const cargando = ref(false)

const PERIODOS = [
  { id: 'hoy', label: 'Hoy' },
  { id: 'ayer', label: 'Ayer' },
  { id: 'semana', label: 'Últimos 7 días' },
  { id: 'mes', label: 'Este mes' },
  { id: 'mes_anterior', label: 'Mes anterior' },
  { id: 'rango', label: 'Otro rango' },
]

function fechas(id, hoy) {
  const d = (dias) => { const f = new Date(hoy); f.setDate(f.getDate() + dias); return isoDate(f) }
  if (id === 'hoy') return { desde: isoDate(hoy), hasta: isoDate(hoy) }
  if (id === 'ayer') return { desde: d(-1), hasta: d(-1) }
  if (id === 'semana') return { desde: d(-6), hasta: isoDate(hoy) }
  if (id === 'mes') return { desde: isoDate(new Date(hoy.getFullYear(), hoy.getMonth(), 1)), hasta: isoDate(hoy) }
  if (id === 'mes_anterior') {
    return { desde: isoDate(new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1)), hasta: isoDate(new Date(hoy.getFullYear(), hoy.getMonth(), 0)) }
  }
  return rango.value
}

const titulo = computed(() => {
  if (!reporte.value) return ''
  const { desde, hasta } = reporte.value
  return desde === hasta ? formatDateLong(desde) : `${formatDateLong(desde)} al ${formatDateLong(hasta)}`
})

const tarjetas = computed(() => {
  if (!reporte.value) return []
  const t = reporte.value.totales
  const c = reporte.value.comparativos[0]
  return [
    { nombre: 'Ventas', valor: formatMoney(t.ventas), cambio: c.variacion_ventas, antes: formatMoney(c.ventas) },
    { nombre: 'Cuentas', valor: t.cuentas, cambio: c.variacion_cuentas, antes: c.cuentas },
    { nombre: 'Ticket promedio', valor: formatMoney(t.ticket_promedio), cambio: c.variacion_ticket, antes: formatMoney(c.ticket_promedio) },
    { nombre: 'Propinas', valor: formatMoney(t.propinas), cambio: null, antes: null },
  ]
})

const serie = computed(() => (reporte.value?.serie || []).map((d) => ({
  etiqueta: formatDay(d.jornada), valor: d.ventas, detalle: `${d.cuentas} cuentas`,
})))

async function cargar() {
  const { desde, hasta } = fechas(periodo.value, hoyRestaurante.value)
  if (!desde || !hasta) return
  cargando.value = true
  const [r, m] = await Promise.all([
    quiet(() => postData('/reporte/ventas', { desde, hasta })),
    quiet(() => postData('/reporte/meseros', { desde, hasta })),
  ])
  cargando.value = false
  if (r) reporte.value = r
  meseros.value = m || []
  cancelaciones.value = null
}

async function verCancelaciones() {
  cancelaciones.value = (await quiet(() => postData('/reporte/cancelaciones', { desde: reporte.value.desde, hasta: reporte.value.hasta }))) || []
}

function elegir(id) {
  periodo.value = id
  if (id !== 'rango') cargar()
}

function exportarMeseros() {
  downloadCsv('ventas-por-mesero', [
    { titulo: 'Mesero', campo: 'nombre' }, { titulo: 'Mesas', campo: 'mesas' }, { titulo: 'Órdenes', campo: 'ordenes' },
    { titulo: 'Ítems', campo: 'items' }, { titulo: 'Ventas', campo: 'ventas' }, { titulo: 'Cancelaciones', campo: 'cancelaciones' },
  ], meseros.value)
}

function exportarCancelaciones() {
  downloadCsv('cancelaciones', [
    { titulo: 'Orden', campo: 'orden' }, { titulo: 'Mesa', campo: 'mesa' }, { titulo: 'Producto', campo: 'producto' },
    { titulo: 'Cantidad', campo: 'cantidad' }, { titulo: 'Valor', campo: 'valor' }, { titulo: 'Tipo', campo: 'tipo' },
    { titulo: 'Motivo', campo: 'motivo' }, { titulo: 'Quién', campo: 'usuario' },
  ], cancelaciones.value)
}

// La jornada de "hoy" la define el restaurante (RG-09); se toma del dashboard
const hoyRestaurante = ref(new Date())
onMounted(async () => {
  const tablero = await quiet(() => postData('/reporte/dashboard'))
  if (tablero) hoyRestaurante.value = parseDate(tablero.jornada)
  rango.value = fechas('semana', hoyRestaurante.value)
  cargar()
})
</script>

<template>
  <div class="reportes">
    <header class="page-head">
      <div>
        <h1>Reportes</h1>
        <p v-if="reporte">{{ titulo }}<template v-if="reporte.en_curso"> · la jornada aún no termina</template></p>
      </div>
      <button class="btn btn-secundario no-print" type="button" :disabled="!reporte" @click="printer.printPage()">Imprimir</button>
    </header>

    <div class="periodos no-print" role="group" aria-label="Periodo">
      <button v-for="p in PERIODOS" :key="p.id" type="button" class="btn btn-secundario btn-sm" :aria-pressed="periodo === p.id"
              @click="elegir(p.id)">{{ p.label }}</button>
      <form v-if="periodo === 'rango'" class="rango" @submit.prevent="cargar">
        <input v-model="rango.desde" class="input" type="date" aria-label="Desde" required>
        <input v-model="rango.hasta" class="input" type="date" aria-label="Hasta" required>
        <button class="btn btn-sm" type="submit">Ver</button>
      </form>
    </div>

    <p v-if="!reporte" class="empty">{{ cargando ? 'Calculando…' : 'Elige un periodo.' }}</p>

    <template v-else>
      <dl class="tarjetas">
        <div v-for="t in tarjetas" :key="t.nombre" class="tarjeta">
          <dt>{{ t.nombre }}</dt>
          <dd class="valor">{{ t.valor }}</dd>
          <dd v-if="t.cambio !== null" class="cambio">{{ formatChange(t.cambio) }} <span class="muted">vs {{ t.antes }}</span></dd>
          <dd v-else-if="t.antes !== null" class="cambio muted">Sin datos para comparar</dd>
        </div>
      </dl>
      <p class="muted nota">
        Comparado con {{ reporte.comparativos[0].nombre.toLowerCase() }}
        ({{ reporte.comparativos[0].desde === reporte.comparativos[0].hasta ? formatDateLong(reporte.comparativos[0].desde)
          : `${formatDateLong(reporte.comparativos[0].desde)} al ${formatDateLong(reporte.comparativos[0].hasta)}` }}).
        Ventas según {{ reporte.base }}, sin propinas y con descuentos restados.
        <template v-if="reporte.totales.cuentas_anuladas"> {{ reporte.totales.cuentas_anuladas }} cuentas anuladas no se cuentan.</template>
      </p>

      <BarChart v-if="serie.length > 1" titulo="Ventas por jornada" :datos="serie" :formato="formatMoney" :formato-corto="formatMoneyShort" />

      <div class="grid">
        <TablaDesglose titulo="Productos más vendidos" columna="Producto" :filas="reporte.productos" archivo="productos" />
        <TablaDesglose titulo="Categorías" columna="Categoría" :filas="reporte.categorias" archivo="categorias" />
        <TablaDesglose titulo="Zonas" columna="Zona" :filas="reporte.zonas" archivo="zonas" />
        <TablaDesglose titulo="Canales" columna="Canal" :filas="reporte.canales" archivo="canales" />
        <TablaDesglose v-if="reporte.medios.length" titulo="Medios de pago (con propina)" columna="Medio" :filas="reporte.medios" conteo="pagos" archivo="medios-de-pago" />
        <TablaDesglose titulo="Menos vendidos" columna="Producto" :filas="reporte.menos_vendidos" archivo="menos-vendidos" />
      </div>

      <AnalisisOperacion :desde="reporte.desde" :hasta="reporte.hasta" />

      <section class="panel bloque">
        <header class="bloque-head">
          <h2>Meseros</h2>
          <button v-if="meseros.length" type="button" class="enlace no-print" @click="exportarMeseros">Descargar CSV</button>
        </header>
        <p v-if="!meseros.length" class="empty">Sin órdenes de meseros en este periodo.</p>
        <div v-else class="table-wrap">
          <table class="table">
            <thead><tr><th>Mesero</th><th class="num">Mesas</th><th class="num">Órdenes</th><th class="num">Ítems</th><th class="num">Ventas</th><th class="num">Cancelaciones</th><th class="no-print"></th></tr></thead>
            <tbody>
              <tr v-for="m in meseros" :key="m.mesero_id">
                <td>{{ m.nombre }}</td><td class="num">{{ m.mesas }}</td><td class="num">{{ m.ordenes }}</td><td class="num">{{ m.items }}</td>
                <td class="num">{{ formatMoney(m.ventas) }}</td><td class="num">{{ m.cancelaciones }}</td>
                <td class="no-print">
                  <RouterLink class="enlace" :to="{ name: 'informe-mesero', query: { usuario_id: m.mesero_id, desde: reporte.desde, hasta: reporte.hasta } }">Informe</RouterLink>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel bloque">
        <header class="bloque-head">
          <h2>Cancelaciones y pérdidas</h2>
          <span class="muted">{{ reporte.cancelaciones.items }} ítems · {{ formatMoney(reporte.cancelaciones.valor) }} · pérdidas {{ formatMoney(reporte.cancelaciones.perdidas) }}</span>
        </header>
        <button v-if="cancelaciones === null && reporte.cancelaciones.items" class="btn btn-secundario btn-sm no-print" type="button" @click="verCancelaciones">Ver el detalle</button>
        <div v-else-if="cancelaciones?.length" class="table-wrap">
          <button type="button" class="enlace no-print" @click="exportarCancelaciones">Descargar CSV</button>
          <table class="table">
            <thead><tr><th>Cuándo</th><th>Orden</th><th>Producto</th><th class="num">Valor</th><th>Tipo</th><th>Motivo</th><th>Quién</th></tr></thead>
            <tbody>
              <tr v-for="(c, i) in cancelaciones" :key="i">
                <td>{{ formatDateTime(c.momento) }}</td><td>{{ c.orden }} · {{ c.mesa }}</td><td>{{ c.cantidad }} × {{ c.producto }}</td>
                <td class="num">{{ formatMoney(c.valor) }}</td><td>{{ c.tipo === 'perdida' ? 'Pérdida' : 'Cancelación' }}</td>
                <td>{{ c.motivo }}</td><td>{{ c.usuario }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.periodos {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-5);
}

.periodos [aria-pressed='true'] {
  background: var(--tinta);
  border-color: var(--tinta);
  color: #fff;
}

.rango {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.rango .input {
  width: auto;
  min-height: 2.5rem;
}

.tarjetas {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
  gap: var(--space-3);
  margin: 0;
}

.tarjeta {
  padding: var(--space-4);
  background: var(--superficie);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
}

.tarjeta dt {
  color: var(--acero);
  font-size: var(--text-sm);
}

.tarjeta .valor {
  margin: var(--space-1) 0 0;
  font-size: var(--text-2xl);
  font-weight: 800;
  font-stretch: 68%;
}

.cambio {
  margin: var(--space-1) 0 0;
  font-size: var(--text-sm);
  font-weight: 600;
}

.nota {
  margin: var(--space-3) 0 var(--space-5);
  font-size: var(--text-sm);
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr));
  gap: var(--space-4);
  margin: var(--space-5) 0;
}

.bloque {
  margin-bottom: var(--space-5);
  padding-bottom: var(--space-2);
}

.bloque-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: baseline;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--linea);
}

.bloque-head h2 {
  font-size: var(--text-lg);
}

.bloque > .btn {
  margin: var(--space-3) var(--space-4);
}

.enlace {
  border: none;
  background: none;
  color: var(--accion);
  text-decoration: underline;
  font-size: var(--text-sm);
  cursor: pointer;
}
</style>
