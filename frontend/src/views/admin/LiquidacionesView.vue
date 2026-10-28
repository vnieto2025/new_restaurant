<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { usePrintStore } from '@/stores/print'
import { formatMoney, formatDate } from '@/utils/format'
import AppModal from '@/components/AppModal.vue'
import StatusChip from '@/components/StatusChip.vue'

/*
  Propinas y pago a domiciliarios por periodo (doc 26A): vista del periodo abierto, borrador editable,
  aprobación que congela y pago con comprobante. El sistema calcula según las reglas del restaurante;
  el pago se hace por fuera.
*/
const auth = useAuthStore()
const printer = usePrintStore()
const { busy, attempt, quiet } = useAction()

const MODELOS = { individual: 'Individual: al mesero', colectiva: 'Colectiva: pozo del equipo', mixta: 'Mixta: mesero y pozo' }
const METODOS = { horas_puntos: 'Horas × puntos del rol', horas: 'Horas trabajadas', puntos: 'Puntos del rol' }
const PAGOS = { zona: 'Valor fijo según la zona', porcentaje: 'Porcentaje del envío', mixto: 'Base más porcentaje' }
const MEDIOS = { efectivo: 'Efectivo', transferencia: 'Transferencia', otro: 'Otro' }

const config = ref(null)
const vista = ref('propinas')
const historial = ref([])
const abierta = ref(null)
const seleccion = ref(null)
const ajuste = ref(null)
const pago = ref(null)
const horas = ref({})
const fecha = ref(null)

const tipo = computed(() => vista.value)
const esPropinas = computed(() => tipo.value === 'propinas')
const mostrada = computed(() => seleccion.value || abierta.value)
const borrador = computed(() => mostrada.value?.estado === 'calculada')

async function loadConfig() {
  config.value = await quiet(() => postData('/liquidacion/config/get'))
  if (config.value && !config.value.puede_propinas) vista.value = config.value.puede_domiciliarios ? 'domiciliarios' : 'reglas'
}

async function loadTipo() {
  if (vista.value === 'reglas') return
  seleccion.value = null
  const [lista, periodo] = await Promise.all([
    quiet(() => postData('/liquidacion/list', { tipo: tipo.value })),
    quiet(() => postData('/liquidacion/periodo', { tipo: tipo.value, fecha: fecha.value })),
  ])
  historial.value = lista || []
  abierta.value = periodo
  const enCurso = historial.value.find((l) => l.estado === 'calculada')
  if (enCurso) ver(enCurso)
}

async function ver(liquidacion) {
  const detalle = await quiet(() => postData('/liquidacion/get', { liquidacion_id: liquidacion.id }))
  if (detalle) mostrar(detalle)
}

function mostrar(detalle) {
  seleccion.value = detalle
  horas.value = Object.fromEntries(detalle.lineas.map((l) => [l.id, l.horas]))
}

async function calcular() {
  const body = { tipo: tipo.value }
  if (seleccion.value?.estado === 'calculada') body.liquidacion_id = seleccion.value.id
  else body.fecha = abierta.value.desde
  const data = await attempt(() => postData('/liquidacion/calcular', body), { success: 'Liquidación calculada.' })
  if (data) {
    mostrar(data)
    historial.value = (await quiet(() => postData('/liquidacion/list', { tipo: tipo.value }))) || []
  }
}

async function editarLinea(linea, cambios) {
  const data = await attempt(() => postData('/liquidacion/linea', { linea_id: linea.id, ...cambios }), { success: 'Reparto actualizado.' })
  if (data) mostrar(data)
}

function guardarHoras(linea) {
  const valor = Number(horas.value[linea.id])
  if (Number.isNaN(valor) || valor === linea.horas) return
  editarLinea(linea, { horas: valor })
}

async function guardarAjuste() {
  const a = ajuste.value
  const data = await attempt(() => postData('/liquidacion/ajustar', { liquidacion_id: mostrada.value.id, linea_id: a.linea.id,
    valor: Math.round(Number(a.valor) * (a.signo === '-' ? -1 : 1)), motivo: a.motivo.trim() }),
  { success: borrador.value ? 'Ajuste aplicado.' : 'Ajuste registrado para la siguiente liquidación.' })
  if (!data) return
  ajuste.value = null
  mostrar(data)
}

