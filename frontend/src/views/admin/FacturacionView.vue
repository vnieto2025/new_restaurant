<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { formatMoney, formatDate, formatDateTime, isoDate, downloadCsv, TIPOS_IDENTIFICACION } from '@/utils/format'
import AppModal from '@/components/AppModal.vue'
import StatusChip from '@/components/StatusChip.vue'

/*
  Facturación electrónica (docs 21 y 21A): documentos de venta con su estado ante el proveedor,
  rangos de numeración, ventas por impuesto y configuración del proveedor.
  Cobrar nunca espera al proveedor: lo que falla queda en cola y se reintenta solo.
*/
const auth = useAuthStore()
const { busy, attempt, quiet } = useAction()

const TIPOS_DOC = { pos: 'POS electrónico', factura: 'Factura', nota_credito: 'Nota crédito' }
const MODOS = { aceptar: 'Acepta todo', rechazar: 'Rechaza todo', caido: 'No responde (caído)' }

const vista = ref('documentos')
const estado = ref(null)

// Documentos
const hoy = isoDate(new Date())
const inicioMes = isoDate(new Date(new Date().getFullYear(), new Date().getMonth(), 1))
const filtros = ref({ estado: '', tipo: '', desde: inicioMes, hasta: hoy, buscar: '' })
const documentos = ref([])
const documento = ref(null)
const correccion = ref(null)

// Resoluciones
const resoluciones = ref([])
const resolucion = ref(null)

// Por impuesto
const periodo = ref({ desde: inicioMes, hasta: hoy })
const resumen = ref(null)

// Configuración
const config = ref(null)

const puedeGestionar = computed(() => auth.can('facturacion.gestionar'))
const puedeConfigurar = computed(() => auth.can('facturacion.configurar'))

async function loadEstado() {
  estado.value = await quiet(() => postData('/facturacion/estado'))
}

async function loadDocumentos() {
  const body = Object.fromEntries(Object.entries(filtros.value).filter(([, v]) => v))
  documentos.value = (await quiet(() => postData('/documento/list', body))) || []
}

async function loadResoluciones() {
  resoluciones.value = (await quiet(() => postData('/resolucion/list'))) || []
}

async function loadResumen() {
  resumen.value = await quiet(() => postData('/documento/impuestos', periodo.value))
}

async function loadConfig() {
  const data = await quiet(() => postData('/facturacion/config/get'))
  if (data) config.value = { ...data, modo: data.modo_simulado || 'aceptar', usuario: '', clave: '' }
}

const CARGAS = { documentos: loadDocumentos, resoluciones: loadResoluciones, impuestos: loadResumen, configuracion: loadConfig }
watch(vista, (v) => CARGAS[v]())

async function refrescar() {
  await Promise.all([loadEstado(), CARGAS[vista.value]()])
}

// ---- Documentos ----

async function abrir(doc) {
  documento.value = await attempt(() => postData('/documento/get', { documento_id: doc.id }))
  correccion.value = null
}

async function enviarPendientes() {
  await attempt(() => postData('/documento/enviar', {}), { success: (r) => r && `Enviados: ${r.aceptada} aceptados, ${r.rechazada} rechazados, ${r.pendiente} en espera.` })
  refrescar()
}

async function enviarAhora(doc) {
  await attempt(() => postData('/documento/enviar', { documento_ids: [doc.id], forzar: true }))
  await abrir(doc)
  refrescar()
}

function corregir() {
  const d = documento.value
  correccion.value = { nombre: d.receptor_nombre === 'Consumidor final' ? '' : d.receptor_nombre,
    tipo_documento: d.receptor_tipo_documento || 'CC', documento: d.receptor_documento || '', correo: d.receptor_correo || '' }
}

async function reenviar() {
  const receptor = correccion.value?.documento ? correccion.value : null
  const data = await attempt(() => postData('/documento/corregir', { documento_id: documento.value.id, receptor }),
    { success: (d) => d && (d.estado === 'aceptada' ? 'Documento corregido y aceptado.' : 'Documento corregido y reenviado.') })
  if (data) {
    documento.value = data
    correccion.value = null
    refrescar()
  }
}

