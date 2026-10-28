<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useToastStore } from '@/stores/toast'
import { useAuthStore } from '@/stores/auth'
import { usePrintStore } from '@/stores/print'
import { useRealtime } from '@/composables/useRealtime'
import { useAction } from '@/composables/useAction'
import { useDraft } from '@/composables/useDraft'
import { formatMoney, formatTime, CANALES } from '@/utils/format'
import OpsBar from '@/components/OpsBar.vue'
import ConnectionBanner from '@/components/ConnectionBanner.vue'
import MenuPicker from '@/components/MenuPicker.vue'
import CartPanel from '@/components/CartPanel.vue'
import ClienteCaptura from '@/components/ClienteCaptura.vue'
import EntregaCaptura from '@/components/EntregaCaptura.vue'
import AvisosPendientes from '@/components/AvisosPendientes.vue'
import EnlacePago from '@/components/EnlacePago.vue'
import StatusChip from '@/components/StatusChip.vue'

/*
  Mostrador (doc 17, flujo C): órdenes de la mesa externa, identificadas por número y nombre del cliente.
  Aquí también llegan las que el cliente hace con el QR de "para llevar". Con el módulo de domicilios,
  la orden puede salir a domicilio con zona de envío y dirección (doc 15B).
*/
const toast = useToastStore()
const auth = useAuthStore()
const printer = usePrintStore()
const { busy, attempt } = useAction()
const draft = useDraft('mostrador')

const externa = ref(null)
const carta = ref(null)
const ordenes = ref([])
const vista = ref('nueva')
const zonas = ref([])
const refresco = ref(0)
const enlacePago = ref(null)
const puedeEnlace = computed(() => auth.modulos.has('pagos_linea') && auth.can('pagos_linea.cobrar'))
const avisosPorEnviar = ref(0)
const avisa = computed(() => auth.can(['notificaciones.enviar', 'notificaciones.configurar']))
const clienteEncontrado = ref(null)

const conDomicilios = computed(() => auth.modulos.has('domicilios') && zonas.value.length > 0)
const tipo = computed({
  get: () => draft.draft.value.tipo || 'llevar',
  set: (valor) => { draft.draft.value.tipo = valor },
})
if (!draft.draft.value.entrega) draft.draft.value.entrega = entregaVacia()
const entrega = computed({
  get: () => draft.draft.value.entrega,
  set: (valor) => { draft.draft.value.entrega = valor },
})
const esDomicilio = computed(() => conDomicilios.value && tipo.value === 'domicilio')
const valorPedido = computed(() => draft.lineas.value.reduce((s, l) => s + l.precio * l.cantidad, 0))
const tarifa = computed(() => zonas.value.find((z) => z.id === Number(entrega.value.zona_envio_id))?.tarifa || 0)

function entregaVacia() {
  return { zona_envio_id: '', direccion: '', barrio: '', indicaciones: '', guardar_direccion: true }
}

// Nombre en el borrador; celular y autorización junto a él
const datosCliente = computed({
  get: () => ({
    cliente_nombre: draft.draft.value.cliente_nombre,
    cliente_telefono: draft.draft.value.cliente_telefono || '',
    acepta_datos: !!draft.draft.value.acepta_datos,
  }),
  set: (valor) => Object.assign(draft.draft.value, valor),
})

const activas = computed(() => ordenes.value.filter((o) => o.mesa_tipo === 'externa'))
const listas = computed(() => activas.value.filter((o) => o.estado === 'lista'))

async function load() {
  try {
    if (!externa.value) {
      const mesas = await postData('/mesa/list', { incluir_externa: true })
      externa.value = mesas.find((m) => m.tipo === 'externa')
    }
    if (externa.value && !carta.value) carta.value = await postData('/orden/carta', { mesa_id: externa.value.id })
    if (auth.modulos.has('domicilios') && !zonas.value.length) zonas.value = await postData('/domicilio/zona/list').catch(() => [])
    ordenes.value = await postData('/orden/list')
    if (avisa.value) avisosPorEnviar.value = (await postData('/notificacion/pendientes').catch(() => [])).length
  } catch (error) {
    toast.error(error.message)
  }
}

async function reloadMenu() {
  if (externa.value) carta.value = await postData('/orden/carta', { mesa_id: externa.value.id }).catch(() => carta.value)
}

function onEvent(event) {
  if (event.tipo === 'producto.agotado') reloadMenu()
  load()
  refresco.value += 1
}

const { status, online } = useRealtime(['ordenes'], { onEvent, onSync: load })