async function aprobar() {
  const data = await attempt(() => postData('/liquidacion/aprobar', { liquidacion_id: mostrada.value.id }), { success: 'Liquidación aprobada.' })
  if (data) {
    mostrar(data)
    historial.value = (await quiet(() => postData('/liquidacion/list', { tipo: tipo.value }))) || []
  }
}

async function descartar() {
  const ok = await attempt(() => postData('/liquidacion/descartar', { liquidacion_id: mostrada.value.id }), { success: 'Borrador descartado.' })
  if (ok) loadTipo()
}

async function registrarPago() {
  const p = pago.value
  const data = await attempt(() => postData('/liquidacion/pagar', { linea_id: p.linea.id, medio_pago: p.medio,
    referencia: p.referencia.trim() || null }), { success: `Pago a ${p.linea.nombre} registrado.` })
  if (!data) return
  pago.value = null
  mostrar(data)
  imprimir(data.lineas.find((l) => l.id === p.linea.id))
}

function imprimir(linea) {
  printer.print('liquidacion', { liquidacion: mostrada.value, linea })
}

async function guardarReglas() {
  const c = config.value
  const data = await attempt(() => postData('/liquidacion/config/save', {
    periodo: c.periodo, modelo: c.modelo, porcentaje_individual: Number(c.porcentaje_individual), metodo: c.metodo,
    por_zona: c.por_zona, pesos: c.pesos, retencion: Number(c.retencion) || 0, propina_domicilio: c.propina_domicilio,
    pago_domicilio: c.pago_domicilio, pago_porcentaje: Number(c.pago_porcentaje) || 0, pago_base: Number(c.pago_base) || 0,
  }), { success: 'Reglas guardadas. Aplican desde la próxima liquidación.' })
  if (data) config.value = data
}

function cambiarVista(v) {
  vista.value = v
  fecha.value = null
  loadTipo()
}

// Periodo anterior o siguiente: para liquidar uno que quedó sin calcular
function moverPeriodo(paso) {
  const base = new Date(`${paso < 0 ? abierta.value.desde : abierta.value.hasta}T12:00:00`)
  base.setDate(base.getDate() + paso)
  fecha.value = base.toISOString().slice(0, 10)
  loadTipo()
}

function periodoTexto(l) {
  return `${formatDate(l.desde)} al ${formatDate(l.hasta)}`
}

