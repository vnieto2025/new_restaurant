<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { postData } from '@/services/api'
import { useToastStore } from '@/stores/toast'
import { useAuthStore } from '@/stores/auth'
import { usePrintStore } from '@/stores/print'
import { useRealtime } from '@/composables/useRealtime'
import { useAction } from '@/composables/useAction'
import { useDraft } from '@/composables/useDraft'
import { formatMoney, formatTime } from '@/utils/format'
import OpsBar from '@/components/OpsBar.vue'
import ConnectionBanner from '@/components/ConnectionBanner.vue'
import MenuPicker from '@/components/MenuPicker.vue'
import CartPanel from '@/components/CartPanel.vue'
import StatusChip from '@/components/StatusChip.vue'
import ReasonDialog from '@/components/ReasonDialog.vue'
import MesaAcciones from '@/components/MesaAcciones.vue'

const props = defineProps({ mesaId: { type: String, required: true } })

const router = useRouter()
const toast = useToastStore()
const auth = useAuthStore()
const printer = usePrintStore()
const { busy, attempt, quiet } = useAction()
const draft = useDraft(`mesa:${props.mesaId}`)

const carta = ref(null)
const ordenes = ref([])
const panel = ref('enviar')
const verPanel = ref(false)
const cancelar = ref({ open: false, item: null })

const mesa = computed(() => carta.value?.mesa)
const zona = computed(() => carta.value?.zona)
const totalMesa = computed(() => ordenes.value.reduce((sum, o) => sum + o.total, 0))
const totalBorrador = computed(() => draft.lineas.value.reduce((s, l) => s + l.precio * l.cantidad, 0))
const piezasBorrador = computed(() => draft.lineas.value.reduce((s, l) => s + l.cantidad, 0))
const pendientes = computed(() =>
  ordenes.value.flatMap((o) => o.items).filter((i) => ['pendiente_aprobacion', 'nuevo', 'en_proceso', 'despachado'].includes(i.estado)))
const conCaja = computed(() => auth.modulos.has('caja'))
// Sin caja contratada la mesa se libera aquí; con caja se libera al cobrar
const puedeCerrar = computed(() => !conCaja.value && ordenes.value.length > 0 && pendientes.value.length === 0)

// A la orden más reciente que ya está en producción se le agregan ítems (comanda de adición, doc 15)
const ordenDestino = computed(() =>
  ordenes.value.find((o) => !['pendiente_aprobacion', 'cancelada'].includes(o.estado)))

async function loadCarta() {
  const data = await quiet(() => postData('/orden/carta', { mesa_id: Number(props.mesaId) }))
  if (data) carta.value = data
  else if (!carta.value) router.replace({ name: 'mesero' })
}

async function loadOrdenes() {
  try {
    ordenes.value = await postData('/orden/list', { mesa_id: Number(props.mesaId) })
  } catch (error) {
    toast.error(error.message)
  }
}

function onEvent(event) {
  if (event.mesa_id === Number(props.mesaId)) loadOrdenes()
  if (event.tipo === 'producto.agotado') loadCarta()
}

const canales = computed(() => (zona.value ? [`zona:${zona.value.id}`] : []))
const { status, online } = useRealtime(canales, { onEvent, onSync: () => { loadOrdenes(); loadCarta() } })

async function enviar() {
  if (!draft.lineas.value.length) return
  const destino = ordenDestino.value
  const body = { clave_idempotencia: draft.draft.value.clave, items: draft.items() }
  const orden = destino
    ? await attempt(() => postData('/orden/agregar_items', { ...body, orden_id: destino.id }))
    : await attempt(() => postData('/orden/create', { ...body, mesa_id: Number(props.mesaId), notas: draft.draft.value.notas || null }))
  if (!orden) return // el borrador se conserva con la misma clave para reintentar

  toast.success(destino ? `Agregado a ${orden.numero_texto}. Cocina lo ve como adición.` : `Orden ${orden.numero_texto} enviada.`)
  draft.clear()
  panel.value = 'mesa'
  await loadOrdenes()
}

async function aprobar(orden) {
  await attempt(() => postData('/orden/aprobar', { orden_id: orden.id }), { success: 'Orden aprobada y enviada a producción.' })
  loadOrdenes()
}

async function entregar(orden) {
  await attempt(() => postData('/orden/entregar', { orden_id: orden.id }), { success: 'Entregado.' })
  loadOrdenes()
}

async function confirmarCancelacion(motivo) {
  const item = cancelar.value.item
  await attempt(() => postData('/orden/cancelar_item', { orden_item_id: item.id, motivo }), { success: `${item.nombre} cancelado.` })
  cancelar.value.open = false
  loadOrdenes()
}

