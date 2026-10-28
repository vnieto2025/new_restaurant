<script setup>
import { ref, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'
import { usePrintStore } from '@/stores/print'
import { formatMoney, formatDate } from '@/utils/format'
import StatusChip from '@/components/StatusChip.vue'

/*
  Lo que le corresponde a cada persona: sus liquidaciones aprobadas de propinas o de entregas, con su detalle y
  ajustes (RN-PRP-05). Solo ve lo suyo.
*/
const printer = usePrintStore()
const { quiet } = useAction()
const datos = ref(null)

const MEDIOS = { efectivo: 'efectivo', transferencia: 'transferencia', otro: 'otro medio' }

onMounted(async () => {
  datos.value = await quiet(() => postData('/liquidacion/mias'))
})

function imprimir(fila) {
  printer.print('liquidacion', { liquidacion: fila.liquidacion, linea: fila })
}
</script>

<template>
  <div class="mias">
    <header class="page-head">
      <div>
        <h1>Mis propinas y pagos</h1>
        <p>Lo que te corresponde en cada periodo liquidado y si ya te lo pagaron.</p>
      </div>
      <RouterLink class="btn btn-secundario" :to="{ name: 'inicio', query: { menu: 1 } }">Volver</RouterLink>
    </header>

    <template v-if="datos">
      <section v-if="datos.periodo_actual.propinas_mesas" class="panel actual">
        <p class="muted">Periodo actual · {{ formatDate(datos.periodo_actual.desde) }} al {{ formatDate(datos.periodo_actual.hasta) }}</p>
        <p class="grande">Tus mesas llevan {{ formatMoney(datos.periodo_actual.propinas_mesas) }} en propinas por liquidar</p>
        <p class="muted">En {{ datos.periodo_actual.cuentas }} cuentas. Lo que te toca se conoce al liquidar el periodo{{
          datos.periodo_actual.modelo !== 'individual' ? ', porque una parte se reparte entre el equipo' : '' }}.</p>
      </section>

      <article v-for="fila in datos.liquidaciones" :key="fila.id" class="panel liquidacion">
        <header>
          <div>
            <h2>{{ fila.liquidacion.tipo === 'propinas' ? 'Propinas' : 'Entregas' }} · {{ formatDate(fila.liquidacion.desde) }} al {{ formatDate(fila.liquidacion.hasta) }}</h2>
            <StatusChip :estado="fila.pagado_en ? 'pagada' : 'aprobada'" :label="fila.pagado_en ? `Pagado en ${MEDIOS[fila.medio_pago] || fila.medio_pago}` : 'Por pagar'" size="sm" />
          </div>
          <p class="total">{{ formatMoney(fila.total) }}</p>
        </header>
        <dl class="detalle">
          <template v-if="fila.liquidacion.tipo === 'propinas'">
            <div v-if="fila.individual"><dt>De tus mesas</dt><dd>{{ formatMoney(fila.individual) }}</dd></div>
            <div><dt>Del pozo del equipo</dt><dd>{{ formatMoney(fila.pozo) }}</dd></div>
            <div v-if="fila.peso"><dt>Horas · puntos</dt><dd>{{ fila.horas }} h · {{ fila.peso }}</dd></div>
          </template>
          <template v-else>
            <div><dt>{{ fila.entregas }} entregas</dt><dd>{{ formatMoney(fila.pago_entregas) }}</dd></div>
            <div v-if="fila.propinas"><dt>Propinas</dt><dd>{{ formatMoney(fila.propinas) }}</dd></div>
            <div v-if="fila.descuentos"><dt>Faltantes de rendiciones</dt><dd>−{{ formatMoney(fila.descuentos) }}</dd></div>
          </template>
          <div v-for="a in fila.detalle.ajustes || []" :key="a.motivo + a.valor"><dt>Ajuste: {{ a.motivo }}</dt><dd>{{ formatMoney(a.valor) }}</dd></div>
        </dl>
        <button v-if="fila.pagado_en" class="btn btn-secundario btn-sm" type="button" @click="imprimir(fila)">Imprimir comprobante</button>
      </article>
      <p v-if="!datos.liquidaciones.length" class="empty">Todavía no hay liquidaciones aprobadas para ti.</p>
    </template>
  </div>
</template>

<style scoped>
.mias {
  max-width: 48rem;
  margin: 0 auto;
  padding: var(--space-6) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.actual,
.liquidacion {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.grande {
  font-size: var(--text-xl);
  font-weight: 700;
}

.liquidacion header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-3);
}

.liquidacion h2 {
  font-size: var(--text-lg);
  margin-bottom: var(--space-1);
}

.total {
  font-size: var(--text-2xl);
  font-weight: 800;
  font-stretch: 75%;
  white-space: nowrap;
}

.detalle {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.detalle div {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  border-bottom: 1px solid var(--linea);
  padding: var(--space-1) 0;
}

.detalle dd {
  margin: 0;
  font-variant-numeric: tabular-nums;
}

.liquidacion .btn {
  align-self: flex-start;
}
</style>