async function enviar() {
  const nombre = draft.draft.value.cliente_nombre.trim()
  if (!nombre) {
    toast.error('Escribe el nombre del cliente para identificar la orden.')
    return
  }
  if (esDomicilio.value) {
    const e = entrega.value
    if (!draft.draft.value.cliente_telefono || !e.direccion.trim() || !e.zona_envio_id) {
      toast.error('Un domicilio necesita celular, dirección y zona de envío.')
      return
    }
  }
  const orden = await attempt(() => postData('/orden/create', {
    mesa_id: externa.value.id,
    clave_idempotencia: draft.draft.value.clave,
    cliente_nombre: nombre,
    cliente_telefono: draft.draft.value.cliente_telefono || null,
    acepta_datos: !!draft.draft.value.acepta_datos,
    notas: draft.draft.value.notas || null,
    items: draft.items(),
    entrega: esDomicilio.value ? {
      ...entrega.value, zona_envio_id: Number(entrega.value.zona_envio_id),
      barrio: entrega.value.barrio.trim() || null, indicaciones: entrega.value.indicaciones.trim() || null,
    } : null,
  }))
  if (!orden) return
  toast.success(`${esDomicilio.value ? 'Domicilio' : 'Orden'} ${orden.numero_texto} de ${nombre} enviado a cocina.`)
  draft.clear()
  draft.draft.value.entrega = entregaVacia()
  clienteEncontrado.value = null
  load()
}

async function entregar(orden) {
  await attempt(() => postData('/orden/entregar', { orden_id: orden.id }), { success: `${orden.numero_texto} entregada a ${orden.cliente_nombre}.` })
  load()
}

async function imprimir(orden) {
  const tirilla = await attempt(() => postData('/orden/tirilla', { orden_id: orden.id }))
  if (tirilla) printer.print('orden', tirilla)
}

onMounted(load)
</script>

<template>
  <div class="mostrador">
    <OpsBar title="Mostrador" />
    <ConnectionBanner :status="status" :online="online" />

    <div class="vistas" role="tablist">
      <button role="tab" type="button" :aria-selected="vista === 'nueva'" @click="vista = 'nueva'">Orden nueva</button>
      <button role="tab" type="button" :aria-selected="vista === 'pedidos'" @click="vista = 'pedidos'">
        Pedidos <span v-if="activas.length">({{ activas.length }})</span>
        <span v-if="listas.length" class="listos">{{ listas.length }} listos</span>
        <span v-if="avisosPorEnviar" class="listos">{{ avisosPorEnviar }} por avisar</span>
      </button>
    </div>

    <div v-if="vista === 'nueva'" class="layout">
      <MenuPicker :categorias="carta?.categorias || []" :cantidades="draft.cantidades.value" @add="draft.add" />
      <aside class="lado">
        <div v-if="conDomicilios" class="tipo" role="radiogroup" aria-label="Tipo de pedido">
          <button type="button" role="radio" :aria-checked="tipo === 'llevar'" @click="tipo = 'llevar'">Para llevar</button>
          <button type="button" role="radio" :aria-checked="tipo === 'domicilio'" @click="tipo = 'domicilio'">Domicilio</button>
        </div>
        <ClienteCaptura v-model="datosCliente" :telefono-obligatorio="esDomicilio" @cliente="clienteEncontrado = $event" />
        <EntregaCaptura v-if="esDomicilio" v-model="entrega" :zonas="zonas" :direcciones="clienteEncontrado?.direcciones || []"
                        :valor-pedido="valorPedido" :puede-guardar="!!clienteEncontrado?.acepta_datos || !!datosCliente.acepta_datos" />
        <CartPanel :lineas="draft.lineas.value" :titulo="esDomicilio ? 'Domicilio' : 'Para llevar'" @change="draft.change" @remove="draft.remove">
          <div v-if="draft.lineas.value.length" class="field">
            <label for="notas-m">Nota para cocina</label>
            <input id="notas-m" v-model="draft.draft.value.notas" class="input" maxlength="300" placeholder="Opcional">
          </div>
          <p v-if="esDomicilio && tarifa" class="envio">
            <span>Domicilio</span><strong>{{ formatMoney(tarifa) }}</strong>
          </p>
          <p v-if="esDomicilio && tarifa" class="envio total-envio">
            <span>Total con domicilio</span><strong>{{ formatMoney(valorPedido + tarifa) }}</strong>
          </p>
          <button class="btn btn-grande btn-bloque" type="button" :disabled="busy || !draft.lineas.value.length || !online"
                  :aria-busy="busy" @click="enviar">{{ busy ? 'Enviando…' : 'Enviar a cocina' }}</button>
        </CartPanel>
      </aside>
    </div>

    <main v-else class="pedidos">
      <AvisosPendientes v-if="avisa" class="avisos-ancho" :refresco="refresco" @cuenta="avisosPorEnviar = $event" />
      <p v-if="!activas.length" class="empty">No hay pedidos externos pendientes.</p>
      <article v-for="orden in activas" :key="orden.id" class="pedido" :class="{ lista: orden.estado === 'lista' }">
        <div class="pedido-head">
          <span class="numero">{{ orden.numero_texto }}</span>
          <div class="quien">
            <strong>{{ orden.cliente_nombre || 'Sin nombre' }}</strong>
            <span class="muted">{{ CANALES[orden.canal] }} · {{ formatTime(orden.creado_en) }}</span>
          </div>
          <StatusChip :estado="orden.estado" size="lg" />
        </div>
        <p class="detalle">{{ orden.items.filter((i) => i.estado !== 'cancelado').map((i) => `${i.cantidad} ${i.nombre}`).join(', ') }}</p>
        <div class="pedido-pie">
          <strong>{{ formatMoney(orden.total) }}</strong>
          <div class="actions">
            <button class="btn btn-secundario" type="button" :disabled="busy" @click="imprimir(orden)">Imprimir</button>
            <button v-if="puedeEnlace" class="btn btn-secundario" type="button" @click="enlacePago = orden.sesion_mesa_id">Enlace de pago</button>
            <RouterLink v-if="auth.modulos.has('caja') && auth.can(['caja.cobrar', 'caja.cobrar_externas'])" class="btn btn-secundario"
                        :to="{ name: 'caja' }">Cobrar en caja</RouterLink>
            <RouterLink v-if="orden.canal === 'domicilio' && auth.can('domicilios.despachar')" class="btn" :to="{ name: 'entregas' }">
              Ver entrega</RouterLink>
            <button v-else-if="orden.items.some((i) => i.estado === 'despachado')" class="btn" type="button" :disabled="busy"
                    @click="entregar(orden)">Entregado al cliente</button>
          </div>
        </div>
      </article>
    </main>
    <EnlacePago v-if="enlacePago" :sesion-mesa-id="enlacePago" @close="enlacePago = null" />
  </div>
