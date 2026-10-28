<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { useToastStore } from '@/stores/toast'
import { usePrintStore } from '@/stores/print'
import { formatMoney, newKey } from '@/utils/format'
import AppModal from '@/components/AppModal.vue'
import ReasonDialog from '@/components/ReasonDialog.vue'
import FacturaReceptor from '@/components/FacturaReceptor.vue'
import StatusChip from '@/components/StatusChip.vue'
import EnlacePago from '@/components/EnlacePago.vue'

/*
  Cobro de una cuenta (doc 20, secciones 3 y 4): propina aparte, descuento con permiso,
  pago mixto, dividir en partes iguales o por ítems, y cambio del efectivo.
  Los pagos se arman aquí y se envían juntos con una clave de idempotencia.
*/
const props = defineProps({
  cuenta: { type: Object, required: true },
  medios: { type: Array, required: true },
  turnoAbierto: { type: Boolean, default: false },
})
const emit = defineEmits(['updated', 'close'])

const auth = useAuthStore()
const printer = usePrintStore()
const toast = useToastStore()
const { busy, attempt } = useAction()

const pagos = ref([])
const clave = ref(newKey())
const partes = ref(2)
const elegidos = ref(new Set())
const propinaLibre = ref(null)
const descuento = ref(null)
const anular = ref({ open: false, pago: null, cuenta: false })

// Cupones (doc 25A): el servidor valida cada regla y dice cuál falla (RN-CUP-01, RN-CUP-05)
const puedeCupon = computed(() => auth.modulos.has('fidelizacion') && auth.can('cupones.aplicar'))
const codigo = ref('')
const cuponError = ref('')
const cuponBusy = ref(false)
const buscaCliente = ref(null)

// Factura electrónica a nombre del cliente (doc 21): al cobrar o después, mientras esté dentro del plazo
const facturacionActiva = ref(false)
const conFactura = ref(false)
const receptor = ref(receptorVacio())
const facturaPosterior = ref(false)

function receptorVacio() {
  return { cliente_id: null, nombre: '', tipo_documento: 'CC', documento: '', correo: '' }
}

onMounted(async () => {
  if (!auth.can('facturacion.facturar')) return
  const estado = await postData('/facturacion/estado').catch(() => null)
  facturacionActiva.value = !!estado?.activa
})

// Documento vigente: el más reciente que no sea nota crédito ni esté anulado
const documento = computed(() => (props.cuenta.documentos || []).find((d) =>
  d.tipo !== 'nota_credito' && d.estado !== 'anulada' && !d.notas?.length))
const receptorListo = computed(() => receptor.value.documento.trim().length >= 3 && receptor.value.nombre.trim().length >= 2)

watch(() => props.cuenta.id, () => {
  codigo.value = ''
  cuponError.value = ''
  buscaCliente.value = null
  pagos.value = []
  clave.value = newKey()
  elegidos.value = new Set()
  conFactura.value = false
  receptor.value = receptorVacio()
})

const abierta = computed(() => props.cuenta.estado === 'abierta')
// Enlace para que el cliente pague desde su celular (doc 20A)
const enlacePago = ref(false)
const puedeEnlace = computed(() => auth.modulos.has('pagos_linea') && auth.can('pagos_linea.cobrar'))
const porAsignar = computed(() => props.cuenta.saldo - pagos.value.reduce((s, p) => s + (Number(p.monto) || 0), 0))
const cambioTotal = computed(() => pagos.value.reduce((s, p) => s + (p.tipo === 'efectivo' ? Math.max(0, (Number(p.recibido) || 0) - (Number(p.monto) || 0)) : 0), 0))
const sumaElegidos = computed(() => props.cuenta.lineas.filter((l) => elegidos.value.has(l.id)).reduce((s, l) => s + l.total, 0))
const cuotaParte = computed(() => Math.ceil(props.cuenta.saldo / Math.max(1, partes.value)))
const propinaOpcion = computed(() => {
  if (!props.cuenta.propina) return 'ninguna'
  return props.cuenta.propina === props.cuenta.propina_sugerida ? 'sugerida' : 'otra'
})
const listo = computed(() => pagos.value.length > 0 && porAsignar.value >= 0 && pagos.value.every((p) =>
  Number(p.monto) > 0 && (!p.pide_referencia || p.referencia?.trim()) && (p.tipo !== 'efectivo' || !p.recibido || Number(p.recibido) >= Number(p.monto))))

