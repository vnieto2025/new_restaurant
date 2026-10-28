<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { postData } from '@/services/api'
import { useRealtime } from '@/composables/useRealtime'
import { useAction } from '@/composables/useAction'
import { usePrintStore } from '@/stores/print'
import { useToastStore } from '@/stores/toast'
import ComandaSlip from '@/components/ComandaSlip.vue'
import ConnectionBanner from '@/components/ConnectionBanner.vue'
import ReasonDialog from '@/components/ReasonDialog.vue'

/*
  Pantalla de producción (KDS, doc 18): pestañas En proceso y Listos, más antigua primero.
  Cada acción espera la respuesta del servidor antes de mostrarse como hecha.
*/
const props = defineProps({ puntoId: { type: String, required: true } })

const toast = useToastStore()
const printer = usePrintStore()
const { busy, attempt } = useAction()

const punto = ref(null)
const enProceso = ref([])
const listos = ref([])
const tab = ref('en_proceso')
const cargado = ref(false)
const ahora = ref(Date.now())
const desfase = ref(0)
const zonaFiltro = ref('')

const oscuro = ref(readPref('kds.oscuro', true))
const sonido = ref(readPref('kds.sonido', false))
const vistos = new Set()

const dialog = ref({ open: false, tipo: null, comanda: null, item: null })

function readPref(key, fallback) {
  try {
    const value = localStorage.getItem(key)
    return value === null ? fallback : value === '1'
  } catch {
    return fallback
  }
}

function savePref(key, value) {
  try {
    localStorage.setItem(key, value ? '1' : '0')
  } catch {
    // Sin almacenamiento la preferencia dura hasta recargar
  }
}

const zonas = computed(() => [...new Set([...enProceso.value, ...listos.value].map((c) => c.zona))].sort())
const visibles = computed(() => {
  const lista = tab.value === 'listos' ? listos.value : enProceso.value
  return zonaFiltro.value ? lista.filter((c) => c.zona === zonaFiltro.value) : lista
})

let loading = null
async function load() {
  // Si llegan varios avisos seguidos, una sola consulta a la vez
  if (loading) return loading
  loading = (async () => {
    try {
      const data = await postData('/cocina/comandas', { punto_produccion_id: Number(props.puntoId) })
      punto.value = data.punto
      desfase.value = new Date(data.servidor_en).getTime() - Date.now()
      const nuevas = data.en_proceso.filter((c) => !vistos.has(c.id))
      data.en_proceso.concat(data.listos).forEach((c) => vistos.add(c.id))
      if (cargado.value && nuevas.length) avisar(nuevas.length)
      enProceso.value = data.en_proceso
      listos.value = data.listos
      cargado.value = true
    } catch (error) {
      toast.error(error.message)
    } finally {
      loading = null
    }
  })()
  return loading
}

const { status, online } = useRealtime([`punto:${props.puntoId}`], { onEvent: load, onSync: load })

// Sonido de llegada: el navegador exige que alguien toque la pantalla una vez para permitir audio
let audio = null
function avisar(cantidad) {
  toast.info(cantidad === 1 ? 'Llegó una comanda nueva.' : `Llegaron ${cantidad} comandas nuevas.`)
  if (sonido.value) beep()
}

function beep() {
  try {
    audio = audio || new AudioContext()
    const tono = (frecuencia, inicio) => {
      const osc = audio.createOscillator()
      const gain = audio.createGain()
      osc.frequency.value = frecuencia
      osc.connect(gain)
      gain.connect(audio.destination)
      gain.gain.setValueAtTime(0.25, audio.currentTime + inicio)
      gain.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + inicio + 0.25)
      osc.start(audio.currentTime + inicio)
      osc.stop(audio.currentTime + inicio + 0.3)
    }
    tono(880, 0)
    tono(1175, 0.18)
  } catch {
    // Navegador sin audio
  }
}

// Activarlo con un toque desbloquea el audio y suena una vez de prueba
function toggleSonido() {
  sonido.value = !sonido.value
  savePref('kds.sonido', sonido.value)
  if (sonido.value) beep()
}

