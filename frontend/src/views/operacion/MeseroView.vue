<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { useRealtime } from '@/composables/useRealtime'
import { useAction } from '@/composables/useAction'
import { formatMoney, minutesAgo } from '@/utils/format'
import OpsBar from '@/components/OpsBar.vue'
import ConnectionBanner from '@/components/ConnectionBanner.vue'
import StatusChip from '@/components/StatusChip.vue'
import ReasonDialog from '@/components/ReasonDialog.vue'

/*
  Tablet del mesero (doc 17, flujo A): solo las mesas de sus zonas, con su estado,
  las órdenes de QR por aprobar y lo que la cocina ya despachó.
*/
const auth = useAuthStore()
const toast = useToastStore()
const router = useRouter()
const { busy, attempt } = useAction()

const zonas = computed(() => auth.zonas.filter((z) => !z.es_mostrador))
const zonaId = ref(Number(sessionStorage.getItem('mesero.zona')) || null)
const zonaActual = computed(() => zonas.value.find((z) => z.id === zonaId.value) || zonas.value[0])

const mesas = ref([])
const ordenes = ref([])
const cargado = ref(false)
const ahora = ref(Date.now())
const rechazo = ref({ open: false, orden: null })

const porAprobar = computed(() => ordenes.value.filter((o) => o.estado === 'pendiente_aprobacion'))
const listas = computed(() =>
  ordenes.value.filter((o) => o.mesa_tipo !== 'externa' && o.items.some((i) => i.estado === 'despachado')))
const mesasZona = computed(() => mesas.value.filter((m) => m.zona_id === zonaActual.value?.id))

const ESTADO_MESA = {
  libre: 'Libre',
  ocupada: 'Ocupada',
  con_orden: 'Con orden',
  cuenta_solicitada: 'Pidió la cuenta',
  bloqueada: 'Bloqueada',
}

async function load() {
  try {
    const [m, o] = await Promise.all([postData('/mesa/list'), postData('/orden/list')])
    mesas.value = m
    ordenes.value = o
    cargado.value = true
  } catch (error) {
    toast.error(error.message)
  }
}

let pending = null
function onEvent(event) {
  if (event.tipo === 'orden.por_aprobar') toast.info(`Orden de QR por aprobar en ${mesaNombre(event.mesa_id)}.`)
  if (event.tipo === 'comanda.despachada') toast.info(`Listo para llevar: ${mesaNombre(event.mesa_id)}.`)
  if (event.tipo === 'item.agotado') toast.error(`Cocina avisa: un producto de ${mesaNombre(event.mesa_id)} se agotó.`)
  clearTimeout(pending)
  pending = setTimeout(load, 150)
}

function mesaNombre(id) {
  return mesas.value.find((m) => m.id === id)?.nombre || 'una mesa'
}

const canales = computed(() => zonas.value.map((z) => `zona:${z.id}`))
const { status, online } = useRealtime(canales, { onEvent, onSync: load })

function elegirZona(zona) {
  zonaId.value = zona.id
  sessionStorage.setItem('mesero.zona', String(zona.id))
}

function abrirMesa(mesa) {
  if (mesa.estado === 'bloqueada') {
    toast.error(`${mesa.nombre} está bloqueada. Pídele al administrador que la habilite.`)
    return
  }
  router.push({ name: 'mesa', params: { mesaId: mesa.id } })
}

async function aprobar(orden) {
  await attempt(() => postData('/orden/aprobar', { orden_id: orden.id }), { success: `${orden.mesa}: orden enviada a producción.` })
  load()
}

async function rechazar(motivo) {
  const orden = rechazo.value.orden
  await attempt(() => postData('/orden/rechazar', { orden_id: orden.id, motivo }), { success: 'Orden rechazada.' })
  rechazo.value.open = false
  load()
}

async function terminarTurno() {
  const ok = await attempt(() => postData('/turno_mesero/cerrar'), { success: 'Turno terminado. ¡Buen descanso!' })
  if (ok) auth.logout()
}

async function entregar(orden) {
  await attempt(() => postData('/orden/entregar', { orden_id: orden.id }), { success: `Entregado en ${orden.mesa}.` })
  load()
}

let reloj = null
onMounted(() => {
  load()
  reloj = setInterval(() => (ahora.value = Date.now()), 30000)
})
onBeforeUnmount(() => {
  clearInterval(reloj)
  clearTimeout(pending)
})
</script>