async function generar(cuenta) {
  const ok = await attempt(() => postData('/documento/facturar', { cuenta_id: cuenta.id }), { success: 'Documento generado.' })
  if (ok) refrescar()
}

// ---- Resoluciones ----

function nuevaResolucion() {
  resolucion.value = { tipo_documento: 'pos', numero_resolucion: '', prefijo: '', desde: 1, hasta: null,
    vigente_desde: hoy, vigente_hasta: '', alerta_restantes: 100 }
}

function editarResolucion(r) {
  resolucion.value = { ...r, resolucion_id: r.id, vigente_hasta: r.vigente_hasta || '' }
}

async function guardarResolucion() {
  const editando = !!resolucion.value.resolucion_id
  const body = { ...resolucion.value, vigente_hasta: resolucion.value.vigente_hasta || null }
  const ok = await attempt(() => postData(editando ? '/resolucion/update' : '/resolucion/create', body),
    { success: 'Resolución guardada.' })
  if (ok) {
    resolucion.value = null
    refrescar()
  }
}

async function cambiarResolucion(r) {
  await attempt(() => postData('/resolucion/change_status', { resolucion_id: r.id, activo: !r.activo }),
    { success: r.activo ? 'Resolución desactivada.' : 'Resolución activada.' })
  refrescar()
}

// ---- Por impuesto ----

function exportarResumen() {
  downloadCsv(`ventas-por-impuesto-${periodo.value.desde}-${periodo.value.hasta}`, [
    { titulo: 'Impuesto', campo: 'impuesto' }, { titulo: 'Tasa', campo: 'porcentaje_texto' },
    { titulo: 'Base', campo: 'base' }, { titulo: 'Impuesto', campo: 'impuesto_valor' }, { titulo: 'Total', campo: 'total' },
  ], resumen.value.filas)
}

// ---- Configuración ----

async function guardarConfig() {
  const c = config.value
  const credenciales = c.proveedor === 'simulado' ? { modo: c.modo } : { usuario: c.usuario, clave: c.clave }
  const data = await attempt(() => postData('/facturacion/config/save', {
    proveedor: c.proveedor, ambiente: c.ambiente, documento_defecto: c.documento_defecto,
    dias_factura_posterior: Number(c.dias_factura_posterior) || 0, activo: c.activo, credenciales,
  }), { success: (d) => d && (d.activo ? 'Facturación activa.' : 'Configuración guardada.') })
  if (data) {
    config.value = { ...data, modo: data.modo_simulado || 'aceptar', usuario: '', clave: '' }
    loadEstado()
  }
}