// Toca un medio: agrega un pago por lo que falta (o por el monto indicado al dividir)
function agregarPago(medio, monto = null) {
  const valor = monto ?? porAsignar.value
  if (valor <= 0) return
  pagos.value.push({ medio_pago_id: medio.id, nombre: medio.nombre, tipo: medio.tipo, pide_referencia: medio.pide_referencia,
    monto: Math.min(valor, porAsignar.value), recibido: null, referencia: '' })
}

function quitarPago(index) {
  pagos.value.splice(index, 1)
}

function toggleLinea(linea) {
  const next = new Set(elegidos.value)
  next.has(linea.id) ? next.delete(linea.id) : next.add(linea.id)
  elegidos.value = next
}

async function ajustar(body, mensaje) {
  const data = await attempt(() => postData('/cuenta/ajustar', { cuenta_id: props.cuenta.id, ...body }), { success: mensaje })
  if (data) emit('updated', data)
}

function propina(opcion) {
  if (opcion === 'ninguna') ajustar({ propina: 0 }, 'Sin propina.')
  else if (opcion === 'sugerida') ajustar({ propina: props.cuenta.propina_sugerida }, 'Propina sugerida agregada.')
  else propinaLibre.value = props.cuenta.propina || 0
}

async function guardarPropinaLibre() {
  await ajustar({ propina: Number(propinaLibre.value) || 0 }, 'Propina actualizada.')
  propinaLibre.value = null
}

async function guardarDescuento() {
  await ajustar({ descuento: Number(descuento.value.monto) || 0, descuento_motivo: descuento.value.motivo }, 'Descuento aplicado.')
  descuento.value = null
}

async function cobrar() {
  const body = {
    cuenta_id: props.cuenta.id,
    clave_idempotencia: clave.value,
    pagos: pagos.value.map((p) => ({ medio_pago_id: p.medio_pago_id, monto: Number(p.monto),
      recibido: p.tipo === 'efectivo' && p.recibido ? Number(p.recibido) : null, referencia: p.referencia?.trim() || null })),
  }
  // La factura se emite cuando el pago cubre el total
  if (conFactura.value && porAsignar.value === 0) body.factura = limpiarReceptor()
  const data = await attempt(() => postData('/cuenta/pagar', body), {
    success: (cuenta) => cuenta.estado === 'pagada'
      ? `Cuenta pagada${cambioTotal.value ? `. Cambio: ${formatMoney(cambioTotal.value)}` : ''}.`
      : `Abono registrado. Falta ${formatMoney(cuenta.saldo)}.`,
  })
  if (!data) return // los pagos y la clave se conservan para reintentar
  pagos.value = []
  clave.value = newKey()
  elegidos.value = new Set()
  conFactura.value = false
  emit('updated', data)
}

function limpiarReceptor() {
  const r = receptor.value
  return { cliente_id: r.cliente_id, nombre: r.nombre.trim(), tipo_documento: r.tipo_documento,
    documento: r.documento.trim(), correo: r.correo.trim() || null }
}

async function generarDocumento() {
  const ok = await attempt(() => postData('/documento/facturar', { cuenta_id: props.cuenta.id }),
    { success: (d) => d && `Documento ${d.numero} generado.` })
  if (!ok) return
  const cuenta = await postData('/cuenta/get', { cuenta_id: props.cuenta.id }).catch(() => null)
  if (cuenta) emit('updated', cuenta)
}

async function facturarDespues() {
  const ok = await attempt(() => postData('/documento/facturar', { cuenta_id: props.cuenta.id, receptor: limpiarReceptor() }),
    { success: (d) => d && `Factura ${d.numero} generada.` })
  if (!ok) return
  facturaPosterior.value = false
  receptor.value = receptorVacio()
  const cuenta = await postData('/cuenta/get', { cuenta_id: props.cuenta.id }).catch(() => null)
  if (cuenta) emit('updated', cuenta)
}

