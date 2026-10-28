<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { post, postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { formatMoney, formatDate, formatDateTime, isoDate, plural } from '@/utils/format'
import { formatCantidad, enlaceWhatsapp } from '@/utils/inventario'
import AppModal from '@/components/AppModal.vue'
import StatusChip from '@/components/StatusChip.vue'
import CompraForm from '@/components/CompraForm.vue'
import RecepcionDialog from '@/components/RecepcionDialog.vue'

/*
  Compras (doc 23): rápidas de plaza, órdenes al proveedor, recepción total o parcial, cierre con la
  factura y anulación. Cada recepción suma al inventario y recalcula el costo promedio (doc 22).
*/
const auth = useAuthStore()
const route = useRoute()
const { busy, attempt, quiet } = useAction()

const vista = ref(route.query.vista || 'pendientes')
const pendientes = ref([])
const borradores = ref([])
const historial = ref([])
const sugerida = ref([])
const insumos = ref([])
const proveedores = ref([])
const filtros = ref({ estado: '', proveedor_id: '', desde: isoDate(new Date(Date.now() - 29 * 86400000)), hasta: '', buscar: '' })

const formulario = ref(null) // { modo, compra }
const detalle = ref(null)
const recibiendo = ref(null)
const cerrando = ref(null)
const anulando = ref(null)
const alertas = ref(null)

const puedeRegistrar = computed(() => auth.can('compras.registrar'))
const porRecibir = computed(() => pendientes.value.reduce((s, c) => s + c.total - c.valor_recibido, 0))

async function load() {
  const [p, b, i, pr] = await Promise.all([
    quiet(() => postData('/compra/list', { estado: 'pendientes' })),
    quiet(() => postData('/compra/list', { estado: 'borrador' })),
    quiet(() => postData('/insumo/list', { todos: true })),
    quiet(() => postData('/proveedor/list', { todos: true })),
  ])
  pendientes.value = p || []
  borradores.value = b || []
  insumos.value = i || []
  proveedores.value = pr || []
  if (vista.value === 'historial') loadHistorial()
  if (vista.value === 'sugerida') loadSugerida()
}

async function loadHistorial() {
  const body = Object.fromEntries(Object.entries(filtros.value).filter(([, v]) => v))
  historial.value = (await quiet(() => postData('/compra/list', body))) || []
}

async function loadSugerida() {
  sugerida.value = (await quiet(() => postData('/compra/sugerida'))) || []
}

watch(vista, (v) => {
  if (v === 'historial') loadHistorial()
  if (v === 'sugerida') loadSugerida()
})

async function abrir(compra) {
  const data = await attempt(() => postData('/compra/get', { compra_id: compra.id }))
  if (data) detalle.value = data
}

function refrescar(data) {
  if (detalle.value && data?.id === detalle.value.id) detalle.value = data
  load()
}

function onGuardada(data) {
  const modo = formulario.value.modo
  formulario.value = null
  if (modo === 'rapida') mostrarAlertas(data)
  else detalle.value = data
  load()
}

function onRecibida(data) {
  recibiendo.value = null
  mostrarAlertas(data)
  refrescar(data)
}

function mostrarAlertas(data) {
  if (data?.alertas_precio?.length || data?.alertas_costo?.length) {
    alertas.value = { numero: data.numero, precio: data.alertas_precio || [], costo: data.alertas_costo || [] }
  }
}

function desdeSugerida(grupo) {
  formulario.value = {
    modo: 'orden',
    compra: {
      proveedor_id: grupo.proveedor_id,
      lineas: grupo.items.map((i) => ({ insumo_id: i.insumo_id, presentacion_id: i.presentacion_id, cantidad: i.cantidad,
        precio_unitario: i.precio_estimado })),
    },
  }
}

async function solicitar() {
  const data = await attempt(() => postData('/compra/solicitar', { compra_id: detalle.value.id }), { success: 'Compra marcada como solicitada.' })
  if (data) refrescar(data)
}

function editar() {
  formulario.value = { modo: 'orden', compra: detalle.value }
  detalle.value = null
}

async function copiarMensaje() {
  try {
    await navigator.clipboard.writeText(detalle.value.mensaje_proveedor)
    alertaCopiado.value = true
    setTimeout(() => { alertaCopiado.value = false }, 2000)
  } catch {
    alertaCopiado.value = false
  }
}
const alertaCopiado = ref(false)

function abrirCierre() {
  cerrando.value = { factura: detalle.value.factura_proveedor || '', confirmar: false, notas: '' }
}

async function cerrar() {
  const c = cerrando.value
  const data = await attempt(() => postData('/compra/cerrar', {
    compra_id: detalle.value.id, factura_proveedor: c.factura.trim() || null, notas: c.notas.trim() || null,
    cerrar_con_pendiente: c.confirmar,
  }), { success: 'Compra cerrada.' })
  if (data) {
    cerrando.value = null
    refrescar(data)
  }
}

function abrirAnulacion() {
  anulando.value = { motivo: '', reintegrar: false, pagadoCaja: detalle.value.recepciones.some((r) => r.pagado_de_caja) }
}

async function anular() {
  const a = anulando.value
  const json = await attempt(() => post('/compra/anular', {
    compra_id: detalle.value.id, motivo: a.motivo.trim(), reintegrar_caja: a.pagadoCaja && a.reintegrar,
  }), { success: (r) => r?.message })
  if (json) {
    anulando.value = null
    refrescar(json.data)
  }
}

function whatsapp(compra) {
  return enlaceWhatsapp(compra.whatsapp, compra.mensaje_proveedor)
}

onMounted(load)
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Compras</h1>
        <p>{{ plural(pendientes.length, 'compra') }} por recibir<template v-if="porRecibir"> · {{ formatMoney(porRecibir) }} en camino</template></p>
      </div>
      <div v-if="puedeRegistrar" class="actions">
        <button class="btn btn-secundario" type="button" @click="formulario = { modo: 'orden', compra: null }">Orden de compra</button>
        <button class="btn" type="button" @click="formulario = { modo: 'rapida', compra: null }">Compra rápida</button>
      </div>
    </header>

    <section v-if="alertas" class="alertas" aria-live="polite">
      <div class="alertas-head">
        <strong>La compra {{ alertas.numero }} subió costos</strong>
        <button class="btn btn-secundario btn-sm" type="button" @click="alertas = null">Entendido</button>
      </div>
      <ul v-if="alertas.precio.length">
        <li v-for="a in alertas.precio" :key="a.insumo">
          {{ a.insumo }}: {{ formatMoney(a.antes) }} → {{ formatMoney(a.despues) }} por {{ a.presentacion }} (+{{ a.variacion }} %)
        </li>
      </ul>
      <template v-if="alertas.costo.length">
        <p>Platos que ahora cuestan más:</p>
        <ul>
          <li v-for="a in alertas.costo" :key="a.producto_id">{{ a.producto }}: {{ formatMoney(a.antes) }} → {{ formatMoney(a.despues) }} (+{{ a.variacion }} %)</li>
        </ul>
        <RouterLink :to="{ name: 'admin-recetas' }">Revisar márgenes en Recetas y costos</RouterLink>
      </template>
    </section>

    <div class="vistas" role="tablist">
      <button role="tab" type="button" :aria-selected="vista === 'pendientes'" @click="vista = 'pendientes'">Por recibir</button>
      <button role="tab" type="button" :aria-selected="vista === 'historial'" @click="vista = 'historial'">Historial</button>
      <button v-if="puedeRegistrar" role="tab" type="button" :aria-selected="vista === 'sugerida'" @click="vista = 'sugerida'">Qué comprar</button>
    </div>

    <section v-if="vista === 'pendientes'">
      <div class="panel table-wrap">
        <table class="table">
          <thead><tr><th>N.º</th><th>Proveedor</th><th>Estado</th><th>Entrega</th><th class="num">Total</th><th></th></tr></thead>
          <tbody>
            <tr v-for="c in [...pendientes, ...borradores]" :key="c.id">
              <td>{{ c.numero }}</td>
              <td><strong>{{ c.proveedor }}</strong><small class="muted bloque">{{ formatDate(c.fecha) }} · {{ c.forma_pago_texto }}</small></td>
              <td><StatusChip :estado="c.estado" size="sm" /></td>
              <td>{{ c.entrega_esperada ? formatDate(c.entrega_esperada) : '—' }}</td>
              <td class="num">{{ formatMoney(c.total) }}
                <small v-if="c.valor_recibido" class="muted bloque">recibido {{ formatMoney(c.valor_recibido) }}</small></td>
              <td class="actions"><button class="btn btn-secundario btn-sm" type="button" @click="abrir(c)">Ver</button></td>
            </tr>
          </tbody>
        </table>
        <p v-if="!pendientes.length && !borradores.length" class="empty">
          No hay compras por recibir. Las compras de plaza se registran con «Compra rápida» y entran de una vez al inventario.
        </p>
      </div>
    </section>

    <section v-else-if="vista === 'historial'">
      <form class="filtros" @submit.prevent="loadHistorial">
        <input v-model="filtros.buscar" class="input" type="search" placeholder="N.º, proveedor o factura" aria-label="Buscar compra">
        <select v-model="filtros.proveedor_id" class="select" aria-label="Proveedor">
          <option value="">Todos los proveedores</option>
          <option v-for="p in proveedores" :key="p.id" :value="p.id">{{ p.nombre }}</option>
        </select>
        <select v-model="filtros.estado" class="select" aria-label="Estado">
          <option value="">Todos los estados</option>
          <option value="borrador">Borrador</option>
          <option value="solicitada">Solicitada</option>
          <option value="parcial">Recibida en parte</option>
          <option value="recibida">Recibida</option>
          <option value="cerrada">Cerrada</option>
          <option value="anulada">Anulada</option>
        </select>
        <input v-model="filtros.desde" class="input" type="date" aria-label="Desde">
        <input v-model="filtros.hasta" class="input" type="date" aria-label="Hasta">
        <button class="btn btn-secundario" type="submit">Filtrar</button>
      </form>
      <div class="panel table-wrap">
        <table class="table">
          <thead><tr><th>N.º</th><th>Fecha</th><th>Proveedor</th><th>Estado</th><th class="num">Recibido</th><th></th></tr></thead>
          <tbody>
            <tr v-for="c in historial" :key="c.id">
              <td>{{ c.numero }}</td>
              <td>{{ formatDate(c.fecha) }}</td>
              <td><strong>{{ c.proveedor }}</strong>
                <small class="muted bloque">{{ c.es_rapida ? 'Compra rápida' : 'Orden' }} · {{ c.forma_pago_texto }}<template v-if="c.factura_proveedor"> · {{ c.factura_proveedor }}</template></small></td>
              <td><StatusChip :estado="c.estado" :label="c.estado_texto" size="sm" /></td>
              <td class="num">{{ formatMoney(c.valor_recibido) }}</td>
              <td class="actions"><button class="btn btn-secundario btn-sm" type="button" @click="abrir(c)">Ver</button></td>
            </tr>
          </tbody>
        </table>
        <p v-if="!historial.length" class="empty">No hay compras con ese filtro.</p>
      </div>
      <p v-if="historial.length" class="muted">
        Total recibido: {{ formatMoney(historial.filter((c) => c.estado !== 'anulada').reduce((s, c) => s + c.valor_recibido, 0)) }}
      </p>
    </section>

    <section v-else>
      <p class="muted intro">Insumos en su mínimo o por debajo, para llegar al doble del mínimo. Ya descuenta lo que viene en camino.</p>
      <div v-for="g in sugerida" :key="g.proveedor_id || 0" class="panel grupo">
        <div class="grupo-head">
          <div>
            <h2>{{ g.proveedor }}</h2>
            <p class="muted">Estimado {{ formatMoney(g.total_estimado) }}
              <template v-if="g.pedido_minimo && g.total_estimado < g.pedido_minimo"> · pedido mínimo {{ formatMoney(g.pedido_minimo) }}</template></p>
          </div>
          <button class="btn btn-sm" type="button" @click="desdeSugerida(g)">Crear orden</button>
        </div>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>Insumo</th><th class="num">Hay</th><th class="num">Mínimo</th><th class="num">Pedir</th><th class="num">Estimado</th></tr></thead>
            <tbody>
              <tr v-for="i in g.items" :key="i.insumo_id">
                <td>{{ i.insumo }}<small v-if="i.en_camino" class="muted bloque">En camino {{ formatCantidad(i.en_camino, i.unidad) }}</small></td>
                <td class="num">{{ formatCantidad(i.stock, i.unidad) }}</td>
                <td class="num">{{ formatCantidad(i.stock_minimo, i.unidad) }}</td>
                <td class="num nowrap"><strong>{{ i.cantidad }} {{ i.presentacion || i.unidad }}</strong></td>
                <td class="num">{{ formatMoney(i.total_estimado) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <p v-if="!sugerida.length" class="panel empty">Ningún insumo está en su mínimo. Configura la existencia mínima de cada insumo en Existencias.</p>
    </section>

    <!-- Detalle -->
    <AppModal :open="!!detalle" :title="detalle ? `Compra ${detalle.numero} · ${detalle.proveedor}` : ''" width="56rem" @close="detalle = null">
      <template v-if="detalle">
        <div class="cabecera">
          <StatusChip :estado="detalle.estado" :label="detalle.estado_texto" />
          <span>{{ formatDate(detalle.fecha) }}</span>
          <span>{{ detalle.forma_pago_texto }}</span>
          <span v-if="detalle.entrega_esperada">Entrega {{ formatDate(detalle.entrega_esperada) }}</span>
          <span v-if="detalle.factura_proveedor">Factura {{ detalle.factura_proveedor }}</span>
        </div>
        <p v-if="detalle.estado === 'anulada'" class="aviso-anulada">
          Anulada por {{ detalle.anulada_por }} el {{ formatDateTime(detalle.anulada_en) }}: {{ detalle.motivo_anulacion }}
        </p>

        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>Insumo</th><th class="num">Pedido</th><th class="num">Llegó</th><th class="num">Precio</th><th class="num">Total</th></tr></thead>
            <tbody>
              <tr v-for="l in detalle.lineas" :key="l.id">
                <td><strong>{{ l.insumo }}</strong>
                  <small v-if="l.novedad" class="muted bloque">{{ l.novedad }}</small></td>
                <td class="num nowrap">{{ l.cantidad }} {{ l.presentacion || l.unidad }}</td>
                <td class="num nowrap" :class="{ pendiente: l.pendiente > 0 && detalle.estado === 'parcial' }">
                  {{ l.cantidad_recibida }}<small v-if="l.pendiente > 0" class="bloque">faltan {{ l.pendiente }}</small></td>
                <td class="num nowrap">{{ formatMoney(Math.round(l.precio_unitario)) }}
                  <small v-if="l.impuesto_porcentaje" class="muted bloque">IVA {{ l.impuesto_porcentaje }} %</small></td>
                <td class="num">{{ formatMoney(l.total) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <dl class="totales">
          <div><dt>Total pedido</dt><dd>{{ formatMoney(detalle.total) }}</dd></div>
          <div><dt>Recibido</dt><dd>{{ formatMoney(detalle.valor_recibido) }}</dd></div>
          <div v-if="detalle.impuestos"><dt>Impuestos incluidos</dt><dd>{{ formatMoney(detalle.impuestos) }}</dd></div>
        </dl>

        <template v-if="detalle.recepciones.length">
          <h3>Recepciones</h3>
          <ul class="recepciones">
            <li v-for="r in detalle.recepciones" :key="r.id">
              {{ formatDateTime(r.hora_local || r.fecha) }} · {{ r.usuario }} · {{ formatMoney(r.valor) }}
              <template v-if="r.pagado_de_caja"> · pagada de caja</template><template v-if="r.notas"> · {{ r.notas }}</template>
            </li>
          </ul>
        </template>
        <p v-if="detalle.notas" class="muted">Notas: {{ detalle.notas }}</p>
        <p class="muted">Registrada por {{ detalle.creado_por }}.</p>

        <div v-if="detalle.puede_editar && puedeRegistrar" class="mensaje">
          <p><strong>Mensaje para el proveedor</strong></p>
          <pre>{{ detalle.mensaje_proveedor }}</pre>
          <div class="actions">
            <a v-if="whatsapp(detalle)" class="btn btn-secundario btn-sm" :href="whatsapp(detalle)" target="_blank" rel="noopener">Enviar por WhatsApp</a>
            <button class="btn btn-secundario btn-sm" type="button" @click="copiarMensaje">{{ alertaCopiado ? 'Copiado' : 'Copiar mensaje' }}</button>
          </div>
        </div>

        <div class="form-actions">
          <button v-if="detalle.puede_anular && auth.can('compras.anular')" class="btn btn-secundario" type="button" @click="abrirAnulacion">Anular</button>
          <button v-if="detalle.puede_editar && puedeRegistrar" class="btn btn-secundario" type="button" @click="editar">Editar</button>
          <button v-if="detalle.estado === 'borrador' && puedeRegistrar" class="btn btn-secundario" type="button" :disabled="busy" @click="solicitar">Marcar como solicitada</button>
          <button v-if="detalle.puede_cerrar && puedeRegistrar" class="btn btn-secundario" type="button" @click="abrirCierre">Cerrar compra</button>
          <button v-if="detalle.puede_recibir && auth.can('compras.recibir')" class="btn" type="button" @click="recibiendo = detalle">Recibir mercancía</button>
        </div>
      </template>
    </AppModal>

    <CompraForm v-if="formulario" :modo="formulario.modo" :compra="formulario.compra" :insumos="insumos" :proveedores="proveedores"
                @close="formulario = null" @saved="onGuardada" />
    <RecepcionDialog v-if="recibiendo" :compra="recibiendo" @close="recibiendo = null" @done="onRecibida" />

    <AppModal :open="!!cerrando" title="Cerrar compra" width="30rem" @close="cerrando = null">
      <form v-if="cerrando" @submit.prevent="cerrar">
        <p class="muted intro">Cierra la compra cuando ya cuadró con la factura del proveedor.</p>
        <div class="field">
          <label for="cc-factura">Factura del proveedor</label>
          <input id="cc-factura" v-model="cerrando.factura" class="input" maxlength="40">
        </div>
        <div class="field espacio">
          <label for="cc-notas">Notas</label>
          <input id="cc-notas" v-model="cerrando.notas" class="input" maxlength="200" placeholder="Opcional">
        </div>
        <label v-if="detalle?.estado === 'parcial'" class="check espacio">
          <input v-model="cerrando.confirmar" type="checkbox"> Cerrar sin esperar lo que faltó
        </label>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="cerrando = null">Volver</button>
          <button class="btn" type="submit" :disabled="busy || (detalle?.estado === 'parcial' && !cerrando.confirmar)">Confirmar cierre</button>
        </div>
      </form>
    </AppModal>

    <AppModal :open="!!anulando" title="Anular compra" width="30rem" @close="anulando = null">
      <form v-if="anulando" @submit.prevent="anular">
        <p class="muted intro">
          {{ detalle?.valor_recibido ? 'Lo que entró al inventario con esta compra se resta con un movimiento contrario.' : 'Aún no entró nada al inventario.' }}
        </p>
        <div class="field">
          <label for="an-motivo">Motivo</label>
          <input id="an-motivo" v-model="anulando.motivo" class="input" maxlength="200" required minlength="3">
        </div>
        <label v-if="anulando.pagadoCaja" class="check espacio">
          <input v-model="anulando.reintegrar" type="checkbox"> El dinero volvió a la caja (registrar aporte en el turno abierto)
        </label>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="anulando = null">Volver</button>
          <button class="btn btn-peligro" type="submit" :disabled="busy || anulando.motivo.trim().length < 3">Anular compra</button>
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
  overflow-x: auto;
}

.vistas [role='tab'] {
  flex: 0 0 auto;
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
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.filtros .input,
.filtros .select {
  width: auto;
  min-width: 10rem;
  flex: 1 1 10rem;
  max-width: 18rem;
}

.intro {
  margin-bottom: var(--space-3);
}

.bloque {
  display: block;
}

.nowrap {
  white-space: nowrap;
}

.espacio {
  margin-top: var(--space-3);
}

.alertas {
  margin-bottom: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border-left: 4px solid var(--estado-pendiente);
  border-radius: var(--radio-sm);
  background: var(--estado-pendiente-suave);
}

.alertas-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.alertas ul {
  margin: var(--space-1) 0 var(--space-2);
  padding-left: var(--space-5);
}

.grupo {
  margin-bottom: var(--space-4);
  padding-top: var(--space-3);
}

.grupo-head {
  padding: 0 var(--space-4);
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.grupo-head h2 {
  font-size: var(--text-lg);
}

.cabecera {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2) var(--space-4);
  margin-bottom: var(--space-3);
  color: var(--acero);
}

.aviso-anulada {
  margin-bottom: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-left: 4px solid var(--estado-cancelado);
  border-radius: var(--radio-sm);
  background: var(--estado-cancelado-suave);
}

.pendiente {
  color: var(--estado-cancelado);
  font-weight: 700;
}

.totales {
  margin: var(--space-3) 0 var(--space-4) auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  max-width: 20rem;
}

.totales div {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
}

.totales dt {
  color: var(--acero);
}

.totales dd {
  margin: 0;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

h3 {
  font-size: var(--text-base);
  margin-bottom: var(--space-1);
}

.recepciones {
  margin: 0 0 var(--space-3);
  padding-left: var(--space-5);
}

.mensaje {
  margin: var(--space-4) 0;
  padding: var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio-sm);
}

.mensaje pre {
  margin: var(--space-2) 0;
  white-space: pre-wrap;
  font-family: inherit;
}
</style>