<template>
  <div class="mesero">
    <OpsBar title="Mesas">
      <button v-if="auth.dispositivo" class="barra-btn" type="button" @click="auth.logout()">Cambiar de mesero</button>
      <button v-if="auth.roles.includes('mesero')" class="barra-btn" type="button" :disabled="busy" @click="terminarTurno">Terminar mi turno</button>
    </OpsBar>
    <ConnectionBanner :status="status" :online="online" />

    <nav v-if="zonas.length > 1" class="zonas" aria-label="Zonas">
      <button v-for="zona in zonas" :key="zona.id" type="button" class="zona" :aria-pressed="zona.id === zonaActual?.id"
              @click="elegirZona(zona)">
        {{ zona.nombre }}
      </button>
    </nav>

    <main class="contenido">
      <!-- Lo urgente primero: órdenes de QR que esperan al mesero (doc 34) -->
      <section v-if="porAprobar.length" class="alerta" aria-label="Órdenes por aprobar">
        <h2>Por aprobar</h2>
        <article v-for="orden in porAprobar" :key="orden.id" class="pendiente">
          <div class="pendiente-info">
            <strong>{{ orden.mesa }}</strong>
            <span class="muted">{{ orden.numero_texto }} · {{ minutesAgo(orden.creado_en, ahora) }} · {{ formatMoney(orden.total) }}</span>
            <span>{{ orden.items.map((i) => `${i.cantidad} ${i.nombre}`).join(', ') }}</span>
          </div>
          <div class="actions">
            <button class="btn btn-secundario" type="button" :disabled="busy" @click="rechazo = { open: true, orden }">Rechazar</button>
            <button class="btn" type="button" :disabled="busy" @click="aprobar(orden)">Aprobar</button>
          </div>
        </article>
      </section>

      <section v-if="listas.length" class="listas" aria-label="Listo para llevar a la mesa">
        <h2>Para llevar a la mesa</h2>
        <article v-for="orden in listas" :key="orden.id" class="lista">
          <div>
            <strong>{{ orden.mesa }}</strong>
            <span>{{ orden.items.filter((i) => i.estado === 'despachado').map((i) => `${i.cantidad} ${i.nombre}`).join(', ') }}</span>
          </div>
          <button class="btn" type="button" :disabled="busy" @click="entregar(orden)">Entregado</button>
        </article>
      </section>

      <p v-if="!cargado" class="empty">Cargando mesas…</p>
      <p v-else-if="!zonas.length" class="empty">No tienes zonas asignadas. Pídele al administrador que te asigne una.</p>
      <p v-else-if="!mesasZona.length" class="empty">Esta zona aún no tiene mesas.</p>

      <div v-else class="mesas">
        <button v-for="mesa in mesasZona" :key="mesa.id" type="button" class="mesa" :class="`mesa-${mesa.estado}`"
                @click="abrirMesa(mesa)">
          <span class="mesa-nombre">{{ mesa.nombre }}</span>
          <span class="mesa-estado">{{ ESTADO_MESA[mesa.estado] }}</span>
          <StatusChip v-if="mesa.estado_urgente" :estado="mesa.estado_urgente" size="sm" />
          <span v-if="mesa.sesion" class="mesa-total">{{ formatMoney(mesa.sesion.total) }}</span>
        </button>
      </div>
    </main>

    <ReasonDialog :open="rechazo.open" :busy="busy" :title="`Rechazar orden de ${rechazo.orden?.mesa}`"
                  description="La orden no llega a cocina y el cliente ve que fue rechazada."
                  :options="['Mesa vacía', 'Pedido duplicado', 'Ya lo pidió al mesero']" confirm-label="Rechazar"
                  @close="rechazo.open = false" @confirm="rechazar" />
  </div>
</template>

<style scoped>
.mesero {
  min-height: 100dvh;
}

.barra-btn {
  min-height: 2.5rem;
  padding: 0 var(--space-3);
  border: 1px solid #5f6a6f;
  border-radius: var(--radio-sm);
  background: transparent;
  color: #fff;
  font-size: var(--text-sm);
  cursor: pointer;
  white-space: nowrap;
}

.zonas {
  display: flex;
  gap: var(--space-2);
  overflow-x: auto;
  padding: var(--space-3) var(--space-4);
  background: var(--superficie);
  border-bottom: 1px solid var(--linea);
}

.zona {
  flex: none;
  min-height: var(--toque);
  padding: 0 var(--space-5);
  border: 1px solid var(--linea-fuerte);
  border-radius: var(--radio);
  background: var(--superficie);
  font-weight: 700;
  font-size: var(--text-lg);
  cursor: pointer;
}

.zona[aria-pressed='true'] {
  background: var(--tinta);
  border-color: var(--tinta);
  color: #fff;
}

.contenido {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding: var(--space-4);
  max-width: 80rem;
  margin: 0 auto;
}

.alerta,
.listas {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.alerta h2,
.listas h2 {
  font-size: var(--text-lg);
}

.pendiente,
.lista {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radio);
  background: var(--superficie);
  border: 1px solid var(--linea);
}

.pendiente {
  border-left: 8px solid var(--estado-pendiente);
}

.lista {
  border-left: 8px solid var(--estado-despachado);
}

.pendiente-info,
.lista > div {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1 1 16rem;
}

.pendiente-info strong,
.lista strong {
  font-size: var(--text-lg);
}

.mesas {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(9.5rem, 1fr));
  gap: var(--space-3);
}

.mesa {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-1);
  min-height: 8rem;
  padding: var(--space-4);
  border: 2px solid var(--linea);
  border-radius: var(--radio);
  background: var(--superficie);
  text-align: left;
  cursor: pointer;
  touch-action: manipulation;
}

.mesa-nombre {
  font-size: var(--text-2xl);
  font-weight: 800;
  font-stretch: 62%;
  line-height: 1;
}

.mesa-estado {
  color: var(--acero);
  font-weight: 600;
}

.mesa-total {
  margin-top: auto;
  font-weight: 600;
}

/* Ocupada: borde de tinta. Libre: tenue. Bloqueada: rayas (no es un estado de orden). */
.mesa-ocupada,
.mesa-con_orden {
  border-color: var(--tinta);
}

.mesa-cuenta_solicitada {
  border-color: var(--accion);
  border-width: 3px;
}

.mesa-libre {
  background: var(--papel);
}

.mesa-bloqueada {
  background: repeating-linear-gradient(-45deg, var(--fondo) 0 8px, var(--superficie) 8px 16px);
  color: var(--acero);
}
</style>
