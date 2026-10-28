<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useRealtime } from '@/composables/useRealtime'
import { useAction } from '@/composables/useAction'
import { formatMoney, formatTime, formatChange, plural, CANALES } from '@/utils/format'
import StatusChip from '@/components/StatusChip.vue'
import ConnectionBanner from '@/components/ConnectionBanner.vue'

// Lo que está pasando ahora en el restaurante: órdenes con algo pendiente y estado de recepción
const auth = useAuthStore()
const { busy, attempt } = useAction()

const ordenes = ref([])
const vista = ref('activas')
const restaurante = ref(null)
const error = ref('')
const tablero = ref(null)

const GRUPOS = [
  { estado: 'pendiente_aprobacion', titulo: 'Por aprobar' },
  { estado: 'nueva', titulo: 'Nuevas' },
  { estado: 'en_proceso', titulo: 'En proceso' },
  { estado: 'lista', titulo: 'Listas para entregar' },
]

const resumen = computed(() => GRUPOS.map((g) => ({ ...g, cantidad: ordenes.value.filter((o) => o.estado === g.estado).length })))
const vendido = computed(() => ordenes.value.filter((o) => o.estado !== 'cancelada').reduce((s, o) => s + o.total, 0))

async function load() {
  if (auth.can('reportes.ver')) {
    tablero.value = await postData('/reporte/dashboard').catch(() => tablero.value)
  }
  if (!auth.can('ordenes.ver')) return
  try {
    ordenes.value = await postData('/orden/list', { vista: vista.value })
    if (auth.can(['restaurante.configurar', 'restaurante.pausar'])) restaurante.value = await postData('/restaurante/get')
    error.value = ''
  } catch (e) {
    error.value = e.message
  }
}

const { status, online } = useRealtime(auth.can('ordenes.ver') ? ['ordenes'] : [], { onEvent: load, onSync: load })

async function cambiarVista(valor) {
  vista.value = valor
  await load()
}

async function pausar(estado) {
  const data = await attempt(() => postData('/restaurante/change_status', {
    estado,
    mensaje_carta: estado === 'pausado' ? 'Estamos atendiendo muchos pedidos. Vuelve a intentarlo en unos minutos.' : null,
  }), { success: estado === 'pausado' ? 'Pedidos por QR en pausa.' : 'Recibiendo pedidos por QR de nuevo.' })
  if (data) restaurante.value = data
}

onMounted(load)
</script>

