<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { formatMoney, formatDate, isoDate } from '@/utils/format'
import { enlaceWhatsapp } from '@/utils/inventario'
import AppModal from '@/components/AppModal.vue'
import StatusChip from '@/components/StatusChip.vue'

/*
  Cupones (doc 25A): cupones con reglas, plantillas que emiten el cupón de la próxima visita y resultados
  (redenciones, costo del descuento, ticket con y sin cupón). La validación siempre la hace el servidor.
*/
const auth = useAuthStore()
const route = useRoute()
const { busy, attempt, quiet } = useAction()

const TIPOS = { porcentaje: 'Porcentaje', valor: 'Valor fijo', producto: 'Producto', envio: 'Envío gratis' }
const CANALES = { mesa: 'Mesa', para_llevar: 'Para llevar', domicilio: 'Domicilio' }
const DIAS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

const vista = ref(auth.can('cupones.gestionar') ? 'cupones' : 'resultados')
const cupones = ref([])
const plantillas = ref([])
const filtros = ref({ buscar: '', estado: '' })
const form = ref(null)
const catalogo = ref({ productos: [], categorias: [], zonas: [] })
const clienteBusqueda = ref({ texto: '', resultados: [] })
const detalle = ref(null)
const resultados = ref(null)
const periodo = ref({ desde: isoDate(new Date(Date.now() - 29 * 86400000)), hasta: isoDate(new Date()) })

const esPlantilla = computed(() => !!form.value?.plantilla)

async function loadCupones() {
  const body = { plantillas: false }
  if (filtros.value.buscar.trim()) body.buscar = filtros.value.buscar.trim()
  if (filtros.value.estado) body.estado = filtros.value.estado
  cupones.value = (await quiet(() => postData('/cupon/list', body))) || []
}

async function loadPlantillas() {
  plantillas.value = (await quiet(() => postData('/cupon/list', { plantillas: true }))) || []
}

async function loadCatalogo() {
  if (catalogo.value.productos.length) return
  const [productos, categorias, zonas] = await Promise.all([
    postData('/producto/list', { todos: true }).catch(() => []),
    postData('/categoria/list').catch(() => []),
    postData('/zona/list').catch(() => []),
  ])
  catalogo.value = { productos, categorias, zonas }
}

async function loadResultados() {
  resultados.value = await quiet(() => postData('/cupon/resultados', periodo.value))
}

function vacio(plantilla = false) {
  return { cupon_id: null, plantilla, codigo: '', nombre: '', descripcion: '', tipo: 'porcentaje', valor: 10, tope: null,
    producto_id: null, inicia: '', termina: '', canales: [], zonas: [], productos: [], categorias: [], dias: [],
    hora_desde: '', hora_hasta: '', monto_minimo: null, usos_maximos: null, usos_por_cliente: null, acumulable: false,
    cliente: null, emitir_desde: plantilla ? 20000 : null, dias_validez: plantilla ? 30 : null, usos: 0 }
}

async function nuevo(plantilla = false, cliente = null) {
  await loadCatalogo()
  form.value = { ...vacio(plantilla), cliente }
  clienteBusqueda.value = { texto: '', resultados: [] }
}

async function editar(c) {
  await loadCatalogo()
  form.value = { ...vacio(c.plantilla), ...c, cupon_id: c.id, inicia: c.inicia || '', termina: c.termina || '',
    hora_desde: c.hora_desde || '', hora_hasta: c.hora_hasta || '',
    cliente: c.cliente_id ? { id: c.cliente_id, nombre: c.cliente } : null }
}

function alternar(lista, valor) {
  const i = lista.indexOf(valor)
  i >= 0 ? lista.splice(i, 1) : lista.push(valor)
}

async function buscarCliente() {
  const texto = clienteBusqueda.value.texto.trim()
  if (texto.length < 3) return
  clienteBusqueda.value.resultados = await postData('/cliente/buscar', { texto }).catch(() => [])
}