// Una venta directa sin pagos se deshace sin anular nada en caja
const cancelarVenta = ref(false)
async function confirmarCancelacion(motivo) {
  const ok = await attempt(() => postData('/pos/cancelar', { cuenta_id: props.cuenta.id, motivo }), { success: 'Venta cancelada.' })
  cancelarVenta.value = false
  if (ok) emit('close')
}

async function confirmarAnulacion(motivo) {
  const { pago, cuenta } = anular.value
  const data = cuenta
    ? await attempt(() => postData('/cuenta/anular', { cuenta_id: props.cuenta.id, motivo }), { success: 'Cuenta anulada.' })
    : await attempt(() => postData('/cuenta/anular_pago', { pago_id: pago.id, motivo }), { success: 'Pago anulado.' })
  anular.value.open = false
  if (data) emit('updated', data)
}

async function cuponAccion(path, body, mensaje) {
  cuponBusy.value = true
  cuponError.value = ''
  try {
    const data = await postData(path, { cuenta_id: props.cuenta.id, ...body })
    emit('updated', data)
    toast.success(mensaje)
    return true
  } catch (error) {
    cuponError.value = error.message
    return false
  } finally {
    cuponBusy.value = false
  }
}

async function aplicarCupon(valor = codigo.value) {
  if (await cuponAccion('/cupon/aplicar', { codigo: valor.trim() }, `Cupón ${valor.trim().toUpperCase()} aplicado.`)) codigo.value = ''
}

function quitarCupon(cupon) {
  cuponAccion('/cupon/quitar', { redencion_id: cupon.redencion_id }, 'Cupón quitado.')
}

async function buscarCliente() {
  const texto = buscaCliente.value.texto.trim()
  if (texto.length < 3) return
  buscaCliente.value.resultados = await postData('/cliente/buscar', { texto }).catch(() => [])
  buscaCliente.value.buscado = true
}

async function elegirCliente(cliente) {
  if (await cuponAccion('/cupon/cliente', { cliente_id: cliente?.id || null }, cliente ? `Cliente: ${cliente.nombre}.` : 'La cuenta quedó sin cliente.')) {
    buscaCliente.value = null
  }
}

function imprimir() {
  printer.print('cuenta', props.cuenta)
}
</script>