<template>
  <div>
    <ConnectionBanner :status="status" :online="online" />
    <header class="page-head">
      <div>
        <h1>Hoy</h1>
        <p>{{ vista === 'activas' ? 'Órdenes con algo pendiente' : 'Todas las órdenes de la jornada' }}</p>
      </div>
      <div class="actions">
        <button class="btn btn-secundario" type="button" :aria-pressed="vista === 'jornada'"
                @click="cambiarVista(vista === 'activas' ? 'jornada' : 'activas')">
          {{ vista === 'activas' ? 'Ver toda la jornada' : 'Ver solo pendientes' }}
        </button>
        <template v-if="restaurante && auth.can('restaurante.pausar')">
          <button v-if="restaurante.estado === 'activo'" class="btn btn-peligro" type="button" :disabled="busy" @click="pausar('pausado')">
            Pausar pedidos por QR
          </button>
          <button v-else class="btn" type="button" :disabled="busy" @click="pausar('activo')">Reanudar pedidos por QR</button>
        </template>
      </div>
    </header>

    <p v-if="restaurante && restaurante.estado !== 'activo'" class="pausa" role="status">
      El restaurante está {{ restaurante.estado }}: los clientes no pueden pedir por QR. Las tablets siguen funcionando.
    </p>

    <section v-if="tablero" class="tablero">
      <div class="venta">
        <p class="muted">Ventas de hoy</p>
        <p class="cifra">{{ formatMoney(tablero.hoy.ventas) }}</p>
        <p v-if="tablero.comparativo.variacion_ventas !== null" class="comparacion">{{ formatChange(tablero.comparativo.variacion_ventas) }}
          <span class="muted">vs {{ formatMoney(tablero.comparativo.ventas) }} el mismo día de la semana pasada</span></p>
        <p v-else class="muted">El mismo día de la semana pasada no hubo ventas para comparar.</p>
        <p class="muted">{{ plural(tablero.hoy.cuentas, 'cuenta') }} · ticket promedio {{ formatMoney(tablero.hoy.ticket_promedio) }}</p>
      </div>
      <div v-if="tablero.caja" class="dato">
        <p class="muted">Caja</p>
        <p class="fuerte">{{ tablero.caja.turno_abierto ? `Turno de ${tablero.caja.cajero}` : 'Sin turno abierto' }}</p>
        <p v-if="tablero.caja.turno_abierto" class="muted">Efectivo esperado {{ formatMoney(tablero.caja.efectivo_esperado) }}</p>
        <p class="muted">{{ plural(tablero.caja.por_cobrar, 'mesa o pedido', 'mesas o pedidos') }} por cobrar</p>
      </div>
      <div class="dato">
        <p class="muted">Lo más pedido hoy</p>
        <p v-for="p in tablero.productos_del_dia" :key="p.nombre">{{ p.unidades }} × {{ p.nombre }}</p>
        <p v-if="!tablero.productos_del_dia.length" class="muted">Aún nada.</p>
      </div>
      <div v-if="tablero.agotados.length" class="dato">
        <p class="muted">Agotados</p>
        <p v-for="nombre in tablero.agotados" :key="nombre">{{ nombre }}</p>
      </div>
    </section>

    <p v-if="!auth.can('ordenes.ver')" class="empty">Tu rol no incluye ver las órdenes. Usa el menú para administrar.</p>
    <p v-else-if="error" class="empty">{{ error }}</p>

    <template v-else>
      <dl class="resumen">
        <div v-for="grupo in resumen" :key="grupo.estado">
          <dt><StatusChip :estado="grupo.estado" /></dt>
          <dd>{{ grupo.cantidad }}</dd>
        </div>
        <div v-if="vista === 'jornada'">
          <dt>Total de la jornada</dt>
          <dd>{{ formatMoney(vendido) }}</dd>
        </div>
      </dl>

      <div class="panel table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>Orden</th><th>Mesa o cliente</th><th>Canal</th><th>Mesero</th><th>Hora</th><th>Estado</th><th class="num">Total</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="orden in ordenes" :key="orden.id">
              <td><strong>{{ orden.numero_texto }}</strong></td>
              <td>{{ orden.mesa_tipo === 'externa' ? orden.cliente_nombre || orden.mesa : `${orden.mesa} · ${orden.zona}` }}</td>
              <td>{{ CANALES[orden.canal] }}</td>
              <td>{{ orden.mesero || '—' }}</td>
              <td>{{ formatTime(orden.creado_en) }}</td>
              <td><StatusChip :estado="orden.estado" /></td>
              <td class="num">{{ formatMoney(orden.total) }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="!ordenes.length" class="empty">
          {{ vista === 'activas' ? 'No hay órdenes pendientes en este momento.' : 'Todavía no hay órdenes en esta jornada.' }}
        </p>
      </div>
    </template>
  </div>
</template>

<style scoped>
.resumen {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: var(--space-3);
  margin: 0 0 var(--space-5);
}

.resumen div {
  padding: var(--space-4);
  background: var(--superficie);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
}

.resumen dt {
  color: var(--acero);
  font-size: var(--text-sm);
}

.resumen dd {
  margin: var(--space-2) 0 0;
  font-size: var(--text-2xl);
  font-weight: 800;
  font-stretch: 70%;
}

.tablero {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 14rem), 1fr));
  gap: var(--space-3);
  margin-bottom: var(--space-5);
}

.tablero > div {
  padding: var(--space-4);
  background: var(--superficie);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
}

.cifra {
  font-size: var(--text-3xl);
  font-weight: 800;
  font-stretch: 65%;
  line-height: 1.1;
}

.comparacion {
  font-weight: 600;
  margin: var(--space-1) 0;
}

.fuerte {
  font-weight: 700;
  font-size: var(--text-lg);
}

.pausa {
  margin-bottom: var(--space-5);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radio);
  border: 2px dashed var(--tinta);
  background: var(--superficie);
}
</style>