onMounted(async () => {
  await loadConfig()
  loadTipo()
})
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Propinas y liquidaciones</h1>
        <p>Reparto de propinas y pago a domiciliarios por periodo. El pago se hace por fuera; aquí queda el registro.</p>
      </div>
    </header>

    <div class="vistas" role="tablist">
      <button v-if="config?.puede_propinas" role="tab" type="button" :aria-selected="vista === 'propinas'" @click="cambiarVista('propinas')">Propinas</button>
      <button v-if="config?.puede_domiciliarios" role="tab" type="button" :aria-selected="vista === 'domiciliarios'"
              @click="cambiarVista('domiciliarios')">Domiciliarios</button>
      <button role="tab" type="button" :aria-selected="vista === 'reglas'" @click="vista = 'reglas'">Reglas</button>
    </div>

    <section v-if="vista !== 'reglas' && mostrada" class="contenido">
      <div class="cabeza-periodo">
        <div>
          <h2>{{ periodoTexto(mostrada) }}</h2>
          <p class="muted">
            <StatusChip :estado="mostrada.estado" :label="mostrada.estado === 'abierta' ? 'Sin liquidar' : mostrada.estado_texto" size="sm" />
            <template v-if="mostrada.estado === 'abierta'"> Vista previa: todavía no se guarda nada.</template>
            <template v-if="mostrada.aprobada_por"> Aprobada por {{ mostrada.aprobada_por }}.</template>
          </p>
        </div>
        <div class="actions">
          <button v-if="seleccion" class="btn btn-secundario" type="button" @click="seleccion = null">Ver vista previa</button>
          <template v-else>
            <button class="btn btn-secundario" type="button" aria-label="Periodo anterior" @click="moverPeriodo(-1)">‹ Anterior</button>
            <button class="btn btn-secundario" type="button" aria-label="Periodo siguiente" @click="moverPeriodo(1)">Siguiente ›</button>
          </template>
          <template v-if="mostrada.estado === 'abierta' && !mostrada.liquidacion_id">
            <button class="btn" type="button" :disabled="busy" @click="calcular">Calcular liquidación</button>
          </template>
          <template v-if="borrador">
            <button class="btn btn-secundario" type="button" :disabled="busy" @click="descartar">Descartar</button>
            <button class="btn btn-secundario" type="button" :disabled="busy" @click="calcular">Recalcular</button>
            <button class="btn" type="button" :disabled="busy" @click="aprobar">Aprobar</button>
          </template>
        </div>
      </div>

      <p v-for="aviso in mostrada.resumen.avisos || []" :key="aviso" class="aviso">{{ aviso }}</p>

      <dl v-if="esPropinas" class="resumen">
        <div><dt>Propinas</dt><dd>{{ formatMoney(mostrada.resumen.propinas || 0) }}</dd></div>
        <div><dt>Cuentas</dt><dd>{{ mostrada.resumen.cuentas || 0 }}</dd></div>
        <div><dt>A los meseros</dt><dd>{{ formatMoney(mostrada.resumen.individual || 0) }}</dd></div>
        <div><dt>Al pozo</dt><dd>{{ formatMoney(mostrada.resumen.pozo || 0) }}</dd></div>
        <div v-if="mostrada.resumen.retenido"><dt>Retenido</dt><dd>{{ formatMoney(mostrada.resumen.retenido) }}</dd></div>
        <div class="fuerte"><dt>Total a pagar</dt><dd>{{ formatMoney(mostrada.total) }}</dd></div>
      </dl>
      <dl v-else class="resumen">
        <div><dt>Entregas</dt><dd>{{ mostrada.resumen.entregas || 0 }}</dd></div>
        <div><dt>Por entregas</dt><dd>{{ formatMoney(mostrada.resumen.pago_entregas || 0) }}</dd></div>
        <div><dt>Propinas</dt><dd>{{ formatMoney(mostrada.resumen.propinas || 0) }}</dd></div>
        <div><dt>Faltantes</dt><dd>{{ mostrada.resumen.faltantes ? `−${formatMoney(mostrada.resumen.faltantes)}` : formatMoney(0) }}</dd></div>
        <div class="fuerte"><dt>Total a pagar</dt><dd>{{ formatMoney(mostrada.total) }}</dd></div>
      </dl>

      <div class="panel table-wrap">
        <table class="table">
          <thead v-if="esPropinas"><tr><th>Persona</th><th class="num">Horas</th><th class="num">Puntos</th><th>Pozo</th>
            <th class="num">Sus mesas</th><th class="num">Del pozo</th><th class="num">Ajustes</th><th class="num">Total</th><th>Pago</th></tr></thead>
          <thead v-else><tr><th>Domiciliario</th><th class="num">Entregas</th><th class="num">Por entregas</th><th class="num">Propinas</th>
            <th class="num">Faltantes</th><th class="num">Ajustes</th><th class="num">Total</th><th>Pago</th></tr></thead>
          <tbody>
            <tr v-for="l in mostrada.lineas" :key="l.id || l.nombre" :class="{ apagada: esPropinas && !l.participa }">
              <td>{{ l.nombre }}<small class="muted bloque">{{ l.rol_texto }}</small>
                <small v-for="a in l.detalle.ajustes || []" :key="a.motivo + a.valor" class="muted bloque">Ajuste {{ formatMoney(a.valor) }}: {{ a.motivo }}</small>
                <small v-if="l.detalle.por_rendir" class="alerta-texto bloque">Por rendir {{ formatMoney(l.detalle.por_rendir) }}</small></td>
              <template v-if="esPropinas">
                <td class="num">
                  <input v-if="borrador && l.peso" v-model.number="horas[l.id]" class="input horas" type="number" min="0" step="0.5"
                         :aria-label="`Horas de ${l.nombre}`" @change="guardarHoras(l)">
                  <template v-else>{{ l.horas }}</template>
                  <small v-if="l.horas_editadas" class="muted bloque">editadas</small></td>
                <td class="num">{{ l.peso }}</td>
                <td><label v-if="borrador && l.peso" class="check">
                  <input type="checkbox" :checked="l.participa" @change="editarLinea(l, { participa: $event.target.checked })"> Participa</label>
                  <template v-else>{{ l.peso ? (l.participa ? 'Sí' : 'No') : '—' }}</template></td>
                <td class="num">{{ formatMoney(l.individual) }}</td>
                <td class="num">{{ formatMoney(l.pozo) }}</td>
              </template>
              <template v-else>
                <td class="num">{{ l.entregas }}</td>
                <td class="num">{{ formatMoney(l.pago_entregas) }}</td>
                <td class="num">{{ formatMoney(l.propinas) }}</td>
                <td class="num">{{ l.descuentos ? `−${formatMoney(l.descuentos)}` : '—' }}</td>
              </template>
              <td class="num">{{ formatMoney(l.ajustes) }}</td>
              <td class="num fuerte-celda">{{ formatMoney(l.total) }}</td>
              <td><div class="actions">
                <button v-if="l.id && mostrada.estado !== 'abierta' && mostrada.estado !== 'pagada'" class="btn btn-secundario btn-sm" type="button"
                        @click="ajuste = { linea: l, signo: '+', valor: null, motivo: '' }">Ajuste</button>
                <button v-if="l.id && ['aprobada', 'pagada'].includes(mostrada.estado) && !l.pagado_en && l.total > 0" class="btn btn-sm" type="button"
                        @click="pago = { linea: l, medio: 'efectivo', referencia: '' }">Pagar</button>
                <template v-if="l.pagado_en">
                  <span class="pagado">Pagado</span>
                  <button class="btn btn-secundario btn-sm" type="button" @click="imprimir(l)">Comprobante</button>
                </template>
              </div></td>
            </tr>
          </tbody>
        </table>
        <p v-if="!mostrada.lineas.length" class="empty">No hay nada por liquidar en este periodo.</p>
      </div>
      <p v-if="mostrada.pendientes?.length" class="muted nota">
        Ajustes registrados que entran en la siguiente liquidación: {{ mostrada.pendientes.map((p) => `${formatMoney(p.valor)} (${p.motivo})`).join(', ') }}.</p>

      <div v-if="esPropinas && Object.keys(mostrada.resumen.por_mesero || {}).length" class="origen">
        <div>
          <h3>De dónde vienen</h3>
          <p v-for="(valor, nombre) in mostrada.resumen.por_mesero" :key="nombre" class="fila"><span>{{ nombre }}</span><span>{{ formatMoney(valor) }}</span></p>
        </div>
        <div>
          <h3>Por zona</h3>
          <p v-for="(valor, nombre) in mostrada.resumen.por_zona" :key="nombre" class="fila"><span>{{ nombre }}</span><span>{{ formatMoney(valor) }}</span></p>
        </div>
      </div>

      <template v-if="historial.length">
        <h3 class="sub">Liquidaciones anteriores</h3>
        <div class="panel table-wrap">
          <table class="table">
            <thead><tr><th>Periodo</th><th>Estado</th><th class="num">Total</th><th></th></tr></thead>
            <tbody>
              <tr v-for="l in historial" :key="l.id">
                <td>{{ periodoTexto(l) }}</td>
                <td><StatusChip :estado="l.estado" :label="l.estado_texto" size="sm" /></td>
                <td class="num">{{ formatMoney(l.total) }}</td>
                <td><button class="btn btn-secundario btn-sm" type="button" @click="ver(l)">Ver</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </section>

    <form v-else-if="vista === 'reglas' && config" class="panel reglas" @submit.prevent="guardarReglas">
      <p class="aviso">El reparto de propinas, cualquier retención y el pago a domiciliarios tienen implicaciones laborales y
        fiscales. El sistema calcula con las reglas que definas; valídalas con tu abogado laboral y tu contador.</p>
      <template v-if="config.puede_propinas">
        <h2>Propinas</h2>
        <div class="form-grid">
          <div class="field"><label for="lq-periodo">Se liquida cada</label>
            <select id="lq-periodo" v-model="config.periodo" class="select">
              <option value="semanal">Semana (lunes a domingo)</option><option value="quincenal">Quincena</option><option value="mensual">Mes</option>
            </select></div>
          <div class="field"><label for="lq-modelo">Cómo se reparte</label>
            <select id="lq-modelo" v-model="config.modelo" class="select">
              <option v-for="(label, valor) in MODELOS" :key="valor" :value="valor">{{ label }}</option>
            </select></div>
          <div v-if="config.modelo === 'mixta'" class="field"><label for="lq-pct">Parte para el mesero de la mesa (%)</label>
            <input id="lq-pct" v-model.number="config.porcentaje_individual" class="input" type="number" min="0" max="100"></div>
          <div v-if="config.modelo !== 'individual'" class="field"><label for="lq-metodo">El pozo se reparte por</label>
            <select id="lq-metodo" v-model="config.metodo" class="select">
              <option v-for="(label, valor) in METODOS" :key="valor" :value="valor">{{ label }}</option>
            </select></div>
          <div class="field"><label for="lq-ret">Retención del restaurante (%)</label>
            <input id="lq-ret" v-model.number="config.retencion" class="input" type="number" min="0" max="50" step="0.5"></div>
          <div v-if="config.puede_domiciliarios" class="field"><label for="lq-dom">Propinas de domicilios</label>
            <select id="lq-dom" v-model="config.propina_domicilio" class="select">
              <option value="pozo">Van al pozo del equipo</option><option value="domiciliario">Van al domiciliario que entregó</option>
            </select></div>
        </div>
        <label class="check"><input v-model="config.por_zona" type="checkbox"> Cada zona reparte su propio pozo</label>
        <fieldset class="pesos">
          <legend>Puntos por rol (0 = no participa del pozo)</legend>
          <div v-for="(label, rol) in config.roles" :key="rol" class="field">
            <label :for="`peso-${rol}`">{{ label }}</label>
            <input :id="`peso-${rol}`" v-model.number="config.pesos[rol]" class="input" type="number" min="0" max="10" step="0.1">
          </div>
        </fieldset>
        <p class="muted">Las horas salen de los turnos de los meseros. Para quien no marca turno, escríbelas en el borrador antes de aprobar.</p>
      </template>
      <template v-if="config.puede_domiciliarios">
        <h2>Domiciliarios</h2>
        <div class="form-grid">
          <div class="field"><label for="lq-pago">Se le paga</label>
            <select id="lq-pago" v-model="config.pago_domicilio" class="select">
              <option v-for="(label, valor) in PAGOS" :key="valor" :value="valor">{{ label }}</option>
            </select></div>
          <div v-if="config.pago_domicilio === 'mixto'" class="field"><label for="lq-base">Base por entrega</label>
            <input id="lq-base" v-model.number="config.pago_base" class="input" type="number" min="0"></div>
          <div v-if="config.pago_domicilio !== 'zona'" class="field"><label for="lq-pp">Porcentaje del envío</label>
            <input id="lq-pp" v-model.number="config.pago_porcentaje" class="input" type="number" min="0" max="100"></div>
        </div>
        <p class="muted">Los faltantes de sus rendiciones se descuentan. Con efectivo por rendir no se aprueba la liquidación.</p>
      </template>
      <div class="form-actions"><button class="btn" type="submit" :disabled="busy">Guardar reglas</button></div>
    </form>

    <AppModal :open="!!ajuste" title="Ajuste manual" width="28rem" @close="ajuste = null">
      <form v-if="ajuste" @submit.prevent="guardarAjuste">
        <p>{{ ajuste.linea.nombre }}<template v-if="!borrador">. La liquidación ya está aprobada: el ajuste entra en la siguiente.</template></p>
        <div class="opciones espacio" role="group" aria-label="Tipo de ajuste">
          <button type="button" :aria-pressed="ajuste.signo === '+'" @click="ajuste.signo = '+'">Sumar</button>
          <button type="button" :aria-pressed="ajuste.signo === '-'" @click="ajuste.signo = '-'">Restar</button>
        </div>
        <div class="field espacio"><label for="aj-valor">Valor</label>
          <input id="aj-valor" v-model.number="ajuste.valor" class="input" type="number" min="1" required></div>
        <div class="field espacio"><label for="aj-motivo">Motivo</label>
          <input id="aj-motivo" v-model="ajuste.motivo" class="input" maxlength="200" required></div>
        <p class="muted">Queda registrado con tu usuario y la hora.</p>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="ajuste = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy || !ajuste.valor || ajuste.motivo.trim().length < 3">Guardar</button>
        </div>
      </form>
    </AppModal>

    <AppModal :open="!!pago" title="Registrar pago" width="26rem" @close="pago = null">
      <form v-if="pago" @submit.prevent="registrarPago">
        <p>{{ pago.linea.nombre }}: <strong>{{ formatMoney(pago.linea.total) }}</strong></p>
        <div class="field espacio"><label for="pg-medio">Cómo se pagó</label>
          <select id="pg-medio" v-model="pago.medio" class="select">
            <option v-for="(label, valor) in MEDIOS" :key="valor" :value="valor">{{ label }}</option>
          </select></div>
        <div class="field espacio"><label for="pg-ref">Referencia</label>
          <input id="pg-ref" v-model="pago.referencia" class="input" maxlength="60" placeholder="Opcional"></div>
        <p class="muted">Se imprime el comprobante para que la persona lo firme.</p>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="pago = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy">Registrar e imprimir</button>
        </div>
      </form>
    </AppModal>
  </div>
