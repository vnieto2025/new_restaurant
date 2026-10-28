<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useRealtime } from '@/composables/useRealtime'
import { useAction } from '@/composables/useAction'
import { formatMoney, formatTime, minutesAgo } from '@/utils/format'
import OpsBar from '@/components/OpsBar.vue'
import ConnectionBanner from '@/components/ConnectionBanner.vue'
import CobroPanel from '@/components/CobroPanel.vue'
import TurnoPanel from '@/components/TurnoPanel.vue'
import VentaDirecta from '@/components/VentaDirecta.vue'

// Caja (doc 20): lo que está por cobrar, lo cobrado hoy y el turno
const auth = useAuthStore()
const { busy, attempt, quiet } = useAction()

const estado = ref(null)
const pendientes = ref([])
const cobradas = ref([])
// Sin el módulo de pedidos la caja arranca en la venta directa (ADR-007)
const vista = ref(auth.modulos.has('pedidos') ? 'cobrar' : 'venta')
const cuenta = ref(null)
const fondo = ref(null)
const ahora = ref(Date.now())

const turnoAbierto = computed(() => !!estado.value?.turno)

async function load() {
  const [e, p] = await Promise.all([quiet(() => postData('/caja/estado')), quiet(() => postData('/cuenta/pendientes'))])
  if (e) estado.value = e
  if (p) pendientes.value = p
  ahora.value = Date.now()
  if (vista.value === 'cobradas') loadCobradas()
  if (cuenta.value) refreshCuenta()
}

async function loadCobradas() {
  cobradas.value = (await quiet(() => postData('/cuenta/list'))) || []
}

async function refreshCuenta() {
  const data = await quiet(() => postData('/cuenta/get', { cuenta_id: cuenta.value.id }))
  if (data) cuenta.value = data
}

const { status, online } = useRealtime(['ordenes'], { onEvent: load, onSync: load })

async function abrirCuenta(pendiente) {
  const data = await attempt(() => postData('/cuenta/abrir', { sesion_mesa_id: pendiente.sesion_mesa_id }))
  if (data) cuenta.value = data
}

async function verCobrada(item) {
  const data = await attempt(() => postData('/cuenta/get', { cuenta_id: item.id }))
  if (data) cuenta.value = data
}

function onUpdated(data) {
  cuenta.value = data
  load()
}

async function abrirTurno() {
  const ok = await attempt(() => postData('/caja/turno/abrir', { fondo_inicial: Number(fondo.value) || 0 }),
    { success: 'Turno abierto. Ya puedes cobrar.' })
  if (ok) {
    fondo.value = null
    load()
  }
}

// Venta directa registrada: pasa al cobro con el panel de siempre
function cobrarVenta(data) {
  cuenta.value = data
  vista.value = 'cobrar'
  load()
}

function cambiarVista(valor) {
  vista.value = valor
  if (valor === 'cobradas') loadCobradas()
}

onMounted(load)
</script>

