<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { formatMoney, formatDate, TIPOS_IDENTIFICACION } from '@/utils/format'
import { costoReferencia, enlaceWhatsapp } from '@/utils/inventario'
import AppModal from '@/components/AppModal.vue'
import StatusChip from '@/components/StatusChip.vue'

/*
  Proveedores (doc 24): datos de contacto, condiciones, qué insumos surte cada uno y la evolución
  de sus precios. Un proveedor con compras no se borra: se inactiva (RN-PRV-01).
*/
const auth = useAuthStore()
const { busy, attempt, quiet } = useAction()

const proveedores = ref([])
const insumos = ref([])
const buscar = ref('')
const verInactivos = ref(false)
const form = ref(null)
const detalle = ref(null)
const pestana = ref('insumos')
const surte = ref([])

const puedeGestionar = computed(() => auth.can('proveedores.gestionar'))
const visibles = computed(() => proveedores.value.filter((p) =>
  (verInactivos.value || p.activo) && (!buscar.value || p.nombre.toLowerCase().includes(buscar.value.toLowerCase()))))
const porId = computed(() => Object.fromEntries(insumos.value.map((i) => [i.id, i])))
const comprables = computed(() => insumos.value.filter((i) => i.activo && !i.es_preparacion))

async function load() {
  const [p, i] = await Promise.all([
    quiet(() => postData('/proveedor/list', { todos: true })),
    puedeGestionar.value ? quiet(() => postData('/insumo/list', { todos: true })) : Promise.resolve([]),
  ])
  proveedores.value = p || []
  insumos.value = i || []
}

function nuevo() {
  form.value = { nombre: '', razon_social: '', tipo_documento: '', documento: '', contacto: '', telefono: '', whatsapp: '',
    correo: '', direccion: '', forma_pago: 'contado', plazo_dias: 0, dias_entrega: '', pedido_minimo: 0, notas: '' }
}

function editar(p) {
  form.value = Object.fromEntries(Object.entries({ ...p, proveedor_id: p.id }).map(([k, v]) => [k, v ?? '']))
}

async function guardar() {
  const editando = !!form.value.proveedor_id
  const body = Object.fromEntries(Object.entries(form.value).map(([k, v]) => [k, typeof v === 'string' ? (v.trim() || null) : v]))
  body.plazo_dias = Number(body.plazo_dias) || 0
  body.pedido_minimo = Number(body.pedido_minimo) || 0
  const data = await attempt(() => postData(editando ? '/proveedor/update' : '/proveedor/create', body),
    { success: editando ? 'Proveedor actualizado.' : 'Proveedor creado.' })
  if (data) {
    form.value = null
    await load()
    if (detalle.value?.id === data.id) abrir(data)
  }
}

async function cambiarEstado(p) {
  await attempt(() => postData('/proveedor/change_status', { proveedor_id: p.id, activo: !p.activo }),
    { success: p.activo ? 'Proveedor inactivado. Su historial se conserva.' : 'Proveedor activado.' })
  load()
}

async function abrir(p) {
  const data = await attempt(() => postData('/proveedor/get', { proveedor_id: p.id }))
  if (!data) return
  detalle.value = data
  pestana.value = 'insumos'
  surte.value = data.insumos.map((i) => ({ insumo_id: i.insumo_id, presentacion_id: i.presentacion_id || '', preferido: i.preferido }))
}

function agregarInsumo() {
  surte.value.push({ insumo_id: '', presentacion_id: '', preferido: false })
}

async function guardarInsumos() {
  const data = await attempt(() => postData('/proveedor/insumos', {
    proveedor_id: detalle.value.id,
    insumos: surte.value.filter((s) => s.insumo_id).map((s) => ({
      insumo_id: Number(s.insumo_id), presentacion_id: s.presentacion_id ? Number(s.presentacion_id) : null, preferido: s.preferido,
    })),
  }), { success: 'Insumos guardados.' })
  if (data) {
    abrir(detalle.value)
    load()
  }
}