<template>
  <section class="cobro">
    <header class="cabeza">
      <div>
        <h2>{{ cuenta.mesa_tipo === 'externa' ? cuenta.cliente_nombre || (cuenta.venta_directa ? 'Venta directa' : 'Para llevar') : cuenta.mesa }}</h2>
        <p class="muted">{{ cuenta.mesa_tipo === 'externa' ? (cuenta.venta_directa ? 'Venta directa' : cuenta.entrega ? 'Domicilio' : 'Para llevar') : cuenta.zona }} · {{ cuenta.ordenes.join(', ') }}<template v-if="cuenta.mesero"> · {{ cuenta.mesero }}</template></p>
      </div>
      <button class="cerrar" type="button" aria-label="Cerrar cobro" @click="emit('close')">×</button>
    </header>

    <p v-if="cuenta.estado === 'pagada'" class="sello sello-ok">Pagada · {{ cuenta.numero_texto }}</p>
    <p v-if="cuenta.cupon_obsequio" class="obsequio">
      Cupón para la próxima visita de {{ cuenta.cliente?.nombre }}: <strong>{{ cuenta.cupon_obsequio.codigo }}</strong>
      · {{ cuenta.cupon_obsequio.descripcion }}. Sale impreso en el comprobante.</p>
    <p v-else-if="cuenta.estado === 'anulada'" class="sello sello-anulada">Anulada: {{ cuenta.anulada_motivo }}</p>
    <p v-else-if="cuenta.items_pendientes" class="aviso">{{ cuenta.items_pendientes }} ítems aún no se han entregado.</p>
    <p v-if="cuenta.entrega" class="muted domicilio">
      {{ cuenta.entrega.direccion }}<template v-if="cuenta.entrega.barrio"> · {{ cuenta.entrega.barrio }}</template> · zona {{ cuenta.entrega.zona_envio }}
      <template v-if="abierta && cuenta.entrega.estado === 'en_camino'"><br>Va en camino: lo cobra el domiciliario y se registra cuando rinde el efectivo.</template>
    </p>

    <ul class="lineas">
      <li v-for="linea in cuenta.lineas" :key="linea.id" :class="{ elegida: elegidos.has(linea.id) }">
        <label v-if="abierta" class="dividir-check">
          <input type="checkbox" :checked="elegidos.has(linea.id)" :aria-label="`Elegir ${linea.nombre} para dividir`" @change="toggleLinea(linea)">
        </label>
        <span class="linea-nombre">{{ linea.cantidad }} × {{ linea.nombre }}
          <small v-if="linea.modificadores.length">{{ linea.modificadores.map((m) => m.nombre).join(', ') }}</small>
        </span>
        <span>{{ formatMoney(linea.total) }}</span>
      </li>
    </ul>

    <dl class="totales">
      <div><dt>Subtotal</dt><dd>{{ formatMoney(cuenta.subtotal) }}</dd></div>
      <div v-if="cuenta.descuento"><dt>Descuento <small>{{ cuenta.descuento_motivo }}</small></dt><dd>−{{ formatMoney(cuenta.descuento) }}</dd></div>
      <div v-for="c in (cuenta.cupones || []).filter((x) => x.tipo !== 'envio' && x.valor)" :key="c.redencion_id">
        <dt>Cupón <small>{{ c.codigo }}</small></dt><dd>−{{ formatMoney(c.valor) }}</dd></div>
      <div v-if="cuenta.envio"><dt>Domicilio</dt><dd>{{ formatMoney(cuenta.envio) }}</dd></div>
      <div v-if="cuenta.descuento_envio"><dt>Envío gratis <small>cupón</small></dt><dd>−{{ formatMoney(cuenta.descuento_envio) }}</dd></div>
      <div><dt>Propina</dt><dd>{{ formatMoney(cuenta.propina) }}</dd></div>
      <div class="total"><dt>Total</dt><dd>{{ formatMoney(cuenta.total) }}</dd></div>
      <div v-if="cuenta.pagado"><dt>Pagado</dt><dd>{{ formatMoney(cuenta.pagado) }}</dd></div>
      <div v-if="abierta && cuenta.pagado" class="total"><dt>Falta</dt><dd>{{ formatMoney(cuenta.saldo) }}</dd></div>
    </dl>

    <template v-if="abierta">
      <div class="fila-opciones" role="group" aria-label="Propina">
        <span class="etiqueta">Propina</span>
        <button type="button" class="opcion" :aria-pressed="propinaOpcion === 'ninguna'" :disabled="busy" @click="propina('ninguna')">Sin propina</button>
        <button v-if="cuenta.propina_porcentaje" type="button" class="opcion" :aria-pressed="propinaOpcion === 'sugerida'" :disabled="busy"
                @click="propina('sugerida')">{{ cuenta.propina_porcentaje }} % · {{ formatMoney(cuenta.propina_sugerida) }}</button>
        <button type="button" class="opcion" :aria-pressed="propinaOpcion === 'otra'" :disabled="busy" @click="propina('otra')">Otro valor</button>
        <button v-if="auth.can('caja.descuento')" type="button" class="opcion" :disabled="busy"
                @click="descuento = { monto: cuenta.descuento || null, motivo: cuenta.descuento_motivo || '' }">Descuento</button>
      </div>

      <section v-if="puedeCupon" class="cupon" aria-label="Cupón y cliente">
        <div class="cupon-cliente">
          <span class="etiqueta">Cliente</span>
          <template v-if="cuenta.cliente">
            <strong>{{ cuenta.cliente.nombre }}</strong>
            <button type="button" class="enlace" :disabled="cuponBusy" @click="buscaCliente = { texto: '', resultados: [], buscado: false }">Cambiar</button>
          </template>
          <button v-else-if="!buscaCliente" type="button" class="enlace" @click="buscaCliente = { texto: '', resultados: [], buscado: false }">
            Identificar cliente</button>
        </div>
        <div v-if="buscaCliente" class="buscar-cliente">
          <form class="fila-cupon" @submit.prevent="buscarCliente">
            <input v-model="buscaCliente.texto" class="input" type="search" placeholder="Nombre, celular o documento" aria-label="Buscar cliente">
            <button class="btn btn-secundario btn-sm" type="submit">Buscar</button>
            <button class="btn btn-secundario btn-sm" type="button" @click="buscaCliente = null">Cancelar</button>
          </form>
          <ul v-if="buscaCliente.resultados.length" class="clientes">
            <li v-for="cl in buscaCliente.resultados" :key="cl.id">
              <button type="button" :disabled="cuponBusy" @click="elegirCliente(cl)"><strong>{{ cl.nombre }}</strong>
                <span class="muted">{{ cl.telefono_legible }}</span></button>
            </li>
          </ul>
          <p v-else-if="buscaCliente.buscado" class="muted">No está registrado. Regístralo en Clientes para darle cupones.</p>
          <button v-if="cuenta.cliente" type="button" class="enlace" @click="elegirCliente(null)">Quitar el cliente de la cuenta</button>
        </div>

        <form class="fila-cupon" @submit.prevent="aplicarCupon()">
          <label class="etiqueta" for="cupon-codigo">Cupón</label>
          <input id="cupon-codigo" v-model="codigo" class="input codigo" maxlength="30" autocomplete="off" placeholder="Código"
                 :aria-invalid="!!cuponError" aria-describedby="cupon-error">
          <button class="btn btn-secundario" type="submit" :disabled="cuponBusy || codigo.trim().length < 3">Aplicar</button>
        </form>
        <p id="cupon-error" class="cupon-error" role="alert">{{ cuponError }}</p>
        <div v-if="cuenta.cupones_cliente?.length" class="sugeridos">
          <span class="muted">Cupones de {{ cuenta.cliente?.nombre?.split(' ')[0] }}:</span>
          <button v-for="c in cuenta.cupones_cliente" :key="c.codigo" type="button" class="opcion" :disabled="cuponBusy"
                  @click="aplicarCupon(c.codigo)">{{ c.codigo }} · {{ c.descripcion || c.nombre }}</button>
        </div>
        <ul v-if="cuenta.cupones?.length" class="aplicados">
          <li v-for="c in cuenta.cupones" :key="c.redencion_id">
            <span><strong>{{ c.codigo }}</strong> {{ c.nombre }}
              <small v-if="c.nota" class="nota-cupon">No descuenta: {{ c.nota }}</small>
              <small v-else class="muted">−{{ formatMoney(c.valor) }} · aplicó {{ c.aplicado_por }}</small></span>
            <button type="button" class="enlace" :disabled="cuponBusy" @click="quitarCupon(c)">Quitar</button>
          </li>
        </ul>
      </section>

      <div class="dividir">
        <span class="etiqueta">Dividir</span>
        <label class="partes">
          <input v-model.number="partes" class="input" type="number" min="2" max="20" aria-label="Número de partes">
          <span>partes de {{ formatMoney(cuotaParte) }}</span>
        </label>
        <span v-if="elegidos.size" class="muted">Ítems elegidos: {{ formatMoney(sumaElegidos) }}</span>
      </div>

      <div class="medios" role="group" aria-label="Medio de pago">
        <button v-for="medio in medios" :key="medio.id" type="button" class="medio" :disabled="!turnoAbierto || porAsignar <= 0"
                @click="agregarPago(medio, elegidos.size ? sumaElegidos : null)">
          {{ medio.nombre }}
        </button>
        <button v-if="puedeEnlace && cuenta.saldo > 0" type="button" class="medio" @click="enlacePago = true">Enlace de pago</button>
      </div>
      <EnlacePago v-if="enlacePago" :sesion-mesa-id="cuenta.sesion_mesa_id" @close="enlacePago = false" />
      <p class="muted ayuda">
        Toca un medio para cobrar lo que falta. Para dividir, elige ítems o usa
        <button type="button" class="enlace" :disabled="!medios.length" @click="agregarPago(medios[0], cuotaParte)">una parte en efectivo</button>.
      </p>
      <p v-if="!turnoAbierto" class="aviso">Abre el turno de caja para poder cobrar.</p>

      <div v-for="(pago, index) in pagos" :key="index" class="pago">
        <strong>{{ pago.nombre }}</strong>
        <label class="field">
          <span class="label">Valor</span>
          <input v-model.number="pago.monto" class="input" type="number" min="1" inputmode="numeric">
        </label>
        <label v-if="pago.tipo === 'efectivo'" class="field">
          <span class="label">Recibido</span>
          <input v-model.number="pago.recibido" class="input" type="number" min="0" inputmode="numeric" :placeholder="String(pago.monto)">
        </label>
        <label v-if="pago.pide_referencia" class="field">
          <span class="label">Referencia</span>
          <input v-model="pago.referencia" class="input" maxlength="60" required>
        </label>
        <div v-if="pago.tipo === 'efectivo'" class="rapidos">
          <button v-for="billete in [20000, 50000, 100000]" :key="billete" type="button" class="btn btn-secundario btn-sm"
                  @click="pago.recibido = billete">{{ formatMoney(billete) }}</button>
          <span v-if="pago.recibido > pago.monto" class="cambio">Cambio {{ formatMoney(pago.recibido - pago.monto) }}</span>
        </div>
        <button class="btn btn-secundario btn-sm quitar" type="button" @click="quitarPago(index)">Quitar</button>
      </div>

      <p v-if="pagos.length && porAsignar < 0" class="aviso">Los pagos superan lo que falta por {{ formatMoney(-porAsignar) }}.</p>

      <div v-if="facturacionActiva" class="factura">
        <label class="check"><input v-model="conFactura" type="checkbox"> Factura a nombre del cliente</label>
        <FacturaReceptor v-if="conFactura" v-model="receptor" />
        <p v-if="conFactura && porAsignar !== 0" class="muted">La factura se emite al registrar el pago completo.</p>
      </div>

      <button class="btn btn-grande btn-bloque" type="button" :disabled="busy || !listo || (conFactura && porAsignar === 0 && !receptorListo)"
              :aria-busy="busy" @click="cobrar">
        {{ porAsignar === 0 ? `Cobrar ${formatMoney(cuenta.saldo)}` : `Registrar abono de ${formatMoney(cuenta.saldo - porAsignar)}` }}
      </button>
    </template>

    <div v-if="cuenta.pagos.length" class="historial">
      <h3>Pagos</h3>
      <p v-for="pago in cuenta.pagos" :key="pago.id" class="pago-hecho" :class="{ anulado: pago.estado === 'anulado' }">
        <span>{{ pago.medio }} · {{ formatMoney(pago.monto) }}<template v-if="pago.cambio"> (cambio {{ formatMoney(pago.cambio) }})</template></span>
        <button v-if="abierta && pago.estado === 'aplicado' && auth.can('caja.anular')" type="button" class="enlace"
                @click="anular = { open: true, pago, cuenta: false }">Anular</button>
        <span v-if="pago.estado === 'anulado'" class="muted">Anulado</span>
      </p>
    </div>

    <div v-if="cuenta.documentos?.length" class="historial">
      <h3>Documento de venta</h3>
      <p v-for="doc in cuenta.documentos" :key="doc.id" class="pago-hecho">
        <span>{{ doc.tipo_texto }} {{ doc.numero }}<template v-if="doc.receptor_documento"> · {{ doc.receptor_nombre }}</template></span>
        <StatusChip :estado="doc.estado" size="sm" />
      </p>
      <template v-if="facturacionActiva && cuenta.estado === 'pagada' && documento?.tipo === 'pos'">
        <button v-if="!facturaPosterior" class="btn btn-secundario btn-sm" type="button" @click="facturaPosterior = true">
          Factura a nombre del cliente</button>
        <form v-else class="factura" @submit.prevent="facturarDespues">
          <p class="muted">El documento POS se anula con nota crédito y se emite la factura.</p>
          <FacturaReceptor v-model="receptor" />
          <div class="form-actions">
            <button class="btn btn-secundario" type="button" @click="facturaPosterior = false">Cancelar</button>
            <button class="btn" type="submit" :disabled="busy || !receptorListo">Generar factura</button>
          </div>
        </form>
      </template>
    </div>
    <div v-else-if="facturacionActiva && cuenta.estado === 'pagada' && cuenta.total > cuenta.propina" class="aviso sin-doc">
      <span>Esta cuenta quedó sin documento de venta.</span>
      <button class="btn btn-secundario btn-sm" type="button" :disabled="busy" @click="generarDocumento">Generar documento</button>
    </div>

    <div class="actions pie">
      <button class="btn btn-secundario" type="button" @click="imprimir">{{ cuenta.estado === 'pagada' ? 'Imprimir comprobante' : 'Imprimir precuenta' }}</button>
      <button v-if="cuenta.venta_directa && abierta && !cuenta.pagado" class="btn btn-secundario" type="button"
              @click="cancelarVenta = true">Cancelar venta</button>
      <button v-if="cuenta.estado !== 'anulada' && auth.can('caja.anular') && !(cuenta.venta_directa && abierta && !cuenta.pagado)"
              class="btn btn-secundario" type="button"
              @click="anular = { open: true, pago: null, cuenta: true }">Anular cuenta</button>
    </div>

    <AppModal :open="propinaLibre !== null" title="Propina" width="24rem" @close="propinaLibre = null">
      <form @submit.prevent="guardarPropinaLibre">
        <div class="field">
          <label for="propina">Valor de la propina</label>
          <input id="propina" v-model.number="propinaLibre" class="input" type="number" min="0" inputmode="numeric">
        </div>
        <div class="form-actions">
          <button class="btn" type="submit" :disabled="busy">Guardar</button>
        </div>
      </form>
    </AppModal>

    <AppModal :open="!!descuento" title="Descuento" width="26rem" @close="descuento = null">
      <form v-if="descuento" @submit.prevent="guardarDescuento">
        <div class="field">
          <label for="desc-monto">Valor</label>
          <input id="desc-monto" v-model.number="descuento.monto" class="input" type="number" min="0" :max="cuenta.subtotal" inputmode="numeric">
        </div>
        <div class="field motivo">
          <label for="desc-motivo">Motivo</label>
          <input id="desc-motivo" v-model="descuento.motivo" class="input" maxlength="200" placeholder="Cliente frecuente, cortesía…">
        </div>
        <p class="muted">Queda registrado en la auditoría.</p>
        <div class="form-actions">
          <button class="btn" type="submit" :disabled="busy || (descuento.monto > 0 && descuento.motivo.trim().length < 3)">Aplicar</button>
        </div>
      </form>
    </AppModal>

    <ReasonDialog :open="cancelarVenta" :busy="busy" title="Cancelar la venta"
                  description="Los productos vuelven al inventario. Queda en la auditoría."
                  :options="['El cliente se arrepintió', 'Error al registrar']" confirm-label="Cancelar venta"
                  @close="cancelarVenta = false" @confirm="confirmarCancelacion" />
    <ReasonDialog :open="anular.open" :busy="busy" :title="anular.cuenta ? 'Anular la cuenta' : 'Anular el pago'"
                  :description="anular.cuenta ? 'Se anulan la cuenta y todos sus pagos. Queda en la auditoría.' : 'El valor vuelve a quedar pendiente en la cuenta.'"
                  :options="['Cobro duplicado', 'Error de digitación']" confirm-label="Anular"
                  @close="anular.open = false" @confirm="confirmarAnulacion" />
  </section>
