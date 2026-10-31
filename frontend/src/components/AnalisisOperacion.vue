<script setup>
import { ref, computed, watch } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { formatMoney, formatMoneyShort, formatDate, formatChange } from '@/utils/format'

/*
  Reportes de la fase 2 (doc 26, sección 5): horas pico, tiempos, domiciliarios, clientes, inventario y sedes.
  El mapa de calor usa un solo tono de claro a oscuro, con el valor escrito en cada celda, así no depende del color.
*/
const props = defineProps({ desde: { type: String, required: true }, hasta: { type: String, required: true } })
const auth = useAuthStore()
const { quiet } = useAction()

const datos = ref(null)
const sedes = ref(null)
const DIAS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

const horas = computed(() => [...new Set((datos.value?.horas.celdas || []).map((c) => c.hora))].sort((a, b) => a - b))
const celda = computed(() => Object.fromEntries((datos.value?.horas.celdas || []).map((c) => [`${c.dia}-${c.hora}`, c])))
const pico = computed(() => {
  const celdas = datos.value?.horas.celdas || []
  return celdas.length ? celdas.reduce((a, b) => (b.ventas > a.ventas ? b : a)) : null
})

function intensidad(c) {
  if (!c || !datos.value.horas.maximo) return null
  return Math.round(12 + (c.ventas / datos.value.horas.maximo) * 88)
}

function estilo(c) {
  const nivel = intensidad(c)
  if (nivel === null) return {}
  return { background: `color-mix(in srgb, var(--grafica) ${nivel}%, var(--superficie))`, color: nivel > 55 ? '#fff' : 'var(--tinta)' }
}

function etiquetaHora(hora) {
  return `${hora % 12 || 12} ${hora < 12 ? 'a. m.' : 'p. m.'}`
}

async function cargar() {
  const cuerpo = { desde: props.desde, hasta: props.hasta }
  const [a, s] = await Promise.all([
    quiet(() => postData('/reporte/analisis', cuerpo)),
    auth.roles.includes('admin_empresa') && auth.restaurantes.length > 1 ? quiet(() => postData('/reporte/sedes', cuerpo)) : Promise.resolve(null),
  ])
  datos.value = a
  sedes.value = s
}

watch(() => [props.desde, props.hasta], cargar, { immediate: true })
</script>