function toggleTema() {
  oscuro.value = !oscuro.value
  savePref('kds.oscuro', oscuro.value)
}

function replace(tarjeta) {
  const quitar = (lista) => lista.filter((c) => c.id !== tarjeta.id)
  enProceso.value = quitar(enProceso.value)
  listos.value = quitar(listos.value)
  const destino = tarjeta.pestana === 'listos' ? listos : enProceso
  if (tarjeta.estado !== 'entregada' && tarjeta.estado !== 'cancelada') {
    destino.value = [...destino.value, tarjeta].sort((a, b) => new Date(a.creado_en) - new Date(b.creado_en))
  }
}

async function abrir(comanda) {
  const tarjeta = await attempt(() => postData('/cocina/abrir', { comanda_id: comanda.id }))
  if (!tarjeta) return load()
  replace(tarjeta)
  if (tarjeta.imprimir) imprimir(tarjeta)
}

async function despachar(comanda, ids) {
  const tarjeta = await attempt(() => postData('/cocina/despachar', { comanda_id: comanda.id, orden_item_ids: ids }),
    { success: `${comanda.numero_texto} despachada.` })
  if (tarjeta) replace(tarjeta)
  else load()
}

async function imprimir(comanda) {
  const tirilla = await attempt(() => postData('/cocina/tirilla', { comanda_id: comanda.id }))
  if (tirilla) printer.print('comanda', tirilla)
}

function pedirMotivo(tipo, comanda, item = null) {
  dialog.value = { open: true, tipo, comanda, item }
}

async function confirmar(motivo) {
  const { tipo, comanda, item } = dialog.value
  const tarjeta = tipo === 'reabrir'
    ? await attempt(() => postData('/cocina/reabrir', { comanda_id: comanda.id, motivo }), { success: 'Comanda reabierta.' })
    : await attempt(() => postData('/cocina/agotado', { orden_item_id: item.id, motivo }),
      { success: `${item.nombre} agotado. Se avisó al mesero.` })
  dialog.value.open = false
  if (tarjeta) replace(tarjeta)
  else load()
}

let reloj = null
onMounted(() => {
  load()
  reloj = setInterval(() => (ahora.value = Date.now() + desfase.value), 1000)
})
onBeforeUnmount(() => clearInterval(reloj))
</script>

<template>
  <div class="kds" :class="{ claro: !oscuro }">
    <ConnectionBanner :status="status" :online="online" />

    <header class="barra">
      <div class="titulo">
        <RouterLink :to="{ name: 'inicio', query: { menu: 1 } }" class="volver" aria-label="Salir de la pantalla de producción">‹</RouterLink>
        <h1>{{ punto?.nombre || 'Producción' }}</h1>
      </div>

      <div class="tabs" role="tablist">
        <button role="tab" :aria-selected="tab === 'en_proceso'" class="tab" @click="tab = 'en_proceso'">
          En proceso <span class="contador">{{ enProceso.length }}</span>
        </button>
        <button role="tab" :aria-selected="tab === 'listos'" class="tab" @click="tab = 'listos'">
          Listos <span class="contador">{{ listos.length }}</span>
        </button>
      </div>

      <div class="ajustes">
        <select v-if="zonas.length > 1" v-model="zonaFiltro" class="filtro" aria-label="Filtrar por zona">
          <option value="">Todas las zonas</option>
          <option v-for="zona in zonas" :key="zona" :value="zona">{{ zona }}</option>
        </select>
        <button class="ajuste" type="button" :aria-pressed="sonido" @click="toggleSonido">
          Sonido {{ sonido ? 'activado' : 'apagado' }}
        </button>
        <button class="ajuste" type="button" :aria-pressed="!oscuro" @click="toggleTema">
          {{ oscuro ? 'Modo claro' : 'Modo oscuro' }}
        </button>
      </div>
    </header>

    <main class="riel">
      <p v-if="!cargado" class="vacio">Cargando comandas…</p>
      <p v-else-if="!visibles.length" class="vacio">
        {{ tab === 'listos' ? 'No hay nada esperando a que lo recojan.' : 'Sin comandas pendientes. Las nuevas aparecen aquí solas.' }}
      </p>
      <div v-else class="grid">
        <ComandaSlip v-for="comanda in visibles" :key="comanda.id" :comanda="comanda" :ahora="ahora"
                     :tiempo-objetivo="punto?.tiempo_objetivo" :salta-en-proceso="punto?.salta_en_proceso" :busy="busy"
                     @abrir="abrir(comanda)" @despachar="(ids) => despachar(comanda, ids)"
                     @reabrir="pedirMotivo('reabrir', comanda)" @imprimir="imprimir(comanda)"
                     @agotado="(item) => pedirMotivo('agotado', comanda, item)" />
      </div>
    </main>

    <ReasonDialog :open="dialog.open" :busy="busy"
                  :title="dialog.tipo === 'reabrir' ? `Reabrir ${dialog.comanda?.numero_texto}` : `¿Se acabó ${dialog.item?.nombre}?`"
                  :description="dialog.tipo === 'reabrir' ? 'La comanda vuelve a En proceso. Queda registrado.' : 'El ítem se cancela, el producto queda agotado en la carta y el mesero recibe el aviso.'"
                  :options="dialog.tipo === 'reabrir' ? ['Faltó algo', 'Se despachó por error'] : ['Agotado', 'Sin insumo']"
                  :confirm-label="dialog.tipo === 'reabrir' ? 'Reabrir' : 'Marcar agotado'"
                  @close="dialog.open = false" @confirm="confirmar" />
  </div>
