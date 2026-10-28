<script setup>
import { ref, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { formatMoney, formatDateTime, formatDate, isoDate } from '@/utils/format'
import AppModal from '@/components/AppModal.vue'

/*
  Pagos en línea (doc 20A): pasarela del restaurante, pagos recibidos, reembolsos y conciliación contra
  el reporte de la pasarela (monto, comisión, neto y fecha de abono).
*/
const auth = useAuthStore()
const { busy, attempt, quiet } = useAction()

const vista = ref(auth.can('pagos_linea.conciliar') ? 'pagos' : 'config')
const config = ref(null)
const form = ref(null)
const datos = ref({ pagos: [], resumen: {} })
const filtros = ref({ estado: '', desde: isoDate(new Date(Date.now() - 6 * 86400000)), hasta: '' })
const reembolso = ref(null)
const conciliacion = ref(null)

const ESTADOS = { pendiente: 'Esperando pago', aprobado: 'Aprobado', rechazado: 'Rechazado', expirado: 'Expirado',
  reembolsado: 'Reembolsado', parcial: 'Reembolsado en parte', por_reembolsar: 'Con saldo por devolver' }

async function loadConfig() {
  const c = await quiet(() => postData('/pago_linea/config/get'))
  if (!c) return
  config.value = c
  form.value = { activo: c.activo, pasarela: c.pasarela, ambiente: c.ambiente, permitir_propina: c.permitir_propina,
    minutos_expiracion: c.minutos_expiracion, modo: c.modo_simulada }
}

async function loadPagos() {
  const body = Object.fromEntries(Object.entries(filtros.value).filter(([, v]) => v))
  datos.value = (await quiet(() => postData('/pago_linea/list', body))) || { pagos: [], resumen: {} }
}

async function guardar() {
  const f = form.value
  const ok = await attempt(() => postData('/pago_linea/config/save', {
    activo: f.activo, pasarela: f.pasarela, ambiente: f.ambiente, permitir_propina: f.permitir_propina,
    minutos_expiracion: Number(f.minutos_expiracion) || 30, credenciales: f.pasarela === 'simulada' ? { modo: f.modo } : null,
  }), { success: 'Pagos en línea guardados.' })
  if (ok) loadConfig()
}

async function reembolsar() {
  const r = reembolso.value
  const ok = await attempt(() => postData('/pago_linea/reembolsar', { intento_pago_id: r.pago.id, monto: Number(r.monto) || null,
    motivo: r.motivo.trim() }), { success: 'Reembolso solicitado a la pasarela.' })
  if (ok) {
    reembolso.value = null
    loadPagos()
  }
}

async function conciliar() {
  const c = conciliacion.value
  const ok = await attempt(() => postData('/pago_linea/conciliar', { intento_pago_id: c.pago.id, fecha_abono: c.fecha_abono,
    comision: c.comision === '' || c.comision === null ? null : Number(c.comision), nota: c.nota.trim() || null }),
  { success: 'Pago conciliado.' })
  if (ok) {
    conciliacion.value = null
    loadPagos()
  }
}

onMounted(() => {
  if (auth.can('pagos_linea.configurar')) loadConfig()
  if (auth.can(['pagos_linea.conciliar', 'pagos_linea.reembolsar'])) loadPagos()
})
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Pagos en línea</h1>
        <p>Los clientes pagan desde el celular con el QR de la mesa o con el enlace de su pedido.</p>
      </div>
    </header>

    <div class="vistas" role="tablist">
      <button v-if="auth.can(['pagos_linea.conciliar', 'pagos_linea.reembolsar'])" role="tab" type="button"
              :aria-selected="vista === 'pagos'" @click="vista = 'pagos'">Pagos y conciliación</button>
      <button v-if="auth.can('pagos_linea.configurar')" role="tab" type="button" :aria-selected="vista === 'config'"
              @click="vista = 'config'">Pasarela</button>
    </div>

    <section v-if="vista === 'pagos'">
      <form class="filtros" @submit.prevent="loadPagos">
        <select v-model="filtros.estado" class="select" aria-label="Estado">
          <option value="">Todos los estados</option>
          <option v-for="(label, valor) in ESTADOS" :key="valor" :value="valor">{{ label }}</option>
        </select>
        <input v-model="filtros.desde" class="input" type="date" aria-label="Desde">
        <input v-model="filtros.hasta" class="input" type="date" aria-label="Hasta">
        <button class="btn btn-secundario" type="submit">Filtrar</button>
      </form>

      <dl class="resumen">
        <div><dt>Recibido</dt><dd>{{ formatMoney(datos.resumen.bruto || 0) }}</dd></div>
        <div><dt>Comisiones</dt><dd>{{ formatMoney(datos.resumen.comision || 0) }}</dd></div>
        <div><dt>Reembolsado</dt><dd>{{ formatMoney(datos.resumen.reembolsado || 0) }}</dd></div>
        <div class="fuerte"><dt>Neto</dt><dd>{{ formatMoney(datos.resumen.neto || 0) }}</dd></div>
        <div v-if="datos.resumen.por_reembolsar" class="alerta"><dt>Por devolver</dt><dd>{{ formatMoney(datos.resumen.por_reembolsar) }}</dd></div>
        <div><dt>Sin abono confirmado</dt><dd>{{ datos.resumen.sin_abono || 0 }}</dd></div>
      </dl>

      <div class="panel table-wrap">
        <table class="table">
          <thead><tr><th>Fecha</th><th>Cuenta</th><th>Estado</th><th class="num">Monto</th><th class="num">Comisión</th><th>Abono</th><th></th></tr></thead>
          <tbody>
            <tr v-for="p in datos.pagos" :key="p.id">
              <td class="nowrap">{{ formatDateTime(p.hora_local || p.creado_en) }}<small class="muted bloque">{{ p.referencia }}</small></td>
              <td>{{ p.mesa }}<small class="muted bloque">{{ p.cuenta_numero || (p.cuenta_estado === 'abierta' ? 'Cuenta abierta' : '') }}
                · {{ p.origen === 'qr' ? 'QR de la mesa' : 'Enlace' }}</small></td>
              <td>{{ p.estado_texto }}
                <small v-if="p.excedente > p.reembolsado && p.reembolsable" class="alerta-texto bloque">Devolver {{ formatMoney(p.reembolsable) }}</small>
                <small v-if="p.motivo_reembolso" class="muted bloque">{{ p.motivo_reembolso }}</small></td>
              <td class="num">{{ formatMoney(p.monto) }}<small v-if="p.propina" class="muted bloque">propina {{ formatMoney(p.propina) }}</small></td>
              <td class="num">{{ p.comision === null ? '—' : formatMoney(p.comision) }}</td>
              <td>{{ p.fecha_abono ? formatDate(p.fecha_abono) : '—' }}</td>
              <td><div class="actions">
                <button v-if="['aprobado', 'reembolsado', 'parcial'].includes(p.estado) && auth.can('pagos_linea.conciliar')" class="btn btn-secundario btn-sm"
                        type="button" @click="conciliacion = { pago: p, fecha_abono: p.fecha_abono || isoDate(new Date()), comision: p.comision ?? '', nota: p.nota_conciliacion || '' }">
                  Conciliar</button>
                <button v-if="p.reembolsable && auth.can('pagos_linea.reembolsar')" class="btn btn-secundario btn-sm" type="button"
                        @click="reembolso = { pago: p, monto: p.reembolsable, motivo: '' }">Reembolsar</button>
              </div></td>
            </tr>
          </tbody>
        </table>
        <p v-if="!datos.pagos.length" class="empty">No hay pagos en línea con ese filtro.</p>
      </div>
      <p class="muted nota">Para devolver un pago que ya está abonado a una cuenta, primero anula ese pago o la cuenta en caja.</p>
    </section>

    <form v-else-if="form" class="panel config" @submit.prevent="guardar">
      <p v-if="!config.contratado" class="aviso">El restaurante no tiene contratado el módulo de pagos en línea.</p>
      <label class="check"><input v-model="form.activo" type="checkbox"> Recibir pagos en línea</label>
      <div class="form-grid">
        <div class="field"><label for="pl-pasarela">Pasarela</label>
          <select id="pl-pasarela" v-model="form.pasarela" class="select">
            <option v-for="p in config.pasarelas" :key="p" :value="p">{{ p === 'simulada' ? 'Simulada (pruebas)' : p }}</option>
          </select></div>
        <div class="field"><label for="pl-ambiente">Ambiente</label>
          <select id="pl-ambiente" v-model="form.ambiente" class="select">
            <option value="pruebas">Pruebas</option>
            <option value="produccion">Producción</option>
          </select></div>
        <div v-if="form.pasarela === 'simulada'" class="field"><label for="pl-modo">La pasarela simulada</label>
          <select id="pl-modo" v-model="form.modo" class="select">
            <option value="normal">Responde normal</option>
            <option value="caido">No responde</option>
          </select></div>
        <div class="field"><label for="pl-min">Minutos para completar el pago</label>
          <input id="pl-min" v-model.number="form.minutos_expiracion" class="input" type="number" min="5" max="1440"></div>
      </div>
      <label class="check"><input v-model="form.permitir_propina" type="checkbox"> El cliente puede agregar propina al pagar</label>
      <p class="muted">Cada restaurante usa su propia cuenta en la pasarela: el dinero llega directo al restaurante.
        Credenciales {{ config.tiene_credenciales ? 'guardadas: no se muestran' : 'sin configurar' }}.</p>
      <div class="form-actions"><button class="btn" type="submit" :disabled="busy">Guardar</button></div>
    </form>

    <AppModal :open="!!reembolso" title="Reembolsar pago en línea" width="28rem" @close="reembolso = null">
      <form v-if="reembolso" @submit.prevent="reembolsar">
        <p>Se puede devolver hasta <strong>{{ formatMoney(reembolso.pago.reembolsable) }}</strong> por la pasarela.</p>
        <div class="field espacio"><label for="rb-monto">Valor a devolver</label>
          <input id="rb-monto" v-model.number="reembolso.monto" class="input" type="number" min="1" :max="reembolso.pago.reembolsable"></div>
        <div class="field espacio"><label for="rb-motivo">Motivo</label>
          <input id="rb-motivo" v-model="reembolso.motivo" class="input" maxlength="200" required></div>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="reembolso = null">Volver</button>
          <button class="btn btn-peligro" type="submit" :disabled="busy || reembolso.motivo.trim().length < 3">Reembolsar</button>
        </div>
      </form>
    </AppModal>

    <AppModal :open="!!conciliacion" title="Conciliar con la pasarela" width="28rem" @close="conciliacion = null">
      <form v-if="conciliacion" @submit.prevent="conciliar">
        <p class="muted">Según el reporte de la pasarela: cuándo abonó este pago y cuánto cobró de comisión.</p>
        <div class="field espacio"><label for="cn-fecha">Fecha de abono</label>
          <input id="cn-fecha" v-model="conciliacion.fecha_abono" class="input" type="date" required></div>
        <div class="field espacio"><label for="cn-com">Comisión</label>
          <input id="cn-com" v-model="conciliacion.comision" class="input" type="number" min="0" inputmode="numeric"></div>
        <div class="field espacio"><label for="cn-nota">Nota</label>
          <input id="cn-nota" v-model="conciliacion.nota" class="input" maxlength="200" placeholder="Opcional"></div>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="conciliacion = null">Volver</button>
          <button class="btn" type="submit" :disabled="busy || !conciliacion.fecha_abono">Guardar</button>
        </div>
      </form>
    </AppModal>
  </div>
</template>

<style scoped>
.vistas {
  display: flex;
  margin-bottom: var(--space-4);
  border-bottom: 1px solid var(--linea);
}

.vistas [role='tab'] {
  min-height: var(--toque);
  padding: 0 var(--space-4);
  border: none;
  border-bottom: 3px solid transparent;
  background: transparent;
  font-weight: 700;
  cursor: pointer;
}

.vistas [aria-selected='true'] {
  border-bottom-color: var(--accion);
}

.filtros {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.filtros .input,
.filtros .select {
  width: auto;
  flex: 1 1 10rem;
  max-width: 16rem;
}

.resumen {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr));
  gap: var(--space-3);
  margin: 0 0 var(--space-4);
}

.resumen div {
  padding: var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio-sm);
  background: var(--superficie);
}

.resumen dt {
  color: var(--acero);
  font-size: var(--text-sm);
}

.resumen dd {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.resumen .fuerte {
  border-color: var(--accion);
}

.resumen .alerta {
  border-left: 4px solid var(--estado-pendiente);
}

.alerta-texto {
  color: var(--estado-cancelado);
  font-weight: 600;
}

.config {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
}

.aviso {
  padding: var(--space-2) var(--space-3);
  border-left: 4px solid var(--estado-pendiente);
  border-radius: var(--radio-sm);
  background: var(--estado-pendiente-suave);
}

.nowrap {
  white-space: nowrap;
}

.bloque {
  display: block;
}

.espacio {
  margin-top: var(--space-3);
}

.nota {
  margin-top: var(--space-2);
}
</style>