function precioActual(insumoId) {
  return detalle.value?.insumos.find((i) => i.insumo_id === Number(insumoId))
}

function condiciones(p) {
  const partes = [p.forma_pago === 'credito' ? `Crédito ${p.plazo_dias} días` : 'Contado']
  if (p.dias_entrega) partes.push(p.dias_entrega)
  if (p.pedido_minimo) partes.push(`mínimo ${formatMoney(p.pedido_minimo)}`)
  return partes.join(' · ')
}

onMounted(load)
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Proveedores</h1>
        <p>A quién se le compra, en qué condiciones y a qué precio.</p>
      </div>
      <div v-if="puedeGestionar" class="actions">
        <button class="btn" type="button" @click="nuevo">Crear proveedor</button>
      </div>
    </header>

    <div class="filtros">
      <input v-model="buscar" class="input" type="search" placeholder="Buscar proveedor" aria-label="Buscar proveedor">
      <label class="check"><input v-model="verInactivos" type="checkbox"> Ver inactivos</label>
    </div>

    <div class="panel table-wrap">
      <table class="table">
        <thead><tr><th>Proveedor</th><th>Contacto</th><th>Condiciones</th><th class="num">Comprado 90 días</th><th></th></tr></thead>
        <tbody>
          <tr v-for="p in visibles" :key="p.id" :class="{ muted: !p.activo }">
            <td><strong>{{ p.nombre }}</strong><span v-if="!p.activo"> (inactivo)</span>
              <small class="muted bloque">{{ p.insumos ? `${p.insumos} insumos` : 'Sin insumos asignados' }}</small></td>
            <td>{{ p.contacto || '—' }}<small v-if="p.whatsapp || p.telefono" class="muted bloque">{{ p.whatsapp || p.telefono }}</small></td>
            <td>{{ condiciones(p) }}</td>
            <td class="num">{{ formatMoney(p.comprado_90_dias) }}<small class="muted bloque">{{ p.compras_90_dias }} compras</small></td>
            <td class="actions">
              <button class="btn btn-secundario btn-sm" type="button" @click="abrir(p)">Ver</button>
              <button v-if="puedeGestionar" class="btn btn-secundario btn-sm" type="button" @click="editar(p)">Editar</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!visibles.length" class="empty">
        {{ proveedores.length ? 'Ningún proveedor coincide.' : 'Registra a quién le compras: así el sistema sugiere a quién pedir y avisa si sube precios.' }}
      </p>
    </div>

    <AppModal :open="!!detalle" :title="detalle?.nombre || ''" width="52rem" @close="detalle = null">
      <template v-if="detalle">
        <p class="muted">
          {{ condiciones(detalle) }}<template v-if="detalle.documento"> · {{ detalle.tipo_documento }} {{ detalle.documento }}</template>
        </p>
        <p v-if="detalle.whatsapp || detalle.telefono" class="contacto">
          {{ detalle.contacto }} {{ detalle.whatsapp || detalle.telefono }}
          <a v-if="enlaceWhatsapp(detalle.whatsapp, '')" :href="enlaceWhatsapp(detalle.whatsapp, '')" target="_blank" rel="noopener">Abrir WhatsApp</a>
        </p>
        <p v-if="detalle.notas" class="muted">{{ detalle.notas }}</p>

        <div class="vistas" role="tablist">
          <button role="tab" type="button" :aria-selected="pestana === 'insumos'" @click="pestana = 'insumos'">Insumos que surte</button>
          <button role="tab" type="button" :aria-selected="pestana === 'precios'" @click="pestana = 'precios'">Precios</button>
          <button role="tab" type="button" :aria-selected="pestana === 'compras'" @click="pestana = 'compras'">Compras</button>
        </div>

        <section v-if="pestana === 'insumos'">
          <template v-if="puedeGestionar">
            <div class="table-wrap">
              <table class="table">
                <thead><tr><th>Insumo</th><th>Presentación habitual</th><th class="num">Último precio</th><th>Preferido</th><th></th></tr></thead>
                <tbody>
                  <tr v-for="(s, i) in surte" :key="i">
                    <td>
                      <select v-model="s.insumo_id" class="select insumo" :aria-label="`Insumo ${i + 1}`">
                        <option value="" disabled>Elige un insumo</option>
                        <option v-for="ins in comprables" :key="ins.id" :value="ins.id">{{ ins.nombre }}</option>
                      </select>
                    </td>
                    <td>
                      <select v-if="porId[s.insumo_id]?.presentaciones.length" v-model="s.presentacion_id" class="select" :aria-label="`Presentación ${i + 1}`">
                        <option value="">{{ porId[s.insumo_id].unidad }}</option>
                        <option v-for="p in porId[s.insumo_id].presentaciones" :key="p.id" :value="p.id">{{ p.nombre }}</option>
                      </select>
                      <span v-else class="muted">{{ porId[s.insumo_id]?.unidad }}</span>
                    </td>
                    <td class="num nowrap">
                      <template v-if="precioActual(s.insumo_id)?.ultimo_precio != null">
                        {{ formatMoney(Math.round(precioActual(s.insumo_id).ultimo_precio)) }}
                        <small class="muted bloque">{{ precioActual(s.insumo_id).presentacion || precioActual(s.insumo_id).unidad }}</small>
                      </template>
                      <span v-else class="muted">—</span>
                    </td>
                    <td><label class="check"><input v-model="s.preferido" type="checkbox" :aria-label="`Preferido ${i + 1}`"> Sí</label></td>
                    <td><button class="btn btn-secundario btn-sm" type="button" @click="surte.splice(i, 1)">Quitar</button></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p class="muted">El preferido es a quien se sugiere comprar cuando el insumo baja de su mínimo. Solo hay uno por insumo.</p>
            <div class="form-actions">
              <button class="btn btn-secundario" type="button" @click="agregarInsumo">Agregar insumo</button>
              <button class="btn" type="button" :disabled="busy" @click="guardarInsumos">Guardar insumos</button>
            </div>
          </template>
          <ul v-else class="lista">
            <li v-for="i in detalle.insumos" :key="i.insumo_id">{{ i.insumo }}<template v-if="i.preferido"> · preferido</template></li>
          </ul>
        </section>

        <section v-else-if="pestana === 'precios'">
          <div class="table-wrap">
            <table class="table">
              <thead><tr><th>Fecha</th><th>Insumo</th><th class="num">Precio pagado</th><th class="num">Equivale a</th><th>Compra</th></tr></thead>
              <tbody>
                <tr v-for="(p, i) in detalle.precios" :key="i">
                  <td>{{ formatDate(p.fecha) }}</td>
                  <td>{{ p.insumo }}</td>
                  <td class="num nowrap">{{ formatMoney(Math.round(p.precio_unitario)) }}<small class="muted bloque">{{ p.presentacion || p.unidad }}</small></td>
                  <td class="num nowrap">{{ formatMoney(costoReferencia(p.costo_unitario, p.unidad).valor) }}
                    <small class="muted">/{{ costoReferencia(p.costo_unitario, p.unidad).por }}</small></td>
                  <td>{{ p.numero }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-if="!detalle.precios.length" class="empty">Aún no hay compras recibidas de este proveedor.</p>
        </section>

        <section v-else>
          <div class="table-wrap">
            <table class="table">
              <thead><tr><th>N.º</th><th>Fecha</th><th>Estado</th><th class="num">Recibido</th></tr></thead>
              <tbody>
                <tr v-for="c in detalle.compras" :key="c.id">
                  <td>{{ c.numero }}</td>
                  <td>{{ formatDate(c.fecha) }}</td>
                  <td><StatusChip :estado="c.estado" :label="c.estado_texto" size="sm" /></td>
                  <td class="num">{{ formatMoney(c.valor_recibido) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-if="!detalle.compras.length" class="empty">Aún no hay compras a este proveedor.</p>
          <RouterLink :to="{ name: 'admin-compras', query: { vista: 'historial' } }">Ver todas las compras</RouterLink>
        </section>
      </template>
    </AppModal>

    <AppModal :open="!!form" :title="form?.proveedor_id ? `Editar ${form.nombre}` : 'Crear proveedor'" width="42rem" @close="form = null">
      <form v-if="form" @submit.prevent="guardar">
        <div class="form-grid">
          <div class="field"><label for="pv-nombre">Nombre comercial</label>
            <input id="pv-nombre" v-model="form.nombre" class="input" required maxlength="100"></div>
          <div class="field"><label for="pv-razon">Razón social</label>
            <input id="pv-razon" v-model="form.razon_social" class="input" maxlength="150" placeholder="Opcional"></div>
          <div class="field"><label for="pv-tipo">Tipo de documento</label>
            <select id="pv-tipo" v-model="form.tipo_documento" class="select">
              <option value="">Sin documento</option>
              <option v-for="(label, valor) in TIPOS_IDENTIFICACION" :key="valor" :value="valor">{{ label }}</option>
            </select></div>
          <div class="field"><label for="pv-doc">Número</label>
            <input id="pv-doc" v-model="form.documento" class="input" maxlength="30" :disabled="!form.tipo_documento"></div>
          <div class="field"><label for="pv-contacto">Persona de contacto</label>
            <input id="pv-contacto" v-model="form.contacto" class="input" maxlength="100"></div>
          <div class="field"><label for="pv-wa">WhatsApp</label>
            <input id="pv-wa" v-model="form.whatsapp" class="input" maxlength="20" inputmode="tel"></div>
          <div class="field"><label for="pv-tel">Teléfono</label>
            <input id="pv-tel" v-model="form.telefono" class="input" maxlength="20" inputmode="tel"></div>
          <div class="field"><label for="pv-correo">Correo</label>
            <input id="pv-correo" v-model="form.correo" class="input" type="email" maxlength="120"></div>
          <div class="field"><label for="pv-pago">Forma de pago habitual</label>
            <select id="pv-pago" v-model="form.forma_pago" class="select">
              <option value="contado">Contado</option>
              <option value="credito">Crédito</option>
            </select></div>
          <div v-if="form.forma_pago === 'credito'" class="field"><label for="pv-plazo">Plazo (días)</label>
            <input id="pv-plazo" v-model.number="form.plazo_dias" class="input" type="number" min="0" max="365"></div>
          <div class="field"><label for="pv-dias">Días de entrega</label>
            <input id="pv-dias" v-model="form.dias_entrega" class="input" maxlength="80" placeholder="Martes y viernes"></div>
          <div class="field"><label for="pv-min">Pedido mínimo</label>
            <input id="pv-min" v-model.number="form.pedido_minimo" class="input" type="number" min="0" inputmode="numeric"></div>
        </div>
        <div class="field espacio"><label for="pv-dir">Dirección</label>
          <input id="pv-dir" v-model="form.direccion" class="input" maxlength="200" placeholder="Opcional"></div>
        <div class="field espacio"><label for="pv-notas">Notas</label>
          <input id="pv-notas" v-model="form.notas" class="input" maxlength="500" placeholder="Calidad, trato, cumplimiento"></div>
        <div class="form-actions">
          <button v-if="form.proveedor_id" class="btn btn-secundario" type="button" :disabled="busy" @click="cambiarEstado({ id: form.proveedor_id, activo: form.activo }); form = null">
            {{ form.activo ? 'Inactivar' : 'Activar' }}</button>
          <button class="btn btn-secundario" type="button" @click="form = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy">Guardar</button>
        </div>
      </form>
    </AppModal>
  </div>
</template>

<style scoped>
.filtros {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.filtros .input {
  width: auto;
  flex: 1 1 12rem;
  max-width: 20rem;
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

.contacto {
  margin: var(--space-1) 0;
}

.contacto a {
  margin-left: var(--space-2);
}

.vistas {
  display: flex;
  margin: var(--space-3) 0 var(--space-4);
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

.table .insumo {
  min-width: 12rem;
}

.lista {
  padding-left: var(--space-5);
}
</style>