async function guardar() {
  const f = form.value
  const numero = (v) => (v === '' || v === null || v === undefined ? null : Number(v))
  const body = {
    cupon_id: f.cupon_id, plantilla: f.plantilla, codigo: f.codigo.trim() || null, nombre: f.nombre.trim(),
    descripcion: f.descripcion?.trim() || null, tipo: f.tipo, valor: numero(f.valor), tope: f.tipo === 'porcentaje' ? numero(f.tope) : null,
    producto_id: f.tipo === 'producto' ? f.producto_id : null, inicia: f.inicia || null, termina: f.termina || null,
    canales: f.canales, zonas: f.zonas, productos: f.productos, categorias: f.categorias, dias: f.dias,
    hora_desde: f.hora_desde || null, hora_hasta: f.hora_hasta || null, monto_minimo: numero(f.monto_minimo),
    usos_maximos: numero(f.usos_maximos), usos_por_cliente: numero(f.usos_por_cliente), acumulable: f.acumulable,
    cliente_id: f.cliente?.id || null, emitir_desde: numero(f.emitir_desde), dias_validez: numero(f.dias_validez),
  }
  const ok = await attempt(() => postData('/cupon/save', body), { success: (c) => c && (f.cupon_id ? 'Cupón actualizado.' : c.plantilla ? 'Plantilla creada.' : `Cupón ${c.codigo} creado.`) })
  if (!ok) return
  form.value = null
  f.plantilla ? loadPlantillas() : loadCupones()
}

async function cambiarEstado(c, estado) {
  const ok = await attempt(() => postData('/cupon/change_status', { cupon_id: c.id, estado }),
    { success: estado === 'pausado' ? 'Cupón pausado.' : estado === 'anulado' ? 'Cupón anulado.' : 'Cupón activo.' })
  if (ok) c.plantilla ? loadPlantillas() : loadCupones()
}

async function enviar(c) {
  const datos = await attempt(() => postData('/cupon/enviar', { cupon_id: c.id }))
  if (!datos) return
  const url = enlaceWhatsapp(datos.telefono, datos.mensaje)
  if (url) window.open(url, '_blank', 'noopener')
  loadCupones()
}

async function verDetalle(c) {
  detalle.value = await quiet(() => postData('/cupon/get', { cupon_id: c.id }))
}

function vigencia(c) {
  if (!c.inicia && !c.termina) return 'Sin fecha límite'
  if (!c.inicia) return `Hasta ${formatDate(c.termina)}`
  if (!c.termina) return `Desde ${formatDate(c.inicia)}`
  return `${formatDate(c.inicia)} a ${formatDate(c.termina)}`
}

function cambiarVista(v) {
  vista.value = v
  if (v === 'plantillas') loadPlantillas()
  if (v === 'resultados') loadResultados()
}

