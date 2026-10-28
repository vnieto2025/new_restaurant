<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { usePrintStore } from '@/stores/print'
import { formatMoney, formatTime, plural } from '@/utils/format'
import AppModal from '@/components/AppModal.vue'

/*
  Turno de caja (doc 20, sección 2): resumen en vivo, gastos, retiros y aportes, cierre con arqueo
  y, para el administrador, cierre de la jornada (sección 8).
*/
const props = defineProps({
  turno: { type: Object, default: null },
})
const emit = defineEmits(['changed'])

const auth = useAuthStore()
const printer = usePrintStore()
const { busy, attempt, quiet } = useAction()

const movimiento = ref(null)
const cierre = ref(null)
const jornada = ref(null)

const MOVIMIENTOS = {
  gasto: 'Registrar gasto',
  retiro: 'Retirar efectivo',
  aporte: 'Agregar efectivo',
}

const diferencia = computed(() => cierre.value && cierre.value.contado !== null && cierre.value.contado !== ''
  ? Number(cierre.value.contado) - props.turno.resumen.efectivo_esperado : null)

async function loadJornada() {
  if (auth.can('caja.cerrar_jornada')) jornada.value = await quiet(() => postData('/caja/jornada/estado'))
}

async function guardarMovimiento() {
  const ok = await attempt(() => postData('/caja/movimiento/create', movimiento.value),
    { success: 'Movimiento registrado.' })
  if (ok) {
    movimiento.value = null
    emit('changed')
  }
}

async function cerrarTurno(confirmar = false) {
  const body = { efectivo_contado: Number(cierre.value.contado), observacion: cierre.value.observacion || null,
    confirmar_pendientes: confirmar }
  // Si hay cuentas a medio pagar, el servidor lo avisa y se puede confirmar con el otro botón
  const turno = await attempt(() => postData('/caja/turno/cerrar', body), { success: (t) => t.diferencia === 0
    ? 'Turno cerrado. El efectivo cuadra.' : `Turno cerrado con diferencia de ${formatMoney(t.diferencia)}.` })
  if (!turno) return
  cierre.value = null
  printer.print('turno', turno)
  emit('changed')
  loadJornada()
}

async function cerrarJornada() {
  const ok = await attempt(() => postData('/caja/jornada/cerrar'), { success: 'Jornada cerrada.' })
  if (ok) {
    loadJornada()
    emit('changed')
  }
}

onMounted(loadJornada)
</script>

