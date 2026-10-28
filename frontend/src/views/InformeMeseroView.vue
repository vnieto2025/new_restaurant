<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { usePrintStore } from '@/stores/print'
import { formatMoney, formatTime, formatDateLong, formatDateTime, plural } from '@/utils/format'

/*
  Informe diario por mesero (doc 08A, sección 3): atención, ventas, excepciones y detalle por mesa.
  Es una herramienta de gestión. El mesero ve solo el suyo.
*/
const route = useRoute()
const auth = useAuthStore()
const printer = usePrintStore()
const { quiet } = useAction()
const informe = ref(null)

const propio = computed(() => !auth.can('reportes.ver'))

async function cargar() {
  informe.value = await quiet(() => postData('/reporte/mesero', {
    usuario_id: route.query.usuario_id ? Number(route.query.usuario_id) : null,
    desde: route.query.desde || null,
    hasta: route.query.hasta || route.query.desde || null,
  }))
}

watch(() => route.query, cargar)
onMounted(cargar)
</script>

<template>
  <div class="informe" :class="{ suelto: propio }">
    <header class="page-head">
      <div>
        <h1>{{ informe?.mesero || 'Informe' }}</h1>
        <p v-if="informe">{{ informe.desde === informe.hasta ? formatDateLong(informe.desde) : `${formatDateLong(informe.desde)} al ${formatDateLong(informe.hasta)}` }}</p>
      </div>
      <div class="actions no-print">
        <RouterLink v-if="propio" class="btn btn-secundario" :to="{ name: 'inicio' }">Volver</RouterLink>
        <button class="btn btn-secundario" type="button" :disabled="!informe" @click="printer.printPage()">Imprimir</button>
      </div>
    </header>

    <template v-if="informe">
      <dl class="cifras">
        <div><dt>Mesas atendidas</dt><dd>{{ informe.atencion.mesas }}</dd></div>
        <div><dt>Órdenes</dt><dd>{{ informe.atencion.ordenes }}</dd></div>
        <div><dt>Ítems</dt><dd>{{ informe.atencion.items }}</dd></div>
        <div><dt>Vendido</dt><dd>{{ formatMoney(informe.ventas.total) }}</dd></div>
        <div><dt>Ticket por mesa</dt><dd>{{ formatMoney(informe.ventas.ticket_promedio) }}</dd></div>
        <div><dt>Propinas en sus cuentas</dt><dd>{{ formatMoney(informe.ventas.propinas) }}</dd></div>
      </dl>

      <section class="panel bloque">
        <h2>Turnos</h2>
        <p v-if="!informe.turnos.length" class="muted">Sin turnos registrados.</p>
        <p v-for="(t, i) in informe.turnos" :key="i">
          <template v-if="t.fin">De {{ formatTime(t.inicio) }} a {{ formatTime(t.fin) }}</template>
          <template v-else>Desde {{ formatTime(t.inicio) }}, en curso</template>
          <span v-if="t.cierre_automatico" class="muted"> (cerrado al cerrar la jornada)</span>
        </p>
      </section>

      <section class="panel bloque">
        <h2>Detalle por mesa</h2>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>Mesa</th><th>Abierta</th><th>Cerrada</th><th>Órdenes</th><th class="num">Total</th><th>Cobro</th></tr></thead>
            <tbody>
              <tr v-for="(m, i) in informe.mesas" :key="i">
                <td>{{ m.mesa }}</td><td>{{ formatTime(m.abierta_en) }}</td><td>{{ m.cerrada_en ? formatTime(m.cerrada_en) : '—' }}</td>
                <td>{{ m.ordenes.join(', ') }}</td><td class="num">{{ formatMoney(m.total) }}</td>
                <td>{{ m.cuenta === 'pagada' ? m.medios.join(', ') || 'Pagada' : m.cuenta === 'anulada' ? 'Anulada' : 'Sin cobrar' }}</td>
              </tr>
            </tbody>
          </table>
          <p v-if="!informe.mesas.length" class="empty">Sin mesas atendidas.</p>
        </div>
      </section>

      <section class="panel bloque">
        <h2>Excepciones</h2>
        <p v-if="informe.excepciones.mesas_sin_cobrar">{{ plural(informe.excepciones.mesas_sin_cobrar, 'mesa') }} sin cobrar.</p>
        <p v-if="!informe.excepciones.cancelaciones.length" class="muted">Sin cancelaciones.</p>
        <ul v-else class="lista">
          <li v-for="(c, i) in informe.excepciones.cancelaciones" :key="i">
            {{ formatDateTime(c.momento) }} · {{ c.orden }} {{ c.mesa }} · {{ c.cantidad }} × {{ c.producto }} ({{ formatMoney(c.valor) }}) · {{ c.motivo }} · {{ c.usuario }}
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>

<style scoped>
.informe.suelto {
  max-width: 64rem;
  margin: 0 auto;
  padding: var(--space-6) var(--space-4);
}

.cifras {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: var(--space-3);
  margin: 0 0 var(--space-5);
}

.cifras div {
  padding: var(--space-3) var(--space-4);
  background: var(--superficie);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
}

.cifras dt {
  color: var(--acero);
  font-size: var(--text-sm);
}

.cifras dd {
  margin: var(--space-1) 0 0;
  font-size: var(--text-xl);
  font-weight: 800;
  font-stretch: 72%;
}

.bloque {
  padding: var(--space-4);
  margin-bottom: var(--space-4);
}

.bloque h2 {
  font-size: var(--text-lg);
  margin-bottom: var(--space-3);
}

.lista {
  margin: 0;
  padding-left: var(--space-5);
}
</style>