onMounted(async () => {
  if (auth.can('cupones.gestionar')) loadCupones()
  else loadResultados()
  // Desde la ficha del cliente: crear un cupón personal para él
  if (route.query.cliente && auth.can('cupones.gestionar')) {
    nuevo(false, { id: Number(route.query.cliente), nombre: route.query.nombre || 'Cliente' })
  }
})
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Cupones</h1>
        <p>Descuentos con reglas de uso. Caja o el cliente escriben el código y el sistema revisa cada regla.</p>
      </div>
      <div v-if="auth.can('cupones.gestionar') && vista !== 'resultados'" class="actions">
        <button class="btn" type="button" @click="nuevo(vista === 'plantillas')">{{ vista === 'plantillas' ? 'Nueva plantilla' : 'Nuevo cupón' }}</button>
      </div>
    </header>

    <div class="vistas" role="tablist">
      <template v-if="auth.can('cupones.gestionar')">
        <button role="tab" type="button" :aria-selected="vista === 'cupones'" @click="cambiarVista('cupones')">Cupones</button>
        <button role="tab" type="button" :aria-selected="vista === 'plantillas'" @click="cambiarVista('plantillas')">Próxima visita</button>
      </template>
      <button v-if="auth.can('cupones.ver')" role="tab" type="button" :aria-selected="vista === 'resultados'"
              @click="cambiarVista('resultados')">Resultados</button>
    </div>

    <section v-if="vista === 'cupones'">
      <form class="filtros" @submit.prevent="loadCupones">
        <input v-model="filtros.buscar" class="input" type="search" placeholder="Código o nombre" aria-label="Buscar cupón">
        <select v-model="filtros.estado" class="select" aria-label="Estado">
          <option value="">Activos y pausados</option>
          <option value="activo">Activos</option>
          <option value="pausado">Pausados</option>
          <option value="anulado">Anulados</option>
        </select>
        <button class="btn btn-secundario" type="submit">Buscar</button>
      </form>
      <div class="panel table-wrap">
        <table class="table">
          <thead><tr><th>Código</th><th>Beneficio</th><th>Vigencia</th><th class="num">Usos</th><th>Estado</th><th></th></tr></thead>
          <tbody>
            <tr v-for="c in cupones.filter((x) => filtros.estado || x.estado !== 'anulado')" :key="c.id">
              <td><button class="codigo" type="button" @click="verDetalle(c)">{{ c.codigo }}</button>
                <small class="muted bloque">{{ c.nombre }}<template v-if="c.cliente"> · para {{ c.cliente }}</template>
                  <template v-if="c.origen === 'automatico'"> · automático</template></small></td>
              <td>{{ c.beneficio }}<small v-if="c.monto_minimo" class="muted bloque">compra mínima {{ formatMoney(c.monto_minimo) }}</small>
                <small v-if="c.canales.length" class="muted bloque">{{ c.canales.map((x) => CANALES[x]).join(', ') }}</small></td>
              <td class="nowrap">{{ vigencia(c) }}</td>
              <td class="num">{{ c.usos }}<template v-if="c.usos_maximos"> / {{ c.usos_maximos }}</template></td>
              <td><StatusChip :estado="c.estado_actual" size="sm" /></td>
              <td><div class="actions">
                <button v-if="c.estado !== 'anulado'" class="btn btn-secundario btn-sm" type="button" @click="editar(c)">Editar</button>
                <button v-if="c.estado === 'activo'" class="btn btn-secundario btn-sm" type="button" @click="cambiarEstado(c, 'pausado')">Pausar</button>
                <button v-if="c.estado === 'pausado'" class="btn btn-secundario btn-sm" type="button" @click="cambiarEstado(c, 'activo')">Activar</button>
                <button v-if="c.cliente_contactable && ['activo', 'programado'].includes(c.estado_actual)" class="btn btn-secundario btn-sm"
                        type="button" @click="enviar(c)">{{ c.enviado_en ? 'Reenviar' : 'Enviar' }} por WhatsApp</button>
              </div></td>
            </tr>
          </tbody>
        </table>
        <p v-if="!cupones.length" class="empty">No hay cupones. Crea uno para tu próxima campaña.</p>
      </div>
      <p class="muted nota">Un cupón se envía por WhatsApp solo si es personal y el cliente autorizó recibir promociones.</p>
    </section>

    <section v-else-if="vista === 'plantillas'">
      <p class="intro">Cuando un cliente identificado paga una compra desde cierto valor, recibe un cupón personal para su próxima
        visita. Sale impreso en el comprobante y se le puede enviar por WhatsApp si autorizó promociones.</p>
      <div class="panel table-wrap">
        <table class="table">
          <thead><tr><th>Plantilla</th><th>Beneficio</th><th>Se emite con compras desde</th><th>Válido</th><th>Estado</th><th></th></tr></thead>
          <tbody>
            <tr v-for="p in plantillas" :key="p.id">
              <td>{{ p.nombre }}<small v-if="p.descripcion" class="muted bloque">{{ p.descripcion }}</small></td>
              <td>{{ p.beneficio }}<small v-if="p.monto_minimo" class="muted bloque">en compras desde {{ formatMoney(p.monto_minimo) }}</small></td>
              <td class="num">{{ formatMoney(p.emitir_desde) }}</td>
              <td>{{ p.dias_validez }} días</td>
              <td><StatusChip :estado="p.estado_actual" size="sm" /></td>
              <td><div class="actions">
                <button v-if="p.estado !== 'anulado'" class="btn btn-secundario btn-sm" type="button" @click="editar(p)">Editar</button>
                <button v-if="p.estado === 'activo'" class="btn btn-secundario btn-sm" type="button" @click="cambiarEstado(p, 'pausado')">Pausar</button>
                <button v-if="p.estado === 'pausado'" class="btn btn-secundario btn-sm" type="button" @click="cambiarEstado(p, 'activo')">Activar</button>
              </div></td>
            </tr>
          </tbody>
        </table>
        <p v-if="!plantillas.length" class="empty">Sin plantillas: no se emiten cupones automáticos.</p>
      </div>
    </section>

    <section v-else-if="vista === 'resultados'">
      <form class="filtros" @submit.prevent="loadResultados">
        <input v-model="periodo.desde" class="input" type="date" aria-label="Desde">
        <input v-model="periodo.hasta" class="input" type="date" aria-label="Hasta">
        <button class="btn btn-secundario" type="submit">Ver</button>
      </form>
      <template v-if="resultados">
        <dl class="resumen">
          <div><dt>Cupones usados</dt><dd>{{ resultados.resumen.redenciones }}</dd></div>
          <div><dt>Descuento dado</dt><dd>{{ formatMoney(resultados.resumen.descuento) }}</dd></div>
          <div><dt>Ventas con cupón</dt><dd>{{ formatMoney(resultados.resumen.ventas) }}</dd></div>
          <div class="fuerte"><dt>Costo del descuento</dt><dd>{{ resultados.resumen.costo_porcentaje }} %</dd></div>
          <div><dt>Ticket con cupón</dt><dd>{{ formatMoney(resultados.resumen.ticket_con_cupon) }}</dd></div>
          <div><dt>Ticket sin cupón</dt><dd>{{ formatMoney(resultados.resumen.ticket_sin_cupon) }}</dd></div>
          <div><dt>Clientes nuevos</dt><dd>{{ resultados.resumen.clientes_nuevos }}</dd></div>
        </dl>
        <p class="muted nota">Costo del descuento: lo descontado sobre lo que se habría vendido sin cupón.</p>

        <div v-for="tabla in [{ titulo: 'Por cupón', filas: resultados.por_cupon }, { titulo: 'Por canal', filas: resultados.por_canal },
                               { titulo: 'Quién lo aplicó', filas: resultados.por_usuario }]" :key="tabla.titulo" class="bloque-tabla">
          <h2>{{ tabla.titulo }}</h2>
          <div class="panel table-wrap">
            <table class="table">
              <thead><tr><th>{{ tabla.titulo === 'Por cupón' ? 'Cupón' : tabla.titulo === 'Por canal' ? 'Canal' : 'Usuario' }}</th>
                <th class="num">Usos</th><th class="num">Descuento</th><th class="num">Ventas</th><th class="num">Costo</th>
                <th class="num">Ticket</th><th class="num">Clientes nuevos</th></tr></thead>
              <tbody>
                <tr v-for="f in tabla.filas" :key="f.clave">
                  <td>{{ f.nombre }}<small v-if="f.nombre_cupon && f.nombre_cupon !== f.nombre" class="muted bloque">{{ f.nombre_cupon }}</small></td>
                  <td class="num">{{ f.redenciones }}</td>
                  <td class="num">{{ formatMoney(f.descuento) }}</td>
                  <td class="num">{{ formatMoney(f.ventas) }}</td>
                  <td class="num">{{ f.costo_porcentaje }} %</td>
                  <td class="num">{{ formatMoney(f.ticket_promedio) }}</td>
                  <td class="num">{{ f.clientes_nuevos }}</td>
                </tr>
              </tbody>
            </table>
            <p v-if="!tabla.filas.length" class="empty">No se usaron cupones en este periodo.</p>
          </div>
        </div>
      </template>
    </section>

    <AppModal :open="!!form" :title="form?.cupon_id ? 'Editar' : esPlantilla ? 'Nueva plantilla' : 'Nuevo cupón'" width="44rem" @close="form = null">
      <form v-if="form" class="cupon-form" @submit.prevent="guardar">
        <fieldset class="tipos">
          <legend>Qué da</legend>
          <div class="opciones">
            <button v-for="(label, valor) in TIPOS" :key="valor" type="button" :aria-pressed="form.tipo === valor"
                    :disabled="form.usos > 0 && form.tipo !== valor" @click="form.tipo = valor">{{ label }}</button>
          </div>
        </fieldset>

        <div class="form-grid">
          <div v-if="form.tipo === 'porcentaje'" class="field"><label for="cp-valor">Porcentaje</label>
            <input id="cp-valor" v-model.number="form.valor" class="input" type="number" min="1" max="100" required></div>
          <div v-if="form.tipo === 'porcentaje'" class="field"><label for="cp-tope">Descuento máximo</label>
            <input id="cp-tope" v-model.number="form.tope" class="input" type="number" min="1" placeholder="Sin tope"></div>
          <div v-if="form.tipo === 'valor'" class="field"><label for="cp-valor">Valor del descuento</label>
            <input id="cp-valor" v-model.number="form.valor" class="input" type="number" min="1" required></div>
          <template v-if="form.tipo === 'producto'">
            <div class="field"><label for="cp-prod">Producto</label>
              <select id="cp-prod" v-model="form.producto_id" class="select" required>
                <option :value="null" disabled>Elige el producto</option>
                <option v-for="p in catalogo.productos" :key="p.id" :value="p.id">{{ p.nombre }}</option>
              </select></div>
            <div class="field"><label for="cp-pct">Descuento sobre una unidad</label>
              <select id="cp-pct" v-model.number="form.valor" class="select">
                <option :value="100">Gratis</option><option :value="50">50 %</option><option :value="30">30 %</option>
              </select></div>
          </template>
          <p v-if="form.tipo === 'envio'" class="muted ancho">El cliente no paga la tarifa del domicilio.</p>

          <div class="field"><label for="cp-nombre">Nombre</label>
            <input id="cp-nombre" v-model="form.nombre" class="input" maxlength="100" required placeholder="Campaña de mitad de mes"></div>
          <div v-if="!esPlantilla" class="field"><label for="cp-codigo">Código</label>
            <input id="cp-codigo" v-model="form.codigo" class="input codigo-input" maxlength="30" :disabled="form.usos > 0"
                   :placeholder="form.cliente ? 'Se genera solo' : 'MITADMES'" :required="!form.cliente"></div>
          <div class="field ancho"><label for="cp-desc">Lo que ve el cliente</label>
            <input id="cp-desc" v-model="form.descripcion" class="input" maxlength="200" placeholder="10 % en tu cuenta de lunes a jueves"></div>
        </div>

        <div v-if="!esPlantilla" class="cliente-cupon">
          <template v-if="form.cliente">
            <span>Cupón personal de <strong>{{ form.cliente.nombre }}</strong>: solo lo usa esa persona.</span>
            <button v-if="!form.usos" class="btn btn-secundario btn-sm" type="button" @click="form.cliente = null">Quitar</button>
          </template>
          <template v-else>
            <div class="buscar">
              <input v-model="clienteBusqueda.texto" class="input" type="search" placeholder="Asignar a un cliente (opcional)"
                     aria-label="Buscar cliente para el cupón" @keydown.enter.prevent="buscarCliente">
              <button class="btn btn-secundario btn-sm" type="button" @click="buscarCliente">Buscar</button>
            </div>
            <ul v-if="clienteBusqueda.resultados.length" class="resultados">
              <li v-for="cl in clienteBusqueda.resultados" :key="cl.id">
                <button type="button" @click="form.cliente = { id: cl.id, nombre: cl.nombre }; clienteBusqueda.resultados = []">
                  {{ cl.nombre }} <span class="muted">{{ cl.telefono_legible }}</span></button>
              </li>
            </ul>
          </template>
        </div>

        <div v-if="esPlantilla" class="form-grid">
          <div class="field"><label for="cp-emitir">Se emite con compras desde</label>
            <input id="cp-emitir" v-model.number="form.emitir_desde" class="input" type="number" min="1" required></div>
          <div class="field"><label for="cp-validez">Días de validez del cupón</label>
            <input id="cp-validez" v-model.number="form.dias_validez" class="input" type="number" min="1" max="365" required></div>
        </div>

        <div class="form-grid">
          <div class="field"><label for="cp-ini">{{ esPlantilla ? 'Emitir desde el' : 'Válido desde' }}</label>
            <input id="cp-ini" v-model="form.inicia" class="input" type="date"></div>
          <div class="field"><label for="cp-fin">{{ esPlantilla ? 'Emitir hasta el' : 'Válido hasta' }}</label>
            <input id="cp-fin" v-model="form.termina" class="input" type="date"></div>
          <div class="field"><label for="cp-min">Compra mínima</label>
            <input id="cp-min" v-model.number="form.monto_minimo" class="input" type="number" min="0" placeholder="Sin mínimo"></div>
          <div v-if="!esPlantilla" class="field"><label for="cp-usos">Usos totales</label>
            <input id="cp-usos" v-model.number="form.usos_maximos" class="input" type="number" min="1" placeholder="Sin límite"></div>
          <div v-if="!esPlantilla" class="field"><label for="cp-cli">Usos por cliente</label>
            <input id="cp-cli" v-model.number="form.usos_por_cliente" class="input" type="number" min="1" placeholder="Sin límite"></div>
        </div>
        <p v-if="form.usos_por_cliente" class="muted">Con límite por cliente, caja tiene que identificar al cliente para aplicarlo.</p>

        <details class="mas">
          <summary>Dónde y cuándo aplica</summary>
          <fieldset><legend>Canales</legend>
            <label v-for="(label, valor) in CANALES" :key="valor" class="check">
              <input type="checkbox" :checked="form.canales.includes(valor)" @change="alternar(form.canales, valor)"> {{ label }}</label>
          </fieldset>
          <fieldset v-if="catalogo.zonas.length > 1"><legend>Zonas</legend>
            <label v-for="z in catalogo.zonas" :key="z.id" class="check">
              <input type="checkbox" :checked="form.zonas.includes(z.id)" @change="alternar(form.zonas, z.id)"> {{ z.nombre }}</label>
          </fieldset>
          <fieldset><legend>Días</legend>
            <div class="opciones">
              <button v-for="(d, i) in DIAS" :key="d" type="button" :aria-pressed="form.dias.includes(i)" @click="alternar(form.dias, i)">{{ d }}</button>
            </div>
          </fieldset>
          <div class="form-grid">
            <div class="field"><label for="cp-hd">Desde la hora</label><input id="cp-hd" v-model="form.hora_desde" class="input" type="time"></div>
            <div class="field"><label for="cp-hh">Hasta la hora</label><input id="cp-hh" v-model="form.hora_hasta" class="input" type="time"></div>
          </div>
          <fieldset v-if="['porcentaje', 'valor'].includes(form.tipo)"><legend>Solo sobre estas categorías</legend>
            <label v-for="cat in catalogo.categorias" :key="cat.id" class="check">
              <input type="checkbox" :checked="form.categorias.includes(cat.id)" @change="alternar(form.categorias, cat.id)"> {{ cat.nombre }}</label>
          </fieldset>
          <label class="check"><input v-model="form.acumulable" type="checkbox"> Se puede combinar con otros cupones</label>
          <p class="muted">Sin marcar nada, aplica en todos los canales, zonas, días y horas.</p>
        </details>

        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="form = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy || form.nombre.trim().length < 3">Guardar</button>
        </div>
      </form>
    </AppModal>

    <AppModal :open="!!detalle" :title="detalle ? `Cupón ${detalle.codigo}` : ''" width="40rem" @close="detalle = null">
      <template v-if="detalle">
        <p>{{ detalle.beneficio }} · {{ vigencia(detalle) }} · <StatusChip :estado="detalle.estado_actual" size="sm" /></p>
        <h3 class="sub">Últimos usos</h3>
        <ul v-if="detalle.redenciones.length" class="usos">
          <li v-for="r in detalle.redenciones" :key="r.id">
            <span>{{ formatDate(r.fecha) }} · {{ r.cuenta || 'Cuenta abierta' }}<template v-if="r.cliente"> · {{ r.cliente }}</template>
              <small class="muted bloque">{{ CANALES[r.canal] }} · aplicó {{ r.aplicada_por }}<template v-if="r.motivo"> · {{ r.motivo }}</template></small></span>
            <span class="num">{{ formatMoney(r.valor) }}<small class="muted bloque">{{ { aplicada: 'En cuenta abierta', redimida: 'Usado', quitada: 'Quitado', revertida: 'Revertido' }[r.estado] }}</small></span>
          </li>
        </ul>
        <p v-else class="muted">Todavía no se ha usado.</p>
      </template>
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
  max-width: 18rem;
}