</template>

<style scoped>
.mostrador {
  min-height: 100dvh;
}

.vistas {
  display: flex;
  background: var(--superficie);
  border-bottom: 1px solid var(--linea);
}

.vistas [role='tab'] {
  flex: 1;
  min-height: var(--toque-grande);
  border: none;
  border-bottom: 3px solid transparent;
  background: transparent;
  font-weight: 700;
  font-size: var(--text-lg);
  cursor: pointer;
}

.vistas [aria-selected='true'] {
  border-bottom-color: var(--accion);
}

.tipo {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px;
  padding: 2px;
  border-radius: var(--radio-sm);
  background: var(--linea);
}

.tipo button {
  min-height: var(--toque);
  border: none;
  border-radius: calc(var(--radio-sm) - 2px);
  background: var(--superficie);
  font-weight: 700;
  cursor: pointer;
}

.tipo [aria-checked='true'] {
  background: var(--tinta);
  color: #fff;
}

.envio {
  display: flex;
  justify-content: space-between;
  font-variant-numeric: tabular-nums;
}

.total-envio {
  font-size: var(--text-lg);
}

.listos {
  margin-left: var(--space-2);
  padding: 0.1em 0.6em;
  border-radius: 999px;
  background: var(--estado-despachado-suave);
  font-size: var(--text-sm);
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 24rem;
  align-items: start;
  gap: var(--space-4);
  padding: var(--space-4);
}

.lado {
  position: sticky;
  top: 4.5rem;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--superficie);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
}

.pedidos {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(20rem, 1fr));
  gap: var(--space-3);
  padding: var(--space-4);
}

.avisos-ancho {
  grid-column: 1 / -1;
}

.pedido {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--superficie);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
}

.pedido.lista {
  border: 2px solid var(--estado-despachado);
}

.pedido-head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.numero {
  font-size: var(--text-2xl);
  font-weight: 800;
  font-stretch: 62%;
}

.quien {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.quien strong {
  font-size: var(--text-lg);
}

.pedido-pie {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
}

@media (max-width: 52rem) {
  .layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .lado {
    position: static;
  }
}
</style>