<template>
  <div v-if="datos" class="analisis">
    <section v-if="sedes" class="panel bloque">
      <h2>Comparativo entre restaurantes</h2>
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>Restaurante</th><th class="num">Ventas</th><th class="num">%</th><th class="num">Cuentas</th><th class="num">Ticket promedio</th><th class="num">Frente al periodo anterior</th></tr></thead>
          <tbody>
            <tr v-for="r in sedes.restaurantes" :key="r.nombre">
              <td>{{ r.nombre }}</td><td class="num">{{ formatMoney(r.ventas) }}</td><td class="num">{{ r.participacion }}</td><td class="num">{{ r.cuentas }}</td>
              <td class="num">{{ formatMoney(r.ticket_promedio) }}</td><td class="num">{{ r.variacion_ventas === null ? '—' : formatChange(r.variacion_ventas) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel bloque">
      <h2>Horas pico</h2>
      <p v-if="!pico" class="empty">Sin ventas en este periodo.</p>
      <template v-else>
        <p class="muted">Lo más fuerte: {{ DIAS[pico.dia] }} a las {{ etiquetaHora(pico.hora) }}, con {{ formatMoney(pico.ventas) }}.</p>
        <div class="table-wrap">
          <table class="calor">
            <caption class="visually-hidden">Ventas por día de la semana y hora</caption>
            <thead><tr><th scope="col"><span class="visually-hidden">Día</span></th><th v-for="h in horas" :key="h" scope="col">{{ etiquetaHora(h) }}</th></tr></thead>
            <tbody>
              <tr v-for="(dia, d) in DIAS" :key="dia">
                <th scope="row">{{ dia }}</th>
                <td v-for="h in horas" :key="h" :style="estilo(celda[`${d}-${h}`])"
                    :title="celda[`${d}-${h}`] ? `${dia} ${etiquetaHora(h)}: ${formatMoney(celda[`${d}-${h}`].ventas)}, ${celda[`${d}-${h}`].cuentas} cuentas` : `${dia} ${etiquetaHora(h)}: sin ventas`">
                  {{ celda[`${d}-${h}`] ? formatMoneyShort(celda[`${d}-${h}`].ventas) : '' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </section>

    <section v-if="datos.tiempos" class="panel bloque">
      <h2>Tiempos de preparación</h2>
      <p v-if="!datos.tiempos.length" class="empty">Aún no hay comandas despachadas en este periodo.</p>
      <div v-else class="table-wrap">
        <table class="table">
          <thead><tr><th>Punto</th><th class="num">Ítems</th><th class="num">Promedio</th><th class="num">9 de cada 10 en menos de</th></tr></thead>
          <tbody>
            <tr v-for="t in datos.tiempos" :key="t.nombre"><td>{{ t.nombre }}</td><td class="num">{{ t.cantidad }}</td><td class="num">{{ t.promedio }} min</td><td class="num">{{ t.p90 }} min</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="datos.domiciliarios" class="panel bloque">
      <h2>Domiciliarios</h2>
      <p v-if="!datos.domiciliarios.length" class="empty">Sin domicilios en este periodo.</p>
      <div v-else class="table-wrap">
        <table class="table">
          <thead><tr><th>Domiciliario</th><th class="num">Entregas</th><th class="num">Fallidas</th><th class="num">Minutos en camino</th><th class="num">Pago por zona</th></tr></thead>
          <tbody>
            <tr v-for="d in datos.domiciliarios" :key="d.nombre"><td>{{ d.nombre }}</td><td class="num">{{ d.entregadas }}</td><td class="num">{{ d.fallidas }}</td>
              <td class="num">{{ d.minutos_promedio ?? '—' }}</td><td class="num">{{ formatMoney(d.pago) }}</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel bloque">
      <h2>Clientes</h2>
      <dl class="cifras">
        <div><dt>Registrados</dt><dd>{{ datos.clientes.total }}</dd></div>
        <div><dt>Nuevos en el periodo</dt><dd>{{ datos.clientes.nuevos }}</dd></div>
        <div><dt>Frecuentes (2 o más órdenes)</dt><dd>{{ datos.clientes.frecuentes_cantidad }}</dd></div>
        <div><dt>Sin comprar hace {{ datos.clientes.dias_inactivo }} días</dt><dd>{{ datos.clientes.inactivos }}</dd></div>
      </dl>
      <div v-if="datos.clientes.frecuentes.length || datos.clientes.por_recuperar.length" class="dos">
        <div v-if="datos.clientes.frecuentes.length">
          <h3>Los más frecuentes</h3>
          <ul><li v-for="c in datos.clientes.frecuentes" :key="c.nombre">{{ c.nombre }} · {{ c.ordenes }} órdenes · {{ formatMoney(c.valor) }}</li></ul>
        </div>
        <div v-if="datos.clientes.por_recuperar.length">
          <h3>Para recuperar</h3>
          <ul><li v-for="c in datos.clientes.por_recuperar" :key="c.nombre">{{ c.nombre }} · última compra {{ formatDate(c.ultima_compra) }}</li></ul>
        </div>
      </div>
    </section>

    <section v-if="datos.inventario" class="panel bloque">
      <h2>Inventario</h2>
      <div class="dos">
        <div>
          <h3>En el mínimo o por debajo</h3>
          <p v-if="!datos.inventario.criticos.length" class="muted">Ninguno.</p>
          <ul v-else><li v-for="i in datos.inventario.criticos" :key="i.nombre">{{ i.nombre }}: {{ i.stock }} {{ i.unidad }} (mínimo {{ i.minimo }})</li></ul>
        </div>
        <div>
          <h3>Mermas · {{ formatMoney(datos.inventario.valor_mermas) }}</h3>
          <p v-if="!datos.inventario.mermas.length" class="muted">Sin mermas en este periodo.</p>
          <ul v-else><li v-for="m in datos.inventario.mermas" :key="m.nombre">{{ m.nombre }}: {{ m.cantidad }} · {{ formatMoney(m.valor) }}</li></ul>
        </div>
        <div>
          <h3>Costos que cambiaron</h3>
          <p v-if="!datos.inventario.variacion_costos.length" class="muted">Sin cambios entre compras del periodo.</p>
          <ul v-else><li v-for="v in datos.inventario.variacion_costos" :key="v.nombre">{{ v.nombre }}: {{ formatMoney(v.antes) }} → {{ formatMoney(v.despues) }} ({{ formatChange(v.variacion) }})</li></ul>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.analisis {
  --grafica: #2b5f8a;
}

.bloque {
  margin-bottom: var(--space-5);
  padding: var(--space-4);
}

.bloque h2 {
  margin-bottom: var(--space-2);
  font-size: var(--text-lg);
}

.bloque h3 {
  font-size: var(--text-base, 1rem);
  margin-bottom: var(--space-1);
}

.calor {
  border-collapse: separate;
  border-spacing: 2px;
  font-size: var(--text-sm);
}

.calor th {
  padding: var(--space-1);
  font-weight: 600;
  white-space: nowrap;
}

.calor td {
  min-width: 3.25rem;
  height: 2.25rem;
  padding: 0 var(--space-1);
  border-radius: 4px;
  background: var(--fondo);
  text-align: center;
  white-space: nowrap;
}

.cifras {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: var(--space-3);
  margin: var(--space-2) 0;
}

.cifras dt {
  color: var(--acero);
  font-size: var(--text-sm);
}

.cifras dd {
  margin: 0;
  font-size: var(--text-xl);
  font-weight: 700;
}

.dos {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
  gap: var(--space-4);
  margin-top: var(--space-3);
}

.dos ul {
  margin: 0;
  padding-left: var(--space-4);
}
</style>