</template>

<style scoped>
.cobro {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.cabeza {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-3);
}

.cabeza h2 {
  font-size: var(--text-2xl);
  font-stretch: 68%;
}

.cerrar {
  width: var(--toque);
  height: var(--toque);
  border: none;
  background: none;
  font-size: 1.75rem;
  cursor: pointer;
}

.factura {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio-sm);
  background: var(--papel);
}

.sin-doc {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
}

.sello {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radio-sm);
  font-weight: 700;
}

.sello-ok {
  background: var(--estado-entregado-suave);
}

.sello-anulada {
  background: var(--estado-cancelado-suave);
}

.aviso {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radio-sm);
  border: 2px dashed var(--tinta);
  font-size: var(--text-sm);
}

.lineas {
  list-style: none;
  margin: 0;
  padding: var(--space-3) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  background: var(--papel);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
  font-family: var(--font-papel);
  font-size: var(--text-sm);
}

.lineas li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
}

.lineas li.elegida {
  font-weight: 600;
}

.linea-nombre {
  flex: 1;
}

.linea-nombre small {
  display: block;
  color: var(--acero);
}

.dividir-check input {
  width: 1.25rem;
  height: 1.25rem;
  accent-color: var(--accion);
}

.totales {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.totales div {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
}

.totales dt small {
  color: var(--acero);
}

.totales dd {
  margin: 0;
}

.totales .total {
  font-size: var(--text-xl);
  font-weight: 800;
  font-stretch: 75%;
}

.etiqueta {
  font-weight: 600;
  font-size: var(--text-sm);
  min-width: 4.5rem;
}

.fila-opciones,
.dividir,
.medios {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.opcion,
.medio {
  min-height: var(--toque);
  padding: 0 var(--space-4);
  border: 1px solid var(--linea-fuerte);
  border-radius: var(--radio);
  background: var(--superficie);
  font-weight: 600;
  cursor: pointer;
}

.opcion[aria-pressed='true'] {
  border: 2px solid var(--accion);
  background: var(--accion-suave);
}

.medio {
  flex: 1 1 8rem;
  min-height: var(--toque-grande);
}

.medio:disabled,
.opcion:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.partes {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.partes .input {
  width: 5rem;
}

.ayuda {
  font-size: var(--text-sm);
}

.enlace {
  border: none;
  background: none;
  padding: 0;
  color: var(--accion);
  text-decoration: underline;
  cursor: pointer;
  font: inherit;
}

.pago {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
  gap: var(--space-2);
  align-items: end;
  padding: var(--space-3);
  border: 1px solid var(--linea);
  border-left: 6px solid var(--accion);
  border-radius: var(--radio);
}

.pago strong {
  grid-column: 1 / -1;
}

.rapidos {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.cambio {
  font-weight: 800;
  font-size: var(--text-lg);
}

.quitar {
  justify-self: start;
}

.historial h3 {
  font-size: var(--text-base);
  margin-bottom: var(--space-2);
}

.pago-hecho {
  display: flex;
  justify-content: space-between;
  gap: var(--space-2);
  font-size: var(--text-sm);
}

.pago-hecho.anulado span:first-child {
  text-decoration: line-through;
  color: var(--acero);
}

.motivo {
  margin-top: var(--space-3);
}

.cupon {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px dashed var(--linea-fuerte);
  border-radius: var(--radio);
}

.cupon-cliente,
.fila-cupon,
.sugeridos {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.fila-cupon .input {
  flex: 1 1 8rem;
  width: auto;
  min-width: 0;
}

.codigo {
  font-family: var(--font-papel);
  text-transform: uppercase;
}

.cupon-error {
  min-height: 0;
  margin: 0;
  color: var(--estado-cancelado);
  font-weight: 600;
  font-size: var(--text-sm);
}

.cupon-error:empty {
  display: none;
}

.clientes,
.aplicados {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.clientes button {
  width: 100%;
  display: flex;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio-sm);
  background: var(--papel);
  text-align: left;
  cursor: pointer;
}

.aplicados li {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-left: 4px solid var(--accion);
  background: var(--accion-suave);
  border-radius: var(--radio-sm);
}

.aplicados small {
  display: block;
}

.nota-cupon {
  color: var(--estado-cancelado);
  font-weight: 600;
}

.obsequio {
  padding: var(--space-2) var(--space-3);
  border: 2px dashed var(--accion);
  border-radius: var(--radio-sm);
  background: var(--accion-suave);
}

.pie {
  justify-content: flex-end;
}
</style>