<template>
  <div class="caja">
    <OpsBar title="Caja">
      <span v-if="estado" class="turno-tag" :class="{ abierto: turnoAbierto }">
        {{ turnoAbierto ? `Turno de ${estado.turno.usuario}` : 'Sin turno' }}
      </span>
    </OpsBar>
    <ConnectionBanner :status="status" :online="online" />

    <p v-if="estado?.jornada_cerrada" class="franja">La jornada de hoy ya se cerró. Los cobros se reanudan en la próxima jornada.</p>

    <form v-else-if="estado && !turnoAbierto && auth.can('caja.turno')" class="abrir panel" @submit.prevent="abrirTurno">
      <div>
        <h2>Abre el turno para empezar a cobrar</h2>
        <p class="muted">Cuenta la base de efectivo con la que arrancas.</p>
      </div>
      <label class="field">
        <span class="label">Base en efectivo</span>
        <input v-model.number="fondo" class="input" type="number" min="0" inputmode="numeric" placeholder="0">
      </label>
      <button class="btn btn-grande" type="submit" :disabled="busy" :aria-busy="busy">Abrir turno</button>
    </form>
    <p v-else-if="estado && !turnoAbierto" class="franja">No hay un turno de caja abierto. Pídele al cajero que lo abra.</p>

    <div class="vistas" role="tablist">
      <button role="tab" type="button" :aria-selected="vista === 'venta'" @click="cambiarVista('venta')">Venta directa</button>
      <button role="tab" type="button" :aria-selected="vista === 'cobrar'" @click="cambiarVista('cobrar')">
        Por cobrar <span v-if="pendientes.length">({{ pendientes.length }})</span>
      </button>
      <button role="tab" type="button" :aria-selected="vista === 'cobradas'" @click="cambiarVista('cobradas')">Cobradas hoy</button>
      <button v-if="auth.can(['caja.turno', 'caja.ver'])" role="tab" type="button" :aria-selected="vista === 'turno'"
              @click="cambiarVista('turno')">Turno y jornada</button>
    </div>

    <div v-if="vista === 'venta'" class="layout">
      <VentaDirecta :turno-abierto="turnoAbierto" @cobrar="cobrarVenta" />
    </div>

    <div v-else class="layout" :class="{ 'con-cuenta': cuenta && vista !== 'turno' }">
      <main class="lista">
        <template v-if="vista === 'cobrar'">
          <p v-if="!pendientes.length" class="empty">No hay nada por cobrar.</p>
          <button v-for="p in pendientes" :key="p.sesion_mesa_id" type="button" class="pendiente"
                  :class="{ activa: cuenta?.sesion_mesa_id === p.sesion_mesa_id, pedida: p.solicitada }"
                  @click="abrirCuenta(p)">
            <span class="quien">
              <strong>{{ p.mesa_tipo === 'externa' ? p.cliente_nombre || (p.venta_directa ? 'Venta directa' : 'Para llevar') : p.mesa }}</strong>
              <span class="muted">{{ p.mesa_tipo === 'externa' ? (p.venta_directa ? 'Venta directa' : p.domicilio ? 'Domicilio' : 'Para llevar') : '' }} {{ p.ordenes.join(', ') }} · {{ minutesAgo(p.abierta_en, ahora) }}</span>
            </span>
            <span class="valor">
              <strong>{{ formatMoney(p.total) }}</strong>
              <span v-if="p.solicitada" class="marca">Pidió la cuenta</span>
              <span v-else-if="p.pagado" class="muted">Abonado {{ formatMoney(p.pagado) }}</span>
            </span>
          </button>
        </template>

        <template v-else-if="vista === 'cobradas'">
          <p v-if="!cobradas.length" class="empty">Aún no hay cuentas cobradas hoy.</p>
          <div v-else class="panel table-wrap">
            <table class="table">
              <thead><tr><th>Comprobante</th><th>Mesa o cliente</th><th>Hora</th><th class="num">Total</th><th></th></tr></thead>
              <tbody>
                <tr v-for="c in cobradas" :key="c.id" :class="{ muted: c.estado === 'anulada' }">
                  <td>{{ c.numero_texto || '—' }}<span v-if="c.estado === 'anulada'"> (anulada)</span></td>
                  <td>{{ c.mesa_tipo === 'externa' ? c.cliente_nombre || (c.venta_directa ? 'Venta directa' : 'Para llevar') : c.mesa }}</td>
                  <td>{{ formatTime(c.pagada_en) }}</td>
                  <td class="num">{{ formatMoney(c.total) }}</td>
                  <td class="actions">
                    <button class="btn btn-secundario btn-sm" type="button" @click="verCobrada(c)">Ver</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <TurnoPanel v-else :turno="estado?.turno" @changed="load" />
      </main>

      <aside v-if="cuenta && vista !== 'turno'" class="detalle panel">
        <CobroPanel :cuenta="cuenta" :medios="estado?.medios || []" :turno-abierto="turnoAbierto"
                    @updated="onUpdated" @close="cuenta = null" />
      </aside>
    </div>
  </div>
</template>

<style scoped>
.caja {
  min-height: 100dvh;
}

.turno-tag {
  padding: 0.2em 0.7em;
  border: 1px solid #5f6a6f;
  border-radius: 999px;
  font-size: var(--text-sm);
  white-space: nowrap;
}

.turno-tag.abierto {
  background: var(--papel);
  color: var(--tinta);
}

.franja {
  margin: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border: 2px dashed var(--tinta);
  border-radius: var(--radio);
  background: var(--superficie);
}

.abrir {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: var(--space-4);
  margin: var(--space-4);
  padding: var(--space-5);
}

.abrir > div {
  flex: 1 1 16rem;
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

.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--space-4);
  padding: var(--space-4);
  max-width: 90rem;
  margin: 0 auto;
}

.layout.con-cuenta {
  grid-template-columns: minmax(0, 1fr) minmax(0, 30rem);
  align-items: start;
}

.lista {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
}

.pendiente {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
  min-height: 4.5rem;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--linea);
  border-left: 6px solid var(--linea-fuerte);
  border-radius: var(--radio);
  background: var(--superficie);
  text-align: left;
  cursor: pointer;
}

.pendiente.pedida {
  border-left-color: var(--accion);
}

.pendiente.activa {
  border-color: var(--tinta);
  border-left-color: var(--tinta);
}

.quien,
.valor {
  display: flex;
  flex-direction: column;
}

.quien strong {
  font-size: var(--text-lg);
}

.valor {
  align-items: flex-end;
}

.valor strong {
  font-size: var(--text-lg);
}

.marca {
  padding: 0 0.5em;
  border-radius: 999px;
  background: var(--accion);
  color: #fff;
  font-size: var(--text-sm);
  font-weight: 600;
}

.detalle {
  position: sticky;
  top: 4.5rem;
  max-height: calc(100dvh - 5.5rem);
  overflow-y: auto;
  padding: var(--space-4);
}

@media (max-width: 60rem) {
  .layout.con-cuenta {
    grid-template-columns: minmax(0, 1fr);
  }

  .detalle {
    position: fixed;
    inset: 0;
    z-index: 25;
    max-height: none;
    border-radius: 0;
  }
}
</style>