</template>

<style scoped>
.kds {
  --kds-fondo: #161b1d;
  --kds-barra: #20272a;
  --kds-texto: #eef1ef;
  --kds-suave: #9aa5a9;
  min-height: 100dvh;
  background: var(--kds-fondo);
  color: var(--kds-texto);
}

.kds.claro {
  --kds-fondo: var(--fondo);
  --kds-barra: var(--superficie);
  --kds-texto: var(--tinta);
  --kds-suave: var(--acero);
}

.barra {
  position: sticky;
  top: 0;
  z-index: 5;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--kds-barra);
  border-bottom: 1px solid rgba(127, 138, 144, 0.3);
}

.titulo {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.titulo h1 {
  font-size: var(--text-2xl);
  font-stretch: 65%;
}

.volver {
  display: grid;
  place-items: center;
  width: var(--toque);
  height: var(--toque);
  font-size: 2rem;
  text-decoration: none;
  color: var(--kds-suave);
}

.tabs {
  display: flex;
  gap: var(--space-2);
}

.tab {
  min-height: var(--toque-grande);
  padding: 0 var(--space-5);
  border: 2px solid transparent;
  border-radius: var(--radio);
  background: transparent;
  color: var(--kds-suave);
  font-size: var(--text-lg);
  font-weight: 700;
  cursor: pointer;
}

.tab[aria-selected='true'] {
  color: var(--kds-texto);
  border-color: var(--kds-texto);
}

.contador {
  display: inline-block;
  min-width: 1.8em;
  margin-left: var(--space-1);
  padding: 0 0.4em;
  border-radius: 999px;
  background: var(--kds-texto);
  color: var(--kds-fondo);
}

.ajustes {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.ajuste,
.filtro {
  min-height: 2.75rem;
  padding: 0 var(--space-3);
  border: 1px solid rgba(127, 138, 144, 0.5);
  border-radius: var(--radio);
  background: transparent;
  color: var(--kds-texto);
  font: inherit;
  font-size: var(--text-sm);
  cursor: pointer;
}

.filtro option {
  color: var(--tinta);
}

.ajuste[aria-pressed='true'] {
  border-color: var(--kds-texto);
}

.riel {
  padding: var(--space-4);
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(17rem, 1fr));
  align-items: start;
  gap: var(--space-4);
}

.vacio {
  padding: var(--space-7) var(--space-4);
  text-align: center;
  color: var(--kds-suave);
  font-size: var(--text-lg);
}

@media (max-width: 40rem) {
  .tabs {
    order: 3;
    width: 100%;
  }

  .tab {
    flex: 1;
    padding: 0 var(--space-2);
  }
}
</style>
