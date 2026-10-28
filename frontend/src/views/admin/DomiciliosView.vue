<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { formatMoney } from '@/utils/format'
import AppModal from '@/components/AppModal.vue'

/*
  Configuración de domicilios (doc 15B): zonas de envío con tarifa fija por barrios y domiciliarios
  identificados por código. Un domiciliario con usuario ve sus entregas desde el celular.
*/
const auth = useAuthStore()
const { busy, attempt, quiet } = useAction()

const zonas = ref([])
const domiciliarios = ref([])
const usuarios = ref([])
const zona = ref(null)
const domiciliario = ref(null)

const candidatos = computed(() => usuarios.value.filter((u) => u.activo && u.roles.includes('domiciliario')))

async function load() {
  const [z, d, u] = await Promise.all([
    quiet(() => postData('/domicilio/zona/list', { todos: true })),
    quiet(() => postData('/domicilio/domiciliario/list', { todos: true })),
    auth.can('usuarios.gestionar') ? quiet(() => postData('/usuario/list')) : Promise.resolve([]),
  ])
  zonas.value = z || []
  domiciliarios.value = d || []
  usuarios.value = u || []
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
</style>
