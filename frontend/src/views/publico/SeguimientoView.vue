<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { postData } from '@/services/api'
import { formatMoney, formatTime } from '@/utils/format'
import StatusChip from '@/components/StatusChip.vue'

/*
  Seguimiento del pedido del cliente (doc 17, flujo B). Sondeo corto con límite:
  se detiene cuando el pedido se entregó o se canceló (doc 31, sección 6).
*/
const props = defineProps({ seguimiento: { type: String, required: true } })

const POLL_MS = 6000
const pedido = ref(null)
const error = ref('')
let timer = null

const PASOS = [
  { estados: ['pendiente_aprobacion'], label: 'Recibido' },
  { estados: ['nueva', 'en_proceso'], label: 'En preparación' },
  { estados: ['lista'], label: 'Listo' },
  { estados: ['entregada'], label: 'Entregado' },
]

// Un domicilio sigue después de la cocina: sale con el domiciliario y llega (doc 17A, sección 2.6)
const PASOS_DOMICILIO = [
  { estados: ['pendiente_aprobacion'], label: 'Recibido' },
  { estados: ['nueva', 'en_proceso', 'lista'], label: 'En preparación' },
  { estados: ['en_camino'], label: 'En camino' },
  { estados: ['entregada'], label: 'Entregado' },
]

const MENSAJES = {
  pendiente_aprobacion: 'El mesero confirmará tu pedido en un momento.',
  nueva: 'La cocina ya recibió tu pedido.',
  en_proceso: 'Estamos preparando tu pedido.',
  lista: 'Tu pedido está listo.',
  entregada: '¡Buen provecho!',
  cancelada: 'Tu pedido fue cancelado. Si es un error, pregúntale al personal.',
}

const MENSAJES_DOMICILIO = {
  ...MENSAJES,
  pendiente_aprobacion: 'El restaurante confirmará tu pedido en un momento.',
  lista: 'Tu pedido está listo y sale en breve.',
  en_camino: 'Tu pedido va en camino.',
  cancelada: 'Tu pedido fue cancelado. Si es un error, llama al restaurante.',
}

const entrega = computed(() => pedido.value?.entrega)

// Estado que ve el cliente: el de la cocina, completado con el de la entrega en un domicilio
const estado = computed(() => {
  if (!pedido.value) return null
  const e = entrega.value
  if (e?.estado === 'en_camino') return 'en_camino'
  if (e?.estado === 'entregada') return 'entregada'
  if (e?.estado === 'fallida') return 'cancelada'
  return pedido.value.estado
})

const pasos = computed(() => (entrega.value ? PASOS_DOMICILIO : PASOS))
const paso = computed(() => pasos.value.findIndex((p) => p.estados.includes(estado.value)))
const mensaje = computed(() => (entrega.value ? MENSAJES_DOMICILIO : MENSAJES)[estado.value])
const envio = computed(() => (entrega.value && entrega.value.estado !== 'fallida' ? entrega.value.tarifa : 0))

const terminado = computed(() => ['entregada', 'cancelada'].includes(estado.value))

async function load() {
  try {
    pedido.value = await postData('/publico/orden/estado', { seguimiento: props.seguimiento })
    error.value = ''
    if (terminado.value) clearInterval(timer)
  } catch (e) {
    error.value = e.message
  }
}

function onVisible() {
  if (document.visibilityState === 'visible' && !terminado.value) load()
}

onMounted(() => {
  load()
  timer = setInterval(() => document.visibilityState === 'visible' && load(), POLL_MS)
  document.addEventListener('visibilitychange', onVisible)
})

onBeforeUnmount(() => {
  clearInterval(timer)
  document.removeEventListener('visibilitychange', onVisible)
})
</script>