<template>
  <section class="turno-panel">
    <template v-if="turno">
      <header class="cabeza">
        <div>
          <h2>Turno de {{ turno.usuario }}</h2>
          <p class="muted">Abierto a las {{ formatTime(turno.abierto_en) }} con {{ formatMoney(turno.fondo_inicial) }} de base</p>
        </div>
        <button v-if="auth.can('caja.turno')" class="btn btn-peligro" type="button"
                @click="cierre = { contado: '', observacion: '' }">Cerrar turno</button>
      </header>

      <dl class="cifras">
        <div><dt>Cuentas cobradas</dt><dd>{{ turno.resumen.cuentas }}</dd></div>
        <div><dt>Ventas</dt><dd>{{ formatMoney(turno.resumen.ventas) }}</dd></div>
        <div><dt>Propinas</dt><dd>{{ formatMoney(turno.resumen.propinas) }}</dd></div>
        <div><dt>Efectivo esperado en caja</dt><dd>{{ formatMoney(turno.resumen.efectivo_esperado) }}</dd></div>
      </dl>

      <div class="panel table-wrap">
        <table class="table">
          <thead><tr><th>Medio</th><th class="num">Pagos</th><th class="num">Valor</th></tr></thead>
          <tbody>
            <tr v-for="fila in turno.resumen.por_medio" :key="fila.medio">
              <td>{{ fila.medio }}</td><td class="num">{{ fila.pagos }}</td><td class="num">{{ formatMoney(fila.monto) }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="!turno.resumen.por_medio.length" class="empty">Aún no hay cobros en este turno.</p>
      </div>

      <div v-if="auth.can('caja.movimientos')" class="actions">
        <button v-for="(label, tipo) in MOVIMIENTOS" :key="tipo" class="btn btn-secundario" type="button"
                @click="movimiento = { tipo, monto: null, concepto: '' }">{{ label }}</button>
      </div>

      <ul v-if="turno.resumen.movimientos.length" class="movimientos">
        <li v-for="m in turno.resumen.movimientos" :key="m.id">
          <span>{{ formatTime(m.creado_en) }} · {{ m.concepto }} <small class="muted">({{ m.tipo }}, {{ m.usuario }})</small></span>
          <strong>{{ m.tipo === 'aporte' ? '+' : '−' }}{{ formatMoney(m.monto) }}</strong>
        </li>
      </ul>
    </template>

    <section v-if="jornada" class="jornada panel">
      <h3>Jornada {{ jornada.jornada }}</h3>
      <p v-if="jornada.cerrada" class="muted">Cerrada. Ventas: {{ formatMoney(jornada.resumen.ventas) }} en {{ plural(jornada.resumen.cuentas, 'cuenta') }}.</p>
      <template v-else>
        <p class="muted">Ventas hasta ahora: {{ formatMoney(jornada.resumen.ventas) }} en {{ plural(jornada.resumen.cuentas, 'cuenta') }}.</p>
        <ul class="bloqueos">
          <li v-if="jornada.bloqueos.turnos_abiertos">Falta cerrar el turno de caja.</li>
          <li v-if="jornada.bloqueos.mesas_abiertas">{{ plural(jornada.bloqueos.mesas_abiertas, 'mesa') }} sin cobrar.</li>
          <li v-if="jornada.bloqueos.pedidos_externos_abiertos">{{ plural(jornada.bloqueos.pedidos_externos_abiertos, 'pedido para llevar', 'pedidos para llevar') }} sin cobrar.</li>
        </ul>
        <button class="btn" type="button" :disabled="busy || Object.values(jornada.bloqueos).some(Boolean)" @click="cerrarJornada">
          Cerrar la jornada
        </button>
        <p class="muted nota">Al cerrar no se reciben más órdenes ni cobros hasta la próxima jornada.</p>
      </template>
    </section>

    <AppModal :open="!!movimiento" :title="movimiento ? MOVIMIENTOS[movimiento.tipo] : ''" width="26rem" @close="movimiento = null">
      <form v-if="movimiento" @submit.prevent="guardarMovimiento">
        <div class="field">
          <label for="mov-monto">Valor</label>
          <input id="mov-monto" v-model.number="movimiento.monto" class="input" type="number" min="1" required inputmode="numeric">
        </div>
        <div class="field espacio">
          <label for="mov-concepto">Concepto</label>
          <input id="mov-concepto" v-model="movimiento.concepto" class="input" required minlength="3" maxlength="200"
                 placeholder="Hielo, gas, retiro para el banco…">
        </div>
        <div class="form-actions">
          <button class="btn" type="submit" :disabled="busy">Registrar</button>
        </div>
      </form>
    </AppModal>

    <AppModal :open="!!cierre" title="Cerrar turno" width="28rem" @close="cierre = null">
      <form v-if="cierre" @submit.prevent="cerrarTurno(false)">
        <p class="muted">Cuenta el efectivo del cajón, incluida la base.</p>
        <div class="field espacio">
          <label for="contado">Efectivo contado</label>
          <input id="contado" v-model.number="cierre.contado" class="input" type="number" min="0" required inputmode="numeric">
        </div>
        <p v-if="diferencia !== null" class="diferencia" :class="{ cuadra: diferencia === 0 }">
          {{ diferencia === 0 ? 'Cuadra exacto.' : diferencia > 0 ? `Sobran ${formatMoney(diferencia)}.` : `Faltan ${formatMoney(-diferencia)}.` }}
        </p>
        <div class="field espacio">
          <label for="obs">Observación</label>
          <input id="obs" v-model="cierre.observacion" class="input" maxlength="250" placeholder="Opcional">
        </div>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" :disabled="busy" @click="cerrarTurno(true)">Cerrar con cuentas a medio pagar</button>
          <button class="btn btn-peligro" type="submit" :disabled="busy">Cerrar turno</button>
        </div>
      </form>
    </AppModal>
  </section>
</template>

<style scoped>
.turno-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.cabeza {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-3);
}

.cifras {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: var(--space-3);
  margin: 0;
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
  font-stretch: 75%;
}

.movimientos {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.movimientos li {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
}

.jornada {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  align-items: flex-start;
}

.bloqueos {
  margin: 0;
  padding-left: var(--space-5);
}

.nota {
  font-size: var(--text-sm);
}

.espacio {
  margin-top: var(--space-3);
}

.diferencia {
  margin-top: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radio-sm);
  background: var(--estado-cancelado-suave);
  font-weight: 700;
}

.diferencia.cuadra {
  background: var(--estado-entregado-suave);
}
</style>