</template>

<style scoped>
.vistas {
  display: flex;
  flex-wrap: wrap;
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

.contenido {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.cabeza-periodo {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-3);
}

.cabeza-periodo h2 {
  font-size: var(--text-xl);
}

.resumen {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(9.5rem, 1fr));
  gap: var(--space-3);
  margin: 0;
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

.aviso {
  padding: var(--space-2) var(--space-3);
  border-left: 4px solid var(--estado-pendiente);
  border-radius: var(--radio-sm);
  background: var(--estado-pendiente-suave);
}

.horas {
  width: 5.5rem;
  text-align: right;
}

.apagada td {
  color: var(--acero);
}

.fuerte-celda {
  font-weight: 700;
}

.pagado {
  font-weight: 700;
  color: var(--estado-entregado);
}

.alerta-texto {
  color: var(--estado-cancelado);
  font-weight: 600;
}

.origen {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
  gap: var(--space-4);
}

.origen h3,
.sub {
  font-size: var(--text-base);
  margin-bottom: var(--space-2);
}

.fila {
  display: flex;
  justify-content: space-between;
  padding: var(--space-1) 0;
  border-bottom: 1px solid var(--linea);
}

.reglas {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4);
}

.reglas h2 {
  font-size: var(--text-lg);
}

.pesos {
  margin: 0;
  padding: 0;
  border: none;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr));
  gap: var(--space-3);
}

.pesos legend {
  font-weight: 700;
  margin-bottom: var(--space-2);
}

.opciones {
  display: flex;
  gap: var(--space-2);
}

.opciones button {
  min-height: var(--toque);
  padding: 0 var(--space-4);
  border: 1px solid var(--linea-fuerte);
  border-radius: var(--radio);
  background: var(--superficie);
  font-weight: 600;
  cursor: pointer;
}

.opciones [aria-pressed='true'] {
  border: 2px solid var(--accion);
  background: var(--accion-suave);
}

.bloque {
  display: block;
}

.espacio {
  margin-top: var(--space-3);
}

.nota {
  margin-top: calc(-1 * var(--space-2));
}
</style>