.codigo {
  padding: 0;
  border: none;
  background: none;
  font-family: var(--font-papel);
  font-weight: 700;
  color: var(--accion);
  text-decoration: underline;
  cursor: pointer;
}

.codigo-input {
  font-family: var(--font-papel);
  text-transform: uppercase;
}

.intro {
  max-width: 48rem;
  margin-bottom: var(--space-4);
}

.resumen {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr));
  gap: var(--space-3);
  margin: 0 0 var(--space-2);
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

.bloque-tabla {
  margin-top: var(--space-5);
}

.bloque-tabla h2 {
  font-size: var(--text-lg);
  margin-bottom: var(--space-2);
}

.cupon-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.cupon-form fieldset {
  margin: 0;
  padding: 0;
  border: none;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-4);
}

.cupon-form legend {
  font-weight: 700;
  margin-bottom: var(--space-2);
  width: 100%;
}

.opciones {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.opciones button {
  min-height: var(--toque);
  padding: 0 var(--space-3);
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

.opciones button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ancho {
  grid-column: 1 / -1;
}

.cliente-cupon {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px dashed var(--linea-fuerte);
  border-radius: var(--radio-sm);
}

.cliente-cupon > span {
  display: flex;
  justify-content: space-between;
}

.buscar {
  display: flex;
  gap: var(--space-2);
}

.buscar .input {
  flex: 1;
  min-width: 0;
}

.resultados {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.resultados button {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio-sm);
  background: var(--papel);
  text-align: left;
  cursor: pointer;
}

.mas {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio-sm);
}

.mas summary {
  font-weight: 700;
  cursor: pointer;
}

.mas[open] > :not(summary) {
  margin-top: var(--space-3);
}

.sub {
  font-size: var(--text-base);
  margin: var(--space-4) 0 var(--space-2);
}

.usos {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.usos li {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--linea);
}

.nowrap {
  white-space: nowrap;
}

.bloque {
  display: block;
}

.nota {
  margin-top: var(--space-2);
}
</style>