async function precuenta(orden) {
  const tirilla = await attempt(() => postData('/orden/tirilla', { orden_id: orden.id }))
  if (tirilla) printer.print('orden', tirilla)
}

async function pedirCuenta() {
  const cuenta = await attempt(() => postData('/cuenta/solicitar', { mesa_id: Number(props.mesaId) }),
    { success: 'Cuenta pedida. Caja ya la tiene.' })
  if (cuenta) printer.print('cuenta', cuenta)
}

async function cerrarMesa() {
  const ok = await attempt(() => postData('/mesa/cerrar', { mesa_id: Number(props.mesaId) }), { success: 'Mesa cerrada. Queda libre.' })
  if (ok !== undefined) router.push({ name: 'mesero' })
}

onMounted(async () => {
  await loadCarta()
  loadOrdenes()
})
</script>

<template>
  <div class="mesa-view">
    <OpsBar :title="mesa ? `${mesa.nombre}` : 'Mesa'" :back="{ name: 'mesero' }">
      <span v-if="zona" class="zona-tag">{{ zona.nombre }}</span>
    </OpsBar>
    <ConnectionBanner :status="status" :online="online" />

    <div class="layout">
      <MenuPicker class="carta" :categorias="carta?.categorias || []" :cantidades="draft.cantidades.value"
                  @add="draft.add" />

      <aside class="lado" :class="{ abierto: verPanel }" aria-label="Orden de la mesa">
        <div class="lado-tabs" role="tablist">
          <button role="tab" type="button" :aria-selected="panel === 'enviar'" @click="panel = 'enviar'">
            Por enviar <span v-if="piezasBorrador">({{ piezasBorrador }})</span>
          </button>
          <button role="tab" type="button" :aria-selected="panel === 'mesa'" @click="panel = 'mesa'">
            En la mesa <span v-if="ordenes.length">· {{ formatMoney(totalMesa) }}</span>
          </button>
          <button class="cerrar-panel" type="button" aria-label="Cerrar panel" @click="verPanel = false">×</button>
        </div>

        <div v-if="panel === 'enviar'" class="lado-cuerpo">
          <CartPanel :lineas="draft.lineas.value" :titulo="ordenDestino ? `Agregar a ${ordenDestino.numero_texto}` : 'Orden nueva'"
                     @change="draft.change" @remove="draft.remove">
            <div v-if="!ordenDestino && draft.lineas.value.length" class="field">
              <label for="notas">Nota para cocina</label>
              <input id="notas" v-model="draft.draft.value.notas" class="input" maxlength="300" placeholder="Opcional">
            </div>
            <button class="btn btn-grande btn-bloque" type="button" :disabled="busy || !draft.lineas.value.length || !online"
                    :aria-busy="busy" @click="enviar">
              {{ busy ? 'Enviando…' : 'Enviar a cocina' }}
            </button>
            <p v-if="!online" class="muted aviso">Sin internet: la orden se conserva aquí hasta que vuelva la conexión.</p>
          </CartPanel>
        </div>

        <div v-else class="lado-cuerpo">
          <p v-if="!ordenes.length" class="muted">Esta mesa todavía no ha pedido nada.</p>
          <MesaAcciones v-else :mesa-id="Number(mesaId)" :mesa-nombre="mesa?.nombre" @changed="loadOrdenes" />
          <article v-for="orden in ordenes" :key="orden.id" class="orden">
            <header class="orden-head">
              <strong>{{ orden.numero_texto }}</strong>
              <span class="muted">{{ formatTime(orden.creado_en) }}</span>
              <StatusChip :estado="orden.estado" />
            </header>
            <p v-for="comanda in orden.comandas.filter((c) => c.sin_confirmar)" :key="comanda.id" class="sin-confirmar" role="alert">
              {{ comanda.punto_produccion }} aún no confirma que recibió la comanda.
            </p>
            <ul class="items">
              <li v-for="item in orden.items" :key="item.id" :class="{ tachado: item.estado === 'cancelado' }">
                <span>{{ item.cantidad }} × {{ item.nombre }}<small v-if="item.modificadores.length"> · {{ item.modificadores.map((m) => m.nombre).join(', ') }}</small><small v-if="item.nota"> · {{ item.nota }}</small></span>
                <StatusChip :estado="item.estado" size="sm" />
                <button v-if="['nuevo', 'pendiente_aprobacion'].includes(item.estado)" class="quitar" type="button"
                        :aria-label="`Cancelar ${item.nombre}`" @click="cancelar = { open: true, item }">Quitar</button>
              </li>
            </ul>
            <div class="actions">
              <button v-if="orden.estado === 'pendiente_aprobacion'" class="btn btn-sm" type="button" :disabled="busy"
                      @click="aprobar(orden)">Aprobar orden de QR</button>
              <button v-if="orden.items.some((i) => i.estado === 'despachado')" class="btn btn-sm" type="button"
                      :disabled="busy" @click="entregar(orden)">Marcar entregado</button>
              <button class="btn btn-secundario btn-sm" type="button" :disabled="busy" @click="precuenta(orden)">Imprimir</button>
            </div>
          </article>
          <button v-if="conCaja && ordenes.length && auth.can('ordenes.pedir_cuenta')" class="btn btn-bloque" type="button"
                  :disabled="busy" @click="pedirCuenta">
            Pedir la cuenta e imprimir precuenta ({{ formatMoney(totalMesa) }})
          </button>
          <button v-if="puedeCerrar" class="btn btn-secundario btn-bloque" type="button" :disabled="busy" @click="cerrarMesa">
            Cerrar mesa ({{ formatMoney(totalMesa) }})
          </button>
        </div>
      </aside>
    </div>

    <!-- En celular el panel se abre desde esta barra -->
    <button class="barra-movil" type="button" @click="verPanel = true">
      <span>{{ piezasBorrador ? `${piezasBorrador} por enviar` : 'Ver la mesa' }}</span>
      <strong>{{ formatMoney(piezasBorrador ? totalBorrador : totalMesa) }}</strong>
    </button>

    <ReasonDialog :open="cancelar.open" :busy="busy" :title="`Quitar ${cancelar.item?.nombre}`"
                  description="Cocina verá que se quitó de la comanda."
                  :options="['El cliente cambió de idea', 'Se tomó por error']" confirm-label="Quitar"
                  @close="cancelar.open = false" @confirm="confirmarCancelacion" />
  </div>
