<script setup>
import { ref, computed, onMounted } from 'vue'
import { post, postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { usePrintStore } from '@/stores/print'
import { useRealtime } from '@/composables/useRealtime'
import { useAction } from '@/composables/useAction'
import { formatMoney, formatTime, minutesAgo, plural } from '@/utils/format'
import OpsBar from '@/components/OpsBar.vue'
import ConnectionBanner from '@/components/ConnectionBanner.vue'
import AppModal from '@/components/AppModal.vue'
import AvisosPendientes from '@/components/AvisosPendientes.vue'

/*
  Entregas a domicilio (doc 15B, sección 3): quien despacha asigna el domiciliario por su código y sigue
  cada pedido; el domiciliario ve solo lo suyo y marca la salida, la entrega o el fallo. El efectivo
  contra entrega se rinde en caja con su diferencia (sección 6). Los pedidos que el cliente hace en la web
  llegan "por confirmar": quien despacha revisa la dirección y los confirma o rechaza (doc 17A, sección 2.6).
*/
const auth = useAuthStore()
const printer = usePrintStore()
const { busy, attempt, quiet } = useAction()

const despacha = computed(() => auth.can('domicilios.despachar'))
const rinde = computed(() => auth.can('domicilios.rendir') && auth.modulos.has('caja'))

const datos = ref({ activas: [], cerradas: [], domiciliarios: [], propio: null, motivos_fallo: [] })
const vista = ref('salir')
const efectivo = ref({ pendientes: [], rendiciones: [] })
const fallo = ref(null)
const rechazo = ref(null)
const rendicion = ref(null)
const asignando = ref({})
const refresco = ref(0)
const avisa = computed(() => auth.can(['notificaciones.enviar', 'notificaciones.configurar']))

const porConfirmar = computed(() => datos.value.activas.filter((e) => e.por_confirmar))
// Los que esperan confirmación van primero: el cliente está pendiente de la respuesta
const porSalir = computed(() => datos.value.activas.filter((e) => e.estado !== 'en_camino')
  .sort((a, b) => Number(b.por_confirmar) - Number(a.por_confirmar)))
const enCamino = computed(() => datos.value.activas.filter((e) => e.estado === 'en_camino'))
const porRendir = computed(() => efectivo.value.pendientes.reduce((s, g) => s + g.esperado, 0))

const vistas = computed(() => [
  { id: 'salir', label: porConfirmar.value.length ? `Por salir · ${porConfirmar.value.length} por confirmar` : 'Por salir', cuenta: porSalir.value.length },
  { id: 'camino', label: 'En camino', cuenta: enCamino.value.length },
  { id: 'cerradas', label: 'Cerradas hoy', cuenta: datos.value.cerradas.length },
  rinde.value && { id: 'efectivo', label: 'Efectivo', cuenta: efectivo.value.pendientes.length },
].filter(Boolean))
const lista = computed(() => ({ salir: porSalir.value, camino: enCamino.value, cerradas: datos.value.cerradas })[vista.value] || [])

async function load() {
  const [d, e] = await Promise.all([
    quiet(() => postData('/entrega/list')),
    rinde.value ? quiet(() => postData('/entrega/por_rendir')) : Promise.resolve(null),
  ])
  if (d) datos.value = d
  if (e) efectivo.value = e
  refresco.value += 1
}

const { status, online } = useRealtime(['ordenes'], { onEvent: load, onSync: load })

async function asignar(entrega) {
  const id = asignando.value[entrega.id]
  if (!id) return
  await attempt(() => postData('/entrega/asignar', { entrega_id: entrega.id, domiciliario_id: Number(id) }), { success: 'Asignada.' })
  load()
}

async function accion(ruta, entrega) {
  const json = await attempt(() => post(ruta, { entrega_id: entrega.id }), { success: (r) => r?.message })
  if (json) load()
}

async function confirmar(entrega) {
  const json = await attempt(() => post('/orden/aprobar', { orden_id: entrega.orden_id }),
    { success: `${entrega.orden} confirmado y enviado a cocina.` })
  if (json) load()
}

async function rechazar() {
  const r = rechazo.value
  const json = await attempt(() => post('/orden/rechazar', { orden_id: r.entrega.orden_id, motivo: r.motivo.trim() }),
    { success: `${r.entrega.orden} rechazado. No se cobra.` })
  if (json) {
    rechazo.value = null
    load()
  }
}

function abrirFallo(entrega) {
  fallo.value = { entrega, motivo: '', decision: 'reintento' }
}

async function registrarFallo() {
  const f = fallo.value
  const json = await attempt(() => post('/entrega/fallida', { entrega_id: f.entrega.id, motivo: f.motivo.trim(), decision: f.decision }),
    { success: (r) => r?.message })
  if (json) {
    fallo.value = null
    load()
  }
}

function abrirRendicion(grupo) {
  rendicion.value = { grupo, entregado: grupo.esperado, notas: '' }
}

async function rendir() {
  const r = rendicion.value
  const json = await attempt(() => post('/entrega/rendir', {
    domiciliario_id: r.grupo.domiciliario_id, entregado: Number(r.entregado) || 0, notas: r.notas.trim() || null,
  }), { success: (res) => res?.message })
  if (json) {
    rendicion.value = null
    load()
  }
}

async function imprimir(entrega) {
  const tirilla = await attempt(() => postData('/orden/tirilla', { orden_id: entrega.orden_id }))
  if (tirilla) printer.print('orden', tirilla)
}

function enlaceMapa(entrega) {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${entrega.direccion}, ${entrega.barrio || ''}`)}`
}

onMounted(load)
</script>

<template>
  <div class="entregas">
    <OpsBar :title="datos.propio ? `Mis entregas · ${datos.propio.codigo}` : 'Domicilios'" />
    <ConnectionBanner :status="status" :online="online" />

    <div class="vistas" role="tablist">
      <button v-for="v in vistas" :key="v.id" role="tab" type="button" :aria-selected="vista === v.id" @click="vista = v.id">
        {{ v.label }} <span v-if="v.cuenta" class="cuenta">{{ v.cuenta }}</span>
      </button>
    </div>

    <main v-if="vista !== 'efectivo'" class="lista">
      <AvisosPendientes v-if="avisa" class="ancho" :refresco="refresco" />
      <p v-if="!lista.length" class="empty">
        {{ vista === 'salir' ? (datos.propio ? 'No tienes entregas asignadas.' : 'No hay domicilios por salir.')
          : vista === 'camino' ? 'Nadie está en camino.' : 'Aún no hay entregas cerradas hoy.' }}
      </p>
      <article v-for="e in lista" :key="e.id" class="entrega" :class="{ lista: e.lista && vista === 'salir', confirmar: e.por_confirmar }">
        <header class="cabeza">
          <span class="numero">{{ e.orden }}</span>
          <div class="quien">
            <strong>{{ e.cliente_nombre }} <span v-if="e.web" class="origen">Web</span></strong>
            <span class="muted">{{ e.zona_envio }} · pedido {{ formatTime(e.hora_pedido || e.creado_en) }}
              <template v-if="vista === 'camino' && e.salida_en"> · salió {{ minutesAgo(e.salida_en) }}</template></span>
          </div>
          <span class="estado" :class="`estado-${e.estado}`">
            {{ e.por_confirmar ? 'Por confirmar' : e.estado === 'pendiente_asignacion' || e.estado === 'asignada' ? (e.lista ? 'Lista para salir' : 'En cocina') : e.estado_texto }}
          </span>
        </header>

        <div class="direccion">
          <p><strong>{{ e.direccion }}</strong><template v-if="e.barrio"> · {{ e.barrio }}</template></p>
          <p v-if="e.indicaciones" class="muted">{{ e.indicaciones }}</p>
          <p class="enlaces">
            <a :href="`tel:${e.telefono}`">Llamar {{ e.telefono }}</a>
            <a :href="enlaceMapa(e)" target="_blank" rel="noopener">Ver en el mapa</a>
          </p>
        </div>
        <p class="items">{{ e.items.map((i) => `${i.cantidad} ${i.nombre}`).join(', ') }}</p>
        <p v-if="e.notas" class="muted">Nota: {{ e.notas }}</p>

        <p class="cobro">
          <template v-if="e.estado === 'fallida'">{{ e.decision_texto }}: {{ e.motivo_fallo }}</template>
          <template v-else-if="e.pagada">Pagada</template>
          <template v-else-if="e.forma_pago === 'en_linea' && e.estado !== 'entregada'">Pagará en línea · {{ formatMoney(e.por_cobrar) }} pendiente</template>
          <template v-else-if="e.por_cobrar">{{ e.estado === 'entregada' ? 'Cobró' : 'Cobrar' }} <strong>{{ formatMoney(e.por_cobrar) }}</strong> en efectivo</template>
          <template v-if="e.estado === 'entregada' && e.contra_entrega"> · {{ e.rendida ? 'rendido en caja' : 'por rendir en caja' }}</template>
        </p>
        <p v-if="e.intentos && e.estado !== 'fallida'" class="aviso">Reintento: antes {{ e.motivo_fallo }}</p>

        <footer v-if="e.por_confirmar" class="pie">
          <span class="muted">Revisa la dirección y la zona antes de confirmar.</span>
          <div v-if="despacha" class="actions">
            <button class="btn btn-secundario" type="button" :disabled="busy" @click="rechazo = { entrega: e, motivo: '' }">Rechazar</button>
            <button class="btn" type="button" :disabled="busy" @click="confirmar(e)">Confirmar y enviar a cocina</button>
          </div>
        </footer>
        <footer v-else class="pie">
          <template v-if="despacha && (e.estado === 'pendiente_asignacion' || e.estado === 'asignada')">
            <label class="visually-hidden" :for="`dom-${e.id}`">Domiciliario</label>
            <select :id="`dom-${e.id}`" v-model="asignando[e.id]" class="select">
              <option :value="undefined" disabled>{{ e.domiciliario ? `${e.domiciliario.codigo} · ${e.domiciliario.nombre}` : 'Elige domiciliario' }}</option>
              <option v-for="d in datos.domiciliarios" :key="d.id" :value="d.id">
                {{ d.codigo }} · {{ d.nombre }}{{ d.en_camino ? ` (en camino: ${d.en_camino})` : '' }}</option>
            </select>
            <button class="btn btn-secundario" type="button" :disabled="busy || !asignando[e.id]" @click="asignar(e)">
              {{ e.domiciliario ? 'Cambiar' : 'Asignar' }}</button>
          </template>
          <span v-else-if="e.domiciliario && !datos.propio" class="muted">{{ e.domiciliario.codigo }} · {{ e.domiciliario.nombre }}</span>
          <div class="actions">
            <button v-if="despacha && e.estado !== 'fallida'" class="btn btn-secundario" type="button" :disabled="busy" @click="imprimir(e)">Tirilla</button>
            <button v-if="e.estado === 'asignada'" class="btn" type="button" :disabled="busy || !e.lista" @click="accion('/entrega/salir', e)">
              Salió</button>
            <template v-if="e.estado === 'en_camino'">
              <button class="btn btn-secundario" type="button" :disabled="busy" @click="abrirFallo(e)">No se pudo entregar</button>
              <button class="btn" type="button" :disabled="busy" @click="accion('/entrega/entregar', e)">Entregada</button>
            </template>
            <button v-if="despacha && (e.estado === 'pendiente_asignacion' || e.estado === 'asignada')" class="btn btn-secundario"
                    type="button" :disabled="busy" @click="abrirFallo(e)">Cancelar</button>
          </div>
        </footer>
      </article>
    </main>

    <main v-else class="efectivo">
      <p class="ayuda">Cada domiciliario entrega en caja lo que cobró. Si trae de menos, la diferencia queda a su nombre.</p>
      <p v-if="porRendir" class="resumen">Por rendir: <strong>{{ formatMoney(porRendir) }}</strong></p>
      <article v-for="g in efectivo.pendientes" :key="g.domiciliario_id" class="entrega">
        <header class="cabeza">
          <span class="numero">{{ g.codigo }}</span>
          <div class="quien"><strong>{{ g.nombre }}</strong>
            <span class="muted">{{ plural(g.entregas.length, 'entrega') }}</span></div>
          <strong class="monto">{{ formatMoney(g.esperado) }}</strong>
        </header>
        <ul class="detalle">
          <li v-for="e in g.entregas" :key="e.id">{{ e.orden }} · {{ e.cliente }} · {{ formatMoney(e.monto) }}</li>
        </ul>
        <footer class="pie"><button class="btn" type="button" @click="abrirRendicion(g)">Recibir efectivo</button></footer>
      </article>
      <p v-if="!efectivo.pendientes.length" class="empty">Nadie tiene efectivo por rendir.</p>

      <template v-if="efectivo.rendiciones.length">
        <h2>Últimas rendiciones</h2>
        <div class="panel table-wrap">
          <table class="table">
            <thead><tr><th>Hora</th><th>Domiciliario</th><th class="num">Esperado</th><th class="num">Entregó</th><th class="num">Diferencia</th></tr></thead>
            <tbody>
              <tr v-for="r in efectivo.rendiciones" :key="r.id">
                <td>{{ formatTime(r.hora_local) }}</td>
                <td>{{ r.domiciliario }}<small v-if="r.notas" class="muted bloque">{{ r.notas }}</small></td>
                <td class="num">{{ formatMoney(r.esperado) }}</td>
                <td class="num">{{ formatMoney(r.entregado) }}</td>
                <td class="num" :class="{ faltante: r.diferencia < 0 }">{{ r.diferencia ? formatMoney(r.diferencia) : 'Cuadra' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </main>

    <AppModal :open="!!fallo" :title="fallo?.entrega.estado === 'en_camino' ? 'No se pudo entregar' : 'Cancelar domicilio'" width="30rem" @close="fallo = null">
      <form v-if="fallo" @submit.prevent="registrarFallo">
        <div class="motivos" role="group" aria-label="Motivos frecuentes">
          <button v-for="m in datos.motivos_fallo" :key="m" type="button" class="opcion" :aria-pressed="fallo.motivo === m" @click="fallo.motivo = m">{{ m }}</button>
        </div>
        <div class="field">
          <label for="fl-motivo">Motivo</label>
          <input id="fl-motivo" v-model="fallo.motivo" class="input" maxlength="200" required minlength="3">
        </div>
        <fieldset v-if="despacha" class="decision">
          <legend>¿Qué se hace?</legend>
          <label class="check"><input v-model="fallo.decision" type="radio" value="reintento"> Reintentar: vuelve a la lista para salir de nuevo</label>
          <label class="check"><input v-model="fallo.decision" type="radio" value="cancelacion"> Cancelar el pedido: no se cobra</label>
          <label class="check"><input v-model="fallo.decision" type="radio" value="perdida"> Darlo por perdido: no se cobra y queda como pérdida</label>
        </fieldset>
        <p v-else class="muted">El pedido vuelve al local para que decidan si sale de nuevo.</p>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="fallo = null">Volver</button>
          <button class="btn" :class="{ 'btn-peligro': fallo.decision !== 'reintento' }" type="submit"
                  :disabled="busy || fallo.motivo.trim().length < 3">Registrar</button>
        </div>
      </form>
    </AppModal>

    <AppModal :open="!!rechazo" :title="rechazo ? `Rechazar ${rechazo.entrega.orden}` : ''" width="30rem" @close="rechazo = null">
      <form v-if="rechazo" @submit.prevent="rechazar">
        <p>El cliente verá el motivo en el seguimiento de su pedido. No se cobra nada.</p>
        <div class="motivos espacio" role="group" aria-label="Motivos frecuentes">
          <button v-for="m in ['Dirección fuera de cobertura', 'No contesta el celular', 'Producto agotado', 'Pedido duplicado']" :key="m"
                  type="button" class="opcion" :aria-pressed="rechazo.motivo === m" @click="rechazo.motivo = m">{{ m }}</button>
        </div>
        <div class="field espacio">
          <label for="rz-motivo">Motivo</label>
          <input id="rz-motivo" v-model="rechazo.motivo" class="input" maxlength="200" required minlength="3">
        </div>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="rechazo = null">Volver</button>
          <button class="btn btn-peligro" type="submit" :disabled="busy || rechazo.motivo.trim().length < 3">Rechazar pedido</button>
        </div>
      </form>
    </AppModal>

    <AppModal :open="!!rendicion" :title="rendicion ? `Efectivo de ${rendicion.grupo.nombre}` : ''" width="28rem" @close="rendicion = null">
      <form v-if="rendicion" @submit.prevent="rendir">
        <p>Debe entregar <strong>{{ formatMoney(rendicion.grupo.esperado) }}</strong> por {{ plural(rendicion.grupo.entregas.length, 'entrega') }}.</p>
        <div class="field espacio">
          <label for="rd-monto">Efectivo que entregó</label>
          <input id="rd-monto" v-model.number="rendicion.entregado" class="input" type="number" min="0" inputmode="numeric" required>
        </div>
        <p v-if="Number(rendicion.entregado) !== rendicion.grupo.esperado" class="aviso espacio">
          {{ Number(rendicion.entregado) < rendicion.grupo.esperado ? 'Faltan' : 'Sobran' }}
          {{ formatMoney(Math.abs(Number(rendicion.entregado) - rendicion.grupo.esperado)) }}.
        </p>
        <div class="field espacio">
          <label for="rd-notas">Nota</label>
          <input id="rd-notas" v-model="rendicion.notas" class="input" maxlength="200" placeholder="Opcional">
        </div>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="rendicion = null">Volver</button>
          <button class="btn" type="submit" :disabled="busy || rendicion.entregado === '' || rendicion.entregado === null">Registrar y cobrar</button>
        </div>
      </form>
    </AppModal>
  </div>
</template>

<style scoped>
.entregas {
  min-height: 100dvh;
}

.vistas {
  display: flex;
  background: var(--superficie);
  border-bottom: 1px solid var(--linea);
  overflow-x: auto;
}

.vistas [role='tab'] {
  flex: 1 0 auto;
  min-height: var(--toque-grande);
  padding: 0 var(--space-3);
  border: none;
  border-bottom: 3px solid transparent;
  background: transparent;
  font-weight: 700;
  cursor: pointer;
}

.vistas [aria-selected='true'] {
  border-bottom-color: var(--accion);
}

.cuenta {
  margin-left: var(--space-1);
  padding: 0.05em 0.55em;
  border-radius: 999px;
  background: var(--accion-suave);
  font-size: var(--text-sm);
}

.lista,
.efectivo {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 22rem), 1fr));
  align-items: start;
  gap: var(--space-3);
  padding: var(--space-4);
}

