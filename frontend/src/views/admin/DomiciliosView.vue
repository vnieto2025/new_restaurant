<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { usePrintStore } from '@/stores/print'
import { useAction } from '@/composables/useAction'
import { formatMoney } from '@/utils/format'
import AppModal from '@/components/AppModal.vue'

/*
  Configuración de domicilios (doc 15B): zonas de envío con tarifa fija por barrios y domiciliarios
  identificados por código. Un domiciliario con usuario ve sus entregas desde el celular.
  El enlace y el QR de domicilios dejan que el cliente pida desde su celular (doc 17A, sección 2.6).
*/
const auth = useAuthStore()
const printer = usePrintStore()
const { busy, attempt, quiet } = useAction()

const zonas = ref([])
const domiciliarios = ref([])
const usuarios = ref([])
const zona = ref(null)
const domiciliario = ref(null)
const web = ref(null)
const webForm = ref(null)
const copiado = ref(false)
const cambiarEnlace = ref(false)

const candidatos = computed(() => usuarios.value.filter((u) => u.activo && u.roles.includes('domiciliario')))

async function load() {
  const [z, d, u, w] = await Promise.all([
    quiet(() => postData('/domicilio/zona/list', { todos: true })),
    quiet(() => postData('/domicilio/domiciliario/list', { todos: true })),
    auth.can('usuarios.gestionar') ? quiet(() => postData('/usuario/list')) : Promise.resolve([]),
    quiet(() => postData('/domicilio/web/get')),
  ])
  zonas.value = z || []
  domiciliarios.value = d || []
  usuarios.value = u || []
  if (w) web.value = w
}

function editarWeb() {
  webForm.value = { activo: web.value.activo, aprobacion: web.value.aprobacion, mensaje: web.value.mensaje || '' }
}

async function guardarWeb(cambios = {}) {
  const body = { ...(webForm.value || { activo: web.value.activo, aprobacion: web.value.aprobacion, mensaje: web.value.mensaje || '' }), ...cambios }
  const data = await attempt(() => postData('/domicilio/web/save', { ...body, mensaje: body.mensaje?.trim() || null }),
    { success: body.activo ? 'Pedidos por la web activos.' : 'Pedidos por la web pausados.' })
  if (data) {
    web.value = data
    webForm.value = null
  }
}

async function nuevoEnlace() {
  const data = await attempt(() => postData('/domicilio/web/regenerar'), { success: 'Enlace nuevo listo. Cambia el que publicaste.' })
  if (data) web.value = data
  cambiarEnlace.value = false
}

async function copiar() {
  try {
    await navigator.clipboard.writeText(web.value.url)
    copiado.value = true
    setTimeout(() => (copiado.value = false), 2000)
  } catch {
    // Sin permiso de portapapeles el enlace queda visible para copiarlo a mano
  }
}

function imprimirQr() {
  printer.print('qr', [{ id: 'domicilio', tipo: 'domicilio', restaurante: web.value.restaurante, svg: web.value.svg }])
}

function nuevaZona() {
  zona.value = { nombre: '', barrios: '', tarifa: 0, pago_domiciliario: 0, pedido_minimo: 0, orden: zonas.value.length + 1, activo: true }
}

async function guardarZona() {
  const z = zona.value
  const body = { ...z, barrios: z.barrios?.trim() || null, tarifa: Number(z.tarifa) || 0,
    pago_domiciliario: Number(z.pago_domiciliario) || 0, pedido_minimo: Number(z.pedido_minimo) || 0 }
  const ok = await attempt(() => postData('/domicilio/zona/save', body), { success: z.zona_envio_id ? 'Zona actualizada.' : 'Zona creada.' })
  if (ok) {
    zona.value = null
    load()
  }
}

function nuevoDomiciliario() {
  domiciliario.value = { nombre: '', codigo: `D${String(domiciliarios.value.length + 1).padStart(2, '0')}`, documento: '', telefono: '',
    vinculo: 'propio', usuario_id: '' }
}

