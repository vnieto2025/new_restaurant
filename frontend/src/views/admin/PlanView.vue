<script setup>
import { ref, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'
import { formatMoney, formatDate } from '@/utils/format'

/*
  Plan del restaurante (doc 42): módulos contratados, complementos que puede agregar, estado de la cuenta del
  servicio y pagos registrados. Los cambios de plan y los pagos los gestiona soporte.
*/
const { quiet } = useAction()
const plan = ref(null)
const MEDIOS = { transferencia: 'Transferencia', efectivo: 'Efectivo', tarjeta: 'Tarjeta', otro: 'Otro' }
const CONTRATO = { prueba: 'En prueba', activo: 'Activo', suspendido: 'Suspendido', cancelado: 'Cancelado' }

onMounted(async () => {
  plan.value = await quiet(() => postData('/restaurante/plan'))
})
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Mi plan</h1>
        <p>Lo que tienes contratado y el estado de tu cuenta con nosotros.</p>
      </div>
    </header>

    <template v-if="plan">
      <section class="resumen">
        <div class="panel tarjeta">
          <p class="muted">Plan</p>
          <p class="grande">{{ plan.plan_nombre }}</p>
          <p class="muted">Contrato {{ CONTRATO[plan.estado_contrato]?.toLowerCase() }} desde {{ formatDate(plan.fecha_inicio) }}</p>
        </div>
        <div class="panel tarjeta" :class="plan.cuenta.estado">
          <p class="muted">Tu cuenta</p>
          <p class="grande">{{ plan.cuenta.texto }}</p>
          <p v-if="plan.proximo_vencimiento" class="muted">Próximo pago: {{ formatDate(plan.proximo_vencimiento) }}
            <template v-if="plan.mensualidad"> · {{ formatMoney(plan.mensualidad) }}</template></p>
        </div>
      </section>
      <p v-if="plan.cuenta.estado === 'en_mora'" class="aviso">
        Tu pago está pendiente. Escríbenos para ponerte al día y evitar la suspensión del servicio. Tus datos nunca se pierden.</p>

      <div class="columnas">
        <section class="panel bloque">
          <h2>Módulos incluidos</h2>
          <ul class="lista">
            <li v-for="m in plan.modulos" :key="m.codigo">{{ m.nombre }}</li>
          </ul>
        </section>
        <section v-if="plan.complementos_disponibles.length" class="panel bloque">
          <h2>Puedes agregar</h2>
          <ul class="lista">
            <li v-for="m in plan.complementos_disponibles" :key="m.codigo">{{ m.nombre }}</li>
          </ul>
          <p class="muted">Para activarlos, escríbele a soporte.</p>
        </section>
      </div>

      <section class="panel bloque">
        <h2>Pagos</h2>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>Fecha</th><th>Periodo</th><th class="num">Valor</th><th>Medio</th><th>Factura</th></tr></thead>
            <tbody>
              <tr v-for="p in plan.pagos" :key="p.id">
                <td>{{ formatDate(p.fecha) }}</td>
                <td>{{ formatDate(p.periodo_desde) }} a {{ formatDate(p.periodo_hasta) }}</td>
                <td class="num">{{ formatMoney(p.valor) }}</td>
                <td>{{ MEDIOS[p.medio] || p.medio }}</td>
                <td>{{ p.factura || '—' }}</td>
              </tr>
            </tbody>
          </table>
          <p v-if="!plan.pagos.length" class="empty">Aún no hay pagos registrados.</p>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.resumen,
.columnas {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.tarjeta,
.bloque {
  padding: var(--space-4);
}

.bloque {
  margin-bottom: var(--space-4);
}

.bloque h2 {
  font-size: var(--text-lg);
  margin-bottom: var(--space-2);
}

.grande {
  font-size: var(--text-2xl);
  font-weight: 800;
  font-stretch: 75%;
}

.tarjeta.en_mora {
  border-left: 6px solid var(--estado-cancelado);
}

.tarjeta.por_vencer {
  border-left: 6px solid var(--estado-pendiente);
}

.tarjeta.al_dia {
  border-left: 6px solid var(--estado-entregado);
}

.lista {
  margin: 0;
  padding-left: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.aviso {
  margin-bottom: var(--space-4);
  padding: var(--space-3);
  border-left: 4px solid var(--estado-cancelado);
  border-radius: var(--radio-sm);
  background: var(--estado-cancelado-suave);
}
</style>