onMounted(() => {
  if (!auth.can('facturacion.ver')) vista.value = 'configuracion'
  refrescar()
})
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Facturación electrónica</h1>
        <p v-if="estado">
          {{ estado.activa ? 'Activa' : 'Inactiva' }} · proveedor {{ estado.proveedor || 'sin configurar' }}<template v-if="estado.ambiente">
            ({{ estado.ambiente === 'pruebas' ? 'pruebas' : 'producción' }})</template>.
          Si el proveedor falla se sigue vendiendo y el documento se reintenta.
        </p>
      </div>
      <button v-if="puedeGestionar && estado?.documentos?.pendiente" class="btn" type="button" :disabled="busy" @click="enviarPendientes">
        Enviar {{ estado.documentos.pendiente }} en cola
      </button>
    </header>

    <ul v-if="estado?.alertas?.length" class="alertas" aria-label="Alertas de facturación">
      <li v-for="alerta in estado.alertas" :key="alerta.texto" :class="`alerta-${alerta.nivel}`">
        <strong>{{ alerta.nivel === 'critico' ? 'Atención:' : 'Aviso:' }}</strong> {{ alerta.texto }}
      </li>
    </ul>

    <div v-if="estado?.cuentas_sin_documento?.length && (puedeGestionar || auth.can('facturacion.facturar'))" class="panel sin-documento">
      <h2>Cuentas pagadas sin documento</h2>
      <p class="muted">Quedaron así porque no había resolución vigente al cobrar. Genera su documento ahora.</p>
      <p v-for="cuenta in estado.cuentas_sin_documento" :key="cuenta.id" class="fila-cuenta">
        <span>C-{{ String(cuenta.numero).padStart(5, '0') }} · {{ formatDate(cuenta.jornada) }} · {{ formatMoney(cuenta.total) }}</span>
        <button class="btn btn-secundario btn-sm" type="button" :disabled="busy" @click="generar(cuenta)">Generar documento</button>
      </p>
    </div>

    <div class="vistas" role="tablist">
      <button v-if="auth.can('facturacion.ver')" role="tab" type="button" :aria-selected="vista === 'documentos'" @click="vista = 'documentos'">Documentos</button>
      <button role="tab" type="button" :aria-selected="vista === 'resoluciones'" @click="vista = 'resoluciones'">Numeración</button>
      <button v-if="auth.can('facturacion.ver')" role="tab" type="button" :aria-selected="vista === 'impuestos'" @click="vista = 'impuestos'">Ventas por impuesto</button>
      <button v-if="puedeConfigurar" role="tab" type="button" :aria-selected="vista === 'configuracion'" @click="vista = 'configuracion'">Proveedor</button>
    </div>

    <!-- Documentos -->
    <section v-if="vista === 'documentos'">
      <form class="filtros" @submit.prevent="loadDocumentos">
        <div class="field"><label for="f-estado">Estado</label>
          <select id="f-estado" v-model="filtros.estado" class="select">
            <option value="">Todos</option>
            <option value="pendiente">En cola</option>
            <option value="aceptada">Aceptados</option>
            <option value="rechazada">Rechazados</option>
            <option value="anulada">Anulados</option>
          </select></div>
        <div class="field"><label for="f-tipo">Tipo</label>
          <select id="f-tipo" v-model="filtros.tipo" class="select">
            <option value="">Todos</option>
            <option v-for="(label, valor) in TIPOS_DOC" :key="valor" :value="valor">{{ label }}</option>
          </select></div>
        <div class="field"><label for="f-desde">Desde</label><input id="f-desde" v-model="filtros.desde" class="input" type="date"></div>
        <div class="field"><label for="f-hasta">Hasta</label><input id="f-hasta" v-model="filtros.hasta" class="input" type="date"></div>
        <div class="field"><label for="f-buscar">Número o cliente</label>
          <input id="f-buscar" v-model="filtros.buscar" class="input" type="search" placeholder="POSE15, NIT…"></div>
        <button class="btn btn-secundario" type="submit">Filtrar</button>
      </form>

      <div class="panel table-wrap">
        <table class="table">
          <thead><tr><th>Número</th><th>Tipo</th><th>Fecha</th><th>Cliente</th><th class="num">Total</th><th>Estado</th><th></th></tr></thead>
          <tbody>
            <tr v-for="doc in documentos" :key="doc.id">
              <td><strong>{{ doc.numero }}</strong><small v-if="doc.origen" class="muted"> anula {{ doc.origen }}</small></td>
              <td>{{ TIPOS_DOC[doc.tipo] }}</td>
              <td>{{ formatDate(doc.jornada) }}</td>
              <td>{{ doc.receptor_nombre }}<small v-if="doc.receptor_documento" class="muted"> · {{ doc.receptor_documento }}</small></td>
              <td class="num">{{ doc.tipo === 'nota_credito' ? '−' : '' }}{{ formatMoney(doc.total) }}</td>
              <td><StatusChip :estado="doc.estado" size="sm" /></td>
              <td><button class="btn btn-secundario btn-sm" type="button" @click="abrir(doc)">Ver</button></td>
            </tr>
          </tbody>
        </table>
        <p v-if="!documentos.length" class="empty">No hay documentos con ese filtro.</p>
      </div>
    </section>

    <!-- Numeración -->
    <section v-else-if="vista === 'resoluciones'">
      <div class="barra">
        <p class="muted">Los rangos autorizados para cada tipo de documento. El número se asigna al cobrar, sin saltos.</p>
        <button v-if="puedeConfigurar" class="btn" type="button" @click="nuevaResolucion">Agregar resolución</button>
      </div>
      <div class="panel table-wrap">
        <table class="table">
          <thead><tr><th>Documento</th><th>Resolución</th><th>Rango</th><th class="num">Usados</th><th class="num">Quedan</th><th>Vigencia</th><th></th></tr></thead>
          <tbody>
            <tr v-for="r in resoluciones" :key="r.id" :class="{ muted: !r.activo }">
              <td><strong>{{ r.tipo_texto }}</strong><span v-if="!r.activo"> (inactiva)</span></td>
              <td>{{ r.numero_resolucion || '—' }}</td>
              <td>{{ r.prefijo }}{{ r.desde }} a {{ r.prefijo }}{{ r.hasta }}</td>
              <td class="num">{{ r.usados }}</td>
              <td class="num" :class="{ alerta: r.por_agotarse }">{{ r.restantes }}<span v-if="r.por_agotarse"> · por agotarse</span></td>
              <td>{{ formatDate(r.vigente_desde) }}<template v-if="r.vigente_hasta"> a {{ formatDate(r.vigente_hasta) }}</template>
                <strong v-if="r.vencida"> · vencida</strong></td>
              <td class="actions">
                <template v-if="puedeConfigurar">
                  <button class="btn btn-secundario btn-sm" type="button" @click="editarResolucion(r)">Editar</button>
                  <button class="btn btn-secundario btn-sm" type="button" :disabled="busy" @click="cambiarResolucion(r)">
                    {{ r.activo ? 'Desactivar' : 'Activar' }}</button>
                </template>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="!resoluciones.length" class="empty">Agrega la resolución de numeración que te autorizó la DIAN.</p>
      </div>
    </section>

    <!-- Ventas por impuesto -->
    <section v-else-if="vista === 'impuestos'">
      <form class="filtros" @submit.prevent="loadResumen">
        <div class="field"><label for="p-desde">Desde</label><input id="p-desde" v-model="periodo.desde" class="input" type="date"></div>
        <div class="field"><label for="p-hasta">Hasta</label><input id="p-hasta" v-model="periodo.hasta" class="input" type="date"></div>
        <button class="btn btn-secundario" type="submit">Consultar</button>
        <button v-if="resumen?.filas.length" class="btn btn-secundario" type="button" @click="exportarResumen">Descargar CSV</button>
      </form>
      <div v-if="resumen" class="panel table-wrap">
        <table class="table">
          <thead><tr><th>Impuesto</th><th class="num">Tasa</th><th class="num">Base</th><th class="num">Impuesto</th><th class="num">Total</th></tr></thead>
          <tbody>
            <tr v-for="fila in resumen.filas" :key="fila.impuesto + fila.porcentaje">
              <td>{{ fila.impuesto }}</td>
              <td class="num">{{ fila.porcentaje_texto }}</td>
              <td class="num">{{ formatMoney(fila.base) }}</td>
              <td class="num">{{ formatMoney(fila.impuesto_valor) }}</td>
              <td class="num">{{ formatMoney(fila.total) }}</td>
            </tr>
          </tbody>
          <tfoot v-if="resumen.filas.length">
            <tr>
              <th colspan="2">Total</th>
              <th class="num">{{ formatMoney(resumen.totales.base) }}</th>
              <th class="num">{{ formatMoney(resumen.totales.impuesto_valor) }}</th>
              <th class="num">{{ formatMoney(resumen.totales.total) }}</th>
            </tr>
          </tfoot>
        </table>
        <p v-if="!resumen.filas.length" class="empty">No hay documentos en ese periodo.</p>
        <p class="muted nota">Incluye todos los documentos emitidos; las notas crédito restan. Las propinas no hacen parte de la base.</p>
      </div>
    </section>

    <!-- Proveedor -->
    <section v-else-if="vista === 'configuracion' && config">
      <form class="panel config" @submit.prevent="guardarConfig">
        <div class="form-grid">
          <div class="field"><label for="c-prov">Proveedor tecnológico</label>
            <select id="c-prov" v-model="config.proveedor" class="select">
              <option v-for="p in config.proveedores" :key="p" :value="p">{{ p === 'simulado' ? 'Simulado (para pruebas)' : p }}</option>
            </select></div>
          <div class="field"><label for="c-amb">Ambiente</label>
            <select id="c-amb" v-model="config.ambiente" class="select">
              <option value="pruebas">Pruebas</option>
              <option value="produccion">Producción</option>
            </select></div>
          <div class="field"><label for="c-doc">Documento al cobrar</label>
            <select id="c-doc" v-model="config.documento_defecto" class="select">
              <option value="pos">POS electrónico</option>
              <option value="factura">Factura electrónica</option>
            </select></div>
          <div class="field"><label for="c-dias">Días para pedir factura después de pagar</label>
            <input id="c-dias" v-model.number="config.dias_factura_posterior" class="input" type="number" min="0" max="365"></div>
        </div>

        <div v-if="config.proveedor === 'simulado'" class="field espacio">
          <label for="c-modo">Cómo responde el simulador</label>
          <select id="c-modo" v-model="config.modo" class="select">
            <option v-for="(label, valor) in MODOS" :key="valor" :value="valor">{{ label }}</option>
          </select>
          <span class="hint">No envía nada a la DIAN. Sirve para probar el flujo mientras se elige el proveedor real.</span>
        </div>
        <div v-else class="form-grid espacio">
          <div class="field"><label for="c-usuario">Usuario de la API</label>
            <input id="c-usuario" v-model="config.usuario" class="input" autocomplete="off"
                   :placeholder="config.credenciales_guardadas ? 'Guardado: escribe para reemplazar' : ''"></div>
          <div class="field"><label for="c-clave">Clave o token</label>
            <input id="c-clave" v-model="config.clave" class="input" type="password" autocomplete="new-password"
                   :placeholder="config.credenciales_guardadas ? 'Guardada: escribe para reemplazar' : ''"></div>
          <span class="hint">Se guardan cifradas y no se vuelven a mostrar.</span>
        </div>

        <label class="check espacio"><input v-model="config.activo" type="checkbox"> Emitir documento electrónico en cada cobro</label>
        <p class="muted espacio">Valida con tu contador qué documento debes emitir. Para activarla necesitas una resolución vigente del documento elegido.</p>
        <div class="form-actions">
          <button class="btn" type="submit" :disabled="busy">Guardar</button>
        </div>
      </form>
    </section>

    <!-- Detalle de un documento -->
    <AppModal :open="!!documento" :title="documento ? `${TIPOS_DOC[documento.tipo]} ${documento.numero}` : ''" width="44rem" @close="documento = null">
      <div v-if="documento" class="detalle">
        <div class="cabeza-doc">
          <StatusChip :estado="documento.estado" />
          <span class="muted">{{ formatDateTime(documento.creado_en) }}</span>
        </div>
        <p v-if="documento.mensaje" class="mensaje" :class="{ error: documento.estado === 'rechazada' }">{{ documento.mensaje }}</p>
        <p v-if="documento.estado === 'pendiente' && documento.intentos" class="muted">
          {{ documento.intentos }} intento(s). Próximo: {{ documento.proximo_intento_en ? formatDateTime(documento.proximo_intento_en) : 'ya' }}.
        </p>
        <p v-if="documento.origen">Anula el documento <strong>{{ documento.origen }}</strong>. Motivo: {{ documento.motivo }}</p>
        <p v-if="documento.notas.length">Anulado con: <strong>{{ documento.notas.join(', ') }}</strong></p>

        <dl class="datos">
          <div><dt>Cliente</dt><dd>{{ documento.receptor_nombre }}</dd></div>
          <div v-if="documento.receptor_documento"><dt>Documento</dt><dd>{{ documento.receptor_tipo_documento }} {{ documento.receptor_documento }}</dd></div>
          <div v-if="documento.receptor_correo"><dt>Correo</dt><dd>{{ documento.receptor_correo }}</dd></div>
        </dl>

        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>Descripción</th><th class="num">Cant.</th><th class="num">Base</th><th class="num">Tasa</th><th class="num">Impuesto</th><th class="num">Total</th></tr></thead>
            <tbody>
              <tr v-for="(linea, i) in documento.lineas" :key="i">
                <td>{{ linea.descripcion }}<small v-if="linea.descuento" class="muted"> · desc. {{ formatMoney(linea.descuento) }}</small></td>
                <td class="num">{{ linea.cantidad }}</td>
                <td class="num">{{ formatMoney(linea.base) }}</td>
                <td class="num">{{ linea.impuesto ? `${String(linea.porcentaje).replace('.', ',')} %` : '—' }}</td>
                <td class="num">{{ formatMoney(linea.impuesto_valor) }}</td>
                <td class="num">{{ formatMoney(linea.total) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <dl class="totales">
          <div><dt>Base</dt><dd>{{ formatMoney(documento.base) }}</dd></div>
          <div v-for="imp in documento.impuestos_detalle" :key="imp.impuesto + imp.porcentaje">
            <dt>{{ imp.impuesto }} {{ imp.porcentaje_texto }}</dt><dd>{{ formatMoney(imp.valor) }}</dd>
          </div>
          <div class="total"><dt>Total</dt><dd>{{ formatMoney(documento.total) }}</dd></div>
          <div v-if="documento.propina"><dt>Propina (fuera de la base)</dt><dd>{{ formatMoney(documento.propina) }}</dd></div>
        </dl>
        <p v-if="documento.cufe" class="cufe"><span class="muted">CUFE</span> {{ documento.cufe }}</p>

        <form v-if="correccion" class="correccion" @submit.prevent="reenviar">
          <h3>Datos del cliente</h3>
          <div class="form-grid">
            <div class="field"><label for="r-tipo">Tipo</label>
              <select id="r-tipo" v-model="correccion.tipo_documento" class="select">
                <option v-for="(label, valor) in TIPOS_IDENTIFICACION" :key="valor" :value="valor">{{ label }}</option>
              </select></div>
            <div class="field"><label for="r-doc">Número</label><input id="r-doc" v-model="correccion.documento" class="input" maxlength="30"></div>
            <div class="field"><label for="r-nombre">Nombre o razón social</label><input id="r-nombre" v-model="correccion.nombre" class="input" maxlength="150"></div>
            <div class="field"><label for="r-correo">Correo</label><input id="r-correo" v-model="correccion.correo" class="input" type="email"></div>
          </div>
          <p class="muted espacio">Si el rechazo no era por los datos del cliente, déjalos igual y reenvía. Conserva el mismo número.</p>
          <div class="form-actions">
            <button class="btn btn-secundario" type="button" @click="correccion = null">Cancelar</button>
            <button class="btn" type="submit" :disabled="busy">Corregir y reenviar</button>
          </div>
        </form>

        <div v-else class="form-actions">
          <button v-if="documento.estado === 'rechazada' && puedeGestionar && documento.tipo !== 'nota_credito'" class="btn" type="button" @click="corregir">Corregir</button>
          <button v-if="documento.estado === 'rechazada' && puedeGestionar && documento.tipo === 'nota_credito'" class="btn" type="button" :disabled="busy" @click="reenviar">Reenviar</button>
          <button v-if="documento.estado === 'pendiente' && (puedeGestionar || auth.can('facturacion.facturar'))" class="btn" type="button" :disabled="busy"
                  @click="enviarAhora(documento)">Enviar ahora</button>
        </div>
      </div>
    </AppModal>

    <!-- Resolución -->
    <AppModal :open="!!resolucion" :title="resolucion?.resolucion_id ? 'Editar resolución' : 'Agregar resolución'" width="36rem" @close="resolucion = null">
      <form v-if="resolucion" @submit.prevent="guardarResolucion">
        <div class="form-grid">
          <div class="field"><label for="re-tipo">Documento</label>
            <select id="re-tipo" v-model="resolucion.tipo_documento" class="select" :disabled="resolucion.ultimo != null">
              <option v-for="(label, valor) in TIPOS_DOC" :key="valor" :value="valor">{{ label }}</option>
            </select></div>
          <div class="field"><label for="re-num">Número de resolución</label>
            <input id="re-num" v-model="resolucion.numero_resolucion" class="input" maxlength="40"></div>
          <div class="field"><label for="re-pref">Prefijo</label>
            <input id="re-pref" v-model="resolucion.prefijo" class="input" maxlength="10" :disabled="resolucion.ultimo != null" placeholder="POSE"></div>
          <div class="field"><label for="re-alerta">Avisar cuando queden</label>
            <input id="re-alerta" v-model.number="resolucion.alerta_restantes" class="input" type="number" min="0"></div>
          <div class="field"><label for="re-desde">Desde el número</label>
            <input id="re-desde" v-model.number="resolucion.desde" class="input" type="number" min="1" required :disabled="resolucion.ultimo != null"></div>
          <div class="field"><label for="re-hasta">Hasta el número</label>
            <input id="re-hasta" v-model.number="resolucion.hasta" class="input" type="number" :min="resolucion.ultimo || resolucion.desde" required></div>
          <div class="field"><label for="re-vd">Vigente desde</label>
            <input id="re-vd" v-model="resolucion.vigente_desde" class="input" type="date" required></div>
          <div class="field"><label for="re-vh">Vigente hasta</label>
            <input id="re-vh" v-model="resolucion.vigente_hasta" class="input" type="date"></div>
        </div>
        <p v-if="resolucion.ultimo != null" class="muted espacio">Ya se usó hasta el {{ resolucion.prefijo }}{{ resolucion.ultimo }}: solo se puede ampliar el rango o cambiar la vigencia.</p>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="resolucion = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy">Guardar</button>
        </div>
      </form>
    </AppModal>
  </div>
</template>

<style scoped>
.alertas {
  list-style: none;
  margin: 0 0 var(--space-4);
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.alertas li {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radio-sm);
  border-left: 4px solid var(--estado-pendiente);
  background: var(--estado-pendiente-suave);
}

.alertas .alerta-critico {
  border-left-color: var(--estado-cancelado);
  background: var(--estado-cancelado-suave);
}

.sin-documento {
  margin-bottom: var(--space-4);
  padding: var(--space-4);
}

.sin-documento h2 {
  font-size: var(--text-base);
}

.fila-cuenta {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

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
  align-items: flex-end;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.filtros .field {
  min-width: 9rem;
}

.barra {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.alerta {
  font-weight: 700;
}

.nota {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
}

.config {
  padding: var(--space-4);
  max-width: 48rem;
}

.espacio {
  margin-top: var(--space-3);
}

.detalle {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.cabeza-doc {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.mensaje {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radio-sm);
  background: var(--fondo);
  font-size: var(--text-sm);
}

.mensaje.error {
  background: var(--estado-cancelado-suave);
}

.datos {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: var(--space-3);
  margin: 0;
}

.datos dt,
.totales dt {
  color: var(--acero);
  font-size: var(--text-sm);
}

.datos dd {
  margin: 0;
  font-weight: 600;
}

.totales {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  align-self: flex-end;
  min-width: min(100%, 20rem);
}

.totales div {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
}

.totales dd {
  margin: 0;
  font-variant-numeric: tabular-nums;
}

.totales .total {
  font-weight: 700;
  font-size: var(--text-lg);
}

.totales .total dt {
  color: var(--tinta);
  font-size: inherit;
}

.cufe {
  font-family: var(--font-mono, monospace);
  font-size: var(--text-xs, 0.75rem);
  word-break: break-all;
}

.correccion h3 {
  font-size: var(--text-base);
  margin-bottom: var(--space-2);
}
</style>