async function guardarDomiciliario() {
  const d = domiciliario.value
  const body = { ...d, documento: d.documento?.trim() || null, telefono: d.telefono?.trim() || null,
    usuario_id: d.usuario_id ? Number(d.usuario_id) : null }
  const ok = await attempt(() => postData('/domicilio/domiciliario/save', body),
    { success: d.domiciliario_id ? 'Domiciliario actualizado.' : 'Domiciliario creado.' })
  if (ok) {
    domiciliario.value = null
    load()
  }
}

async function cambiarEstado(d) {
  const ok = await attempt(() => postData('/domicilio/domiciliario/change_status', { domiciliario_id: d.id, activo: !d.activo }),
    { success: d.activo ? 'Domiciliario desactivado.' : 'Domiciliario activado.' })
  if (ok !== undefined) load()
}

onMounted(load)
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Domicilios</h1>
        <p>Zonas de envío con su tarifa y las personas que llevan los pedidos.</p>
      </div>
      <div class="actions">
        <RouterLink v-if="auth.can('domicilios.despachar')" class="btn btn-secundario" :to="{ name: 'entregas' }">Ver entregas</RouterLink>
      </div>
    </header>

    <section v-if="web" class="bloque">
      <div class="titulo">
        <h2>Pedidos por la web</h2>
        <button class="btn btn-secundario btn-sm" type="button" @click="editarWeb">Configurar</button>
      </div>
      <div class="panel web">
        <div class="web-qr" v-html="web.svg"></div>
        <div class="web-datos">
          <p class="web-estado" :class="{ activo: web.activo }">
            <strong>{{ web.activo ? 'Recibiendo pedidos' : 'Pausado' }}</strong>
            · {{ web.aprobacion ? 'cada pedido se confirma en Entregas antes de ir a cocina' : 'los pedidos van directo a cocina' }}
          </p>
          <p class="muted">Publica este enlace en tus redes o en WhatsApp, o imprime el QR para volantes y empaques.
            El cliente ve la carta, elige su zona y deja su dirección.</p>
          <p class="enlace"><a :href="web.url" target="_blank" rel="noopener">{{ web.url }}</a></p>
          <p v-if="web.mensaje" class="muted">Aviso en la carta: «{{ web.mensaje }}»</p>
          <p v-if="!web.zonas" class="aviso">Crea una zona de envío activa para poder recibir pedidos.</p>
          <p v-if="web.pago_en_linea" class="muted">El cliente puede pagar en línea o al recibir.</p>
          <div class="actions">
            <button class="btn btn-secundario btn-sm" type="button" @click="copiar">{{ copiado ? 'Copiado' : 'Copiar enlace' }}</button>
            <button class="btn btn-secundario btn-sm" type="button" @click="imprimirQr">Imprimir QR</button>
            <button class="btn btn-secundario btn-sm" type="button" :disabled="busy" @click="cambiarEnlace = true">Generar enlace nuevo</button>
            <button class="btn btn-sm" type="button" :disabled="busy || (!web.activo && !web.zonas)"
                    @click="guardarWeb({ activo: !web.activo })">{{ web.activo ? 'Pausar' : 'Activar' }}</button>
          </div>
        </div>
      </div>
    </section>

    <section class="bloque">
      <div class="titulo">
        <h2>Zonas de envío</h2>
        <button class="btn btn-sm" type="button" @click="nuevaZona">Crear zona</button>
      </div>
      <div class="panel table-wrap">
        <table class="table">
          <thead><tr><th>Zona</th><th class="num">Tarifa al cliente</th><th class="num">Pago al domiciliario</th><th class="num">Pedido mínimo</th><th></th></tr></thead>
          <tbody>
            <tr v-for="z in zonas" :key="z.id" :class="{ muted: !z.activo }">
              <td><strong>{{ z.nombre }}</strong><span v-if="!z.activo"> (inactiva)</span>
                <small v-if="z.barrios" class="muted bloque-texto">{{ z.barrios }}</small></td>
              <td class="num">{{ formatMoney(z.tarifa) }}</td>
              <td class="num">{{ formatMoney(z.pago_domiciliario) }}</td>
              <td class="num">{{ z.pedido_minimo ? formatMoney(z.pedido_minimo) : '—' }}</td>
              <td class="actions"><button class="btn btn-secundario btn-sm" type="button" @click="zona = { ...z, zona_envio_id: z.id }">Editar</button></td>
            </tr>
          </tbody>
        </table>
        <p v-if="!zonas.length" class="empty">Crea las zonas a las que llevas pedidos, por ejemplo «Centro» o «Norte», con su tarifa.</p>
      </div>
    </section>

    <section class="bloque">
      <div class="titulo">
        <h2>Domiciliarios</h2>
        <button class="btn btn-sm" type="button" @click="nuevoDomiciliario">Crear domiciliario</button>
      </div>
      <div class="panel table-wrap">
        <table class="table">
          <thead><tr><th>Código</th><th>Nombre</th><th>Vínculo</th><th>Acceso</th><th></th></tr></thead>
          <tbody>
            <tr v-for="d in domiciliarios" :key="d.id" :class="{ muted: !d.activo }">
              <td><strong>{{ d.codigo }}</strong></td>
              <td>{{ d.nombre }}<span v-if="!d.activo"> (inactivo)</span>
                <small class="muted bloque-texto">{{ d.telefono || 'Sin teléfono' }}<template v-if="d.en_camino"> · {{ d.en_camino }} en camino</template></small></td>
              <td>{{ d.vinculo === 'propio' ? 'Propio' : 'Independiente' }}</td>
              <td>{{ d.usuario ? `Usuario ${d.usuario}` : 'Sin usuario' }}</td>
              <td class="actions">
                <button class="btn btn-secundario btn-sm" type="button" @click="domiciliario = { ...d, domiciliario_id: d.id, usuario_id: d.usuario_id || '' }">Editar</button>
                <button class="btn btn-secundario btn-sm" type="button" :disabled="busy" @click="cambiarEstado(d)">{{ d.activo ? 'Desactivar' : 'Activar' }}</button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="!domiciliarios.length" class="empty">Registra a tus domiciliarios con un código para asignarles las entregas.</p>
      </div>
      <p class="muted nota">El vínculo es informativo: cómo se les paga lo define el restaurante con su contador.</p>
    </section>

    <AppModal :open="!!zona" :title="zona?.zona_envio_id ? `Editar ${zona.nombre}` : 'Crear zona de envío'" width="34rem" @close="zona = null">
      <form v-if="zona" @submit.prevent="guardarZona">
        <div class="form-grid">
          <div class="field"><label for="ze-nombre">Nombre</label>
            <input id="ze-nombre" v-model="zona.nombre" class="input" required maxlength="60"></div>
          <div class="field"><label for="ze-tarifa">Tarifa al cliente</label>
            <input id="ze-tarifa" v-model.number="zona.tarifa" class="input" type="number" min="0" inputmode="numeric"></div>
          <div class="field"><label for="ze-pago">Pago al domiciliario</label>
            <input id="ze-pago" v-model.number="zona.pago_domiciliario" class="input" type="number" min="0" inputmode="numeric"></div>
          <div class="field"><label for="ze-min">Pedido mínimo</label>
            <input id="ze-min" v-model.number="zona.pedido_minimo" class="input" type="number" min="0" inputmode="numeric"></div>
        </div>
        <div class="field espacio"><label for="ze-barrios">Barrios que cubre</label>
          <textarea id="ze-barrios" v-model="zona.barrios" class="input" rows="3" maxlength="500" placeholder="Separados por coma: Centro, La Candelaria…"></textarea>
          <span class="hint">Con esta lista el mostrador sugiere la zona al escribir el barrio.</span></div>
        <label class="check espacio"><input v-model="zona.activo" type="checkbox"> Recibe domicilios</label>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="zona = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy">Guardar</button>
        </div>
      </form>
    </AppModal>

    <AppModal :open="!!domiciliario" :title="domiciliario?.domiciliario_id ? `Editar ${domiciliario.nombre}` : 'Crear domiciliario'" width="34rem" @close="domiciliario = null">
      <form v-if="domiciliario" @submit.prevent="guardarDomiciliario">
        <div class="form-grid">
          <div class="field"><label for="dm-nombre">Nombre</label>
            <input id="dm-nombre" v-model="domiciliario.nombre" class="input" required maxlength="100"></div>
          <div class="field"><label for="dm-codigo">Código</label>
            <input id="dm-codigo" v-model="domiciliario.codigo" class="input" required maxlength="10"></div>
          <div class="field"><label for="dm-tel">Teléfono</label>
            <input id="dm-tel" v-model="domiciliario.telefono" class="input" maxlength="20" inputmode="tel"></div>
          <div class="field"><label for="dm-doc">Documento</label>
            <input id="dm-doc" v-model="domiciliario.documento" class="input" maxlength="30"></div>
          <div class="field"><label for="dm-vinculo">Vínculo</label>
            <select id="dm-vinculo" v-model="domiciliario.vinculo" class="select">
              <option value="propio">Propio del restaurante</option>
              <option value="independiente">Independiente</option>
            </select></div>
          <div v-if="auth.can('usuarios.gestionar')" class="field"><label for="dm-usuario">Usuario para el celular</label>
            <select id="dm-usuario" v-model="domiciliario.usuario_id" class="select">
              <option value="">Sin usuario</option>
              <option v-for="u in candidatos" :key="u.id" :value="u.id">{{ u.nombre }} ({{ u.usuario }})</option>
            </select>
            <span class="hint">Crea el usuario en Personal con el rol Domiciliario.</span></div>
        </div>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="domiciliario = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy">Guardar</button>
        </div>
      </form>
    </AppModal>

    <AppModal :open="!!webForm" title="Pedidos por la web" width="32rem" @close="webForm = null">
      <form v-if="webForm" @submit.prevent="guardarWeb()">
        <label class="check"><input v-model="webForm.activo" type="checkbox"> Recibir pedidos por el enlace y el QR</label>
        <label class="check espacio"><input v-model="webForm.aprobacion" type="checkbox"> Confirmar cada pedido antes de enviarlo a cocina</label>
        <p class="hint">Recomendado: así revisas la dirección y evitas pedidos falsos. Se confirman en Entregas.</p>
        <div class="field espacio">
          <label for="web-mensaje">Aviso en la carta</label>
          <input id="web-mensaje" v-model="webForm.mensaje" class="input" maxlength="200"
                 placeholder="Domicilios de 11:00 a. m. a 9:00 p. m. Tiempo estimado: 40 minutos.">
        </div>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="webForm = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy">Guardar</button>
        </div>
      </form>
    </AppModal>

    <AppModal :open="cambiarEnlace" title="Generar enlace nuevo" width="28rem" @close="cambiarEnlace = false">
      <p>El enlace y el QR que ya publicaste dejarán de funcionar al instante. Úsalo si alguien está enviando pedidos falsos.</p>
      <div class="form-actions">
        <button class="btn btn-secundario" type="button" @click="cambiarEnlace = false">Volver</button>
        <button class="btn btn-peligro" type="button" :disabled="busy" @click="nuevoEnlace">Generar enlace nuevo</button>
      </div>
    </AppModal>
  </div>
</template>

<style scoped>
.bloque {
  margin-bottom: var(--space-6);
}

.titulo {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.titulo h2 {
  font-size: var(--text-lg);
}

.bloque-texto {
  display: block;
}

.espacio {
  margin-top: var(--space-3);
}

.nota {
  margin-top: var(--space-2);
}

.web {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-5);
  padding: var(--space-4);
}

.web-qr {
  flex: none;
  width: 9rem;
}

.web-qr :deep(svg) {
  width: 100%;
  height: auto;
}

.web-datos {
  flex: 1 1 18rem;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.web-estado strong {
  color: var(--acero);
}

.web-estado.activo strong {
  color: var(--estado-entregado);
}

.aviso {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radio-sm);
  background: var(--estado-proceso-suave);
}

.enlace {
  overflow-wrap: anywhere;
  font-family: var(--font-papel);
}
</style>