.efectivo > .ayuda,
.efectivo > .resumen,
.efectivo > .empty,
.efectivo > h2,
.efectivo > .panel,
.lista > .ancho,
.lista > .empty {
  grid-column: 1 / -1;
}

.entrega {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-4);
  background: var(--superficie);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
}

.entrega.lista {
  border: 2px solid var(--estado-despachado);
}

/* Pedido web que espera confirmación: lo primero que debe atender quien despacha */
.entrega.confirmar {
  border: 2px solid var(--estado-proceso);
  background: var(--estado-proceso-suave);
}

.origen {
  margin-left: var(--space-1);
  padding: 0 var(--space-2);
  border-radius: 999px;
  background: var(--tinta);
  color: #fff;
  font-size: var(--text-sm);
  font-weight: 600;
}

.cabeza {
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

.estado {
  padding: 0.2em 0.65em;
  border-radius: 999px;
  background: var(--estado-pendiente-suave);
  font-weight: 600;
  font-size: var(--text-sm);
  white-space: nowrap;
}

.estado-en_camino {
  background: var(--estado-proceso-suave);
}

.estado-entregada {
  background: var(--estado-entregado-suave);
}

.estado-fallida {
  background: var(--estado-cancelado-suave);
}

.direccion p {
  margin: 0;
}

.enlaces {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
  margin-top: var(--space-1) !important;
}

.enlaces a {
  display: inline-flex;
  align-items: center;
  min-height: var(--toque);
  font-weight: 600;
}

.cobro strong,
.monto {
  font-variant-numeric: tabular-nums;
}

.monto {
  font-size: var(--text-xl);
}

.aviso {
  padding: var(--space-2) var(--space-3);
  border-left: 4px solid var(--estado-pendiente);
  border-radius: var(--radio-sm);
  background: var(--estado-pendiente-suave);
}

.pie {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-1);
}

.pie .select {
  flex: 1 1 12rem;
  width: auto;
}

.pie .actions {
  margin-left: auto;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.detalle {
  margin: 0;
  padding-left: var(--space-5);
}

.faltante {
  color: var(--estado-cancelado);
  font-weight: 700;
}

.bloque {
  display: block;
}

.espacio {
  margin-top: var(--space-3);
}

.motivos {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.opcion {
  min-height: var(--toque);
  padding: 0 var(--space-3);
  border: 1px solid var(--linea);
  border-radius: 999px;
  background: var(--papel);
  font-weight: 600;
  cursor: pointer;
}

.opcion[aria-pressed='true'] {
  border-color: var(--accion);
  background: var(--accion-suave);
}

.decision {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: var(--space-3) 0 0;
  padding: var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio-sm);
}

.decision legend {
  font-weight: 700;
}
</style>