</template>

<style scoped>
.mesa-view {
  min-height: 100dvh;
}

.zona-tag {
  padding: 0.2em 0.7em;
  border: 1px solid #5f6a6f;
  border-radius: 999px;
  font-size: var(--text-sm);
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 25rem;
  align-items: start;
  gap: var(--space-4);
  padding: var(--space-4);
}

.lado {
  position: sticky;
  top: 4.5rem;
  max-height: calc(100dvh - 5.5rem);
  display: flex;
  flex-direction: column;
  background: var(--superficie);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
  overflow: hidden;
}

.lado-tabs {
  display: flex;
  border-bottom: 1px solid var(--linea);
}

.lado-tabs [role='tab'] {
  flex: 1;
  min-height: var(--toque);
  border: none;
  border-bottom: 3px solid transparent;
  background: transparent;
  font-weight: 600;
  cursor: pointer;
}

.lado-tabs [aria-selected='true'] {
  border-bottom-color: var(--accion);
}

.cerrar-panel {
  display: none;
}

.lado-cuerpo {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  overflow-y: auto;
}

.aviso {
  font-size: var(--text-sm);
}

.orden {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--linea);
}

.orden-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.orden-head strong {
  font-size: var(--text-lg);
}

.orden-head .muted {
  margin-right: auto;
}

.sin-confirmar {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radio-sm);
  border: 2px dashed var(--tinta);
  font-size: var(--text-sm);
}

.items {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.items li {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.items li > span:first-child {
  flex: 1;
}

.items small {
  color: var(--acero);
}

.tachado > span:first-child {
  text-decoration: line-through;
  color: var(--acero);
}

.quitar {
  min-height: 2.25rem;
  border: 1px solid var(--linea-fuerte);
  border-radius: var(--radio-sm);
  background: transparent;
  font-size: var(--text-sm);
  cursor: pointer;
}

.barra-movil {
  display: none;
}

@media (max-width: 52rem) {
  .layout {
    grid-template-columns: minmax(0, 1fr);
    padding-bottom: 6rem;
  }

  .lado {
    position: fixed;
    inset: auto 0 0 0;
    top: auto;
    z-index: 20;
    max-height: 85dvh;
    border-radius: var(--radio) var(--radio) 0 0;
    box-shadow: 0 -10px 30px rgba(28, 34, 37, 0.25);
    transform: translateY(105%);
    transition: transform 200ms ease-out;
  }

  .lado.abierto {
    transform: none;
  }

  .cerrar-panel {
    display: block;
    width: var(--toque);
    border: none;
    background: transparent;
    font-size: 1.75rem;
    cursor: pointer;
  }

  .barra-movil {
    position: fixed;
    inset: auto var(--space-3) calc(var(--space-3) + env(safe-area-inset-bottom)) var(--space-3);
    z-index: 15;
    display: flex;
    justify-content: space-between;
    align-items: center;
    min-height: var(--toque-grande);
    padding: 0 var(--space-5);
    border: none;
    border-radius: var(--radio);
    background: var(--accion);
    color: #fff;
    font-size: var(--text-lg);
    cursor: pointer;
  }
}
</style>