<template>
  <div class="seguimiento">
    <header class="cabecera">
      <p v-if="pedido" class="lugar">{{ entrega ? `Domicilio · ${pedido.cliente_nombre}` : pedido.mesa_tipo === 'externa' ? pedido.cliente_nombre || pedido.mesa : `${pedido.zona} · ${pedido.mesa}` }}</p>
      <h1>{{ pedido?.restaurante || 'Tu pedido' }}</h1>
    </header>

    <main class="cuerpo">
      <p v-if="error && !pedido" class="aviso">{{ error }}</p>

      <template v-if="pedido">
        <section class="estado" aria-live="polite">
          <p class="numero">Pedido {{ pedido.numero_texto }}</p>
          <p class="mensaje">{{ mensaje }}</p>

          <ol v-if="estado !== 'cancelada'" class="pasos">
            <li v-for="(item, index) in pasos" :key="item.label"
                :class="{ hecho: index < paso, actual: index === paso }">
              {{ item.label }}
            </li>
          </ol>
        </section>

        <ul class="items">
          <li v-for="(item, index) in pedido.items" :key="index">
            <span class="item-nombre" :class="{ tachado: item.estado === 'cancelado' }">
              {{ item.cantidad }} × {{ item.nombre }}
              <small v-if="item.modificadores?.length">{{ item.modificadores.join(', ') }}</small>
              <small v-if="item.motivo">{{ item.motivo }}</small>
            </span>
            <StatusChip :estado="item.estado" size="sm" />
          </li>
        </ul>
        <p v-if="entrega" class="subtotal"><span>Domicilio</span><span>{{ formatMoney(envio) }}</span></p>
        <p class="total"><span>Total</span><strong>{{ formatMoney(pedido.total + envio) }}</strong></p>
        <p v-if="entrega" class="destino">
          Entrega en <strong>{{ entrega.direccion }}</strong><template v-if="entrega.barrio"> · {{ entrega.barrio }}</template>
          <template v-if="entrega.forma_pago === 'contra_entrega' && estado !== 'cancelada'"><br>Pagas al recibir.</template>
        </p>
        <p class="muted hora">Esta página se actualiza sola. Pediste a las {{ formatTime(pedido.creado_en) }}</p>

        <RouterLink v-if="pedido.pago_en_linea && estado !== 'cancelada'" class="btn btn-bloque"
                    :to="{ name: 'pagar', query: { seguimiento } }">Pagar en línea</RouterLink>
        <RouterLink v-if="$route.query.q" class="btn btn-secundario btn-bloque" :to="{ name: 'carta', params: { token: $route.query.q } }">
          Pedir algo más
        </RouterLink>
      </template>
    </main>
  </div>
</template>

<style scoped>
.seguimiento {
  min-height: 100dvh;
  background: var(--papel);
}

.cabecera {
  padding: var(--space-6) var(--space-4) var(--space-4);
  background: var(--tinta);
  color: #fff;
}

.lugar {
  color: #c4ccd0;
  font-weight: 600;
}

.cabecera h1 {
  font-size: var(--text-3xl);
  font-stretch: 68%;
  line-height: 1;
  margin-top: var(--space-1);
}

.cuerpo {
  max-width: 34rem;
  margin: 0 auto;
  padding: var(--space-5) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.numero {
  font-size: var(--text-3xl);
  font-weight: 800;
  font-stretch: 62%;
  line-height: 1;
}

.mensaje {
  margin-top: var(--space-2);
  font-size: var(--text-lg);
}

/* Los pasos sí son una secuencia: recibido -> preparación -> listo -> entregado */
.pasos {
  list-style: none;
  margin: var(--space-5) 0 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-1);
}

.pasos li {
  padding-top: var(--space-2);
  border-top: 6px solid var(--linea);
  color: var(--acero);
  font-size: var(--text-sm);
  font-weight: 600;
}

.pasos li.hecho {
  border-top-color: var(--tinta);
  color: var(--tinta);
}

.pasos li.actual {
  border-top-color: var(--accion);
  color: var(--accion);
}

.items {
  list-style: none;
  margin: 0;
  padding: var(--space-4) 0 0;
  border-top: 1px dashed var(--linea-fuerte);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.items li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.item-nombre small {
  display: block;
  color: var(--acero);
}

.tachado {
  text-decoration: line-through;
  color: var(--acero);
}

.total {
  display: flex;
  justify-content: space-between;
  font-size: var(--text-lg);
}

.hora {
  font-size: var(--text-sm);
}

.subtotal {
  display: flex;
  justify-content: space-between;
  color: var(--acero);
}

.destino {
  padding: var(--space-3);
  border-radius: var(--radio-sm);
  background: var(--superficie);
  border: 1px solid var(--linea);
}

.aviso {
  padding: var(--space-5);
  border-radius: var(--radio);
  background: var(--superficie);
  text-align: center;
}
</style>
