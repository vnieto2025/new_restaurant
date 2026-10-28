<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { formatDateTime, ROLES } from '@/utils/format'
import AppModal from '@/components/AppModal.vue'

const auth = useAuthStore()
const { busy, attempt, quiet } = useAction()

const usuarios = ref([])
const roles = ref([])
const zonas = ref([])
const puntos = ref([])
const form = ref(null)
const pinForm = ref(null)

const nombreZona = (id) => zonas.value.find((z) => z.id === id)?.nombre
const nombrePunto = (id) => puntos.value.find((p) => p.id === id)?.nombre
const pideZonas = computed(() => form.value?.roles.includes('mesero'))
const pidePuntos = computed(() => form.value?.roles.includes('cocina'))

async function load() {
  const [u, r, z, p] = await Promise.all([
    quiet(() => postData('/usuario/list', { todos: true })),
    quiet(() => postData('/usuario/roles')),
    auth.modulos.has('pedidos') ? quiet(() => postData('/zona/list')) : [],
    auth.modulos.has('pedidos') ? quiet(() => postData('/punto_produccion/list')) : [],
  ])
  usuarios.value = u || []
  roles.value = r || []
  zonas.value = (z || []).filter((zona) => !zona.es_mostrador)
  puntos.value = p || []
}

function nuevo() {
  form.value = { usuario: '', nombre: '', documento: '', correo: '', password: '', roles: ['mesero'], zonas: [], puntos: [] }
}

function editar(usuario) {
  form.value = { ...usuario, usuario_id: usuario.id, password: '' }
}

async function guardar() {
  const editando = !!form.value.usuario_id
  const body = { ...form.value, password: form.value.password || null }
  if (!pideZonas.value) body.zonas = []
  if (!pidePuntos.value) body.puntos = []
  const ok = await attempt(() => postData(editando ? '/usuario/update' : '/usuario/create', body),
    { success: editando ? 'Usuario actualizado.' : 'Usuario creado.' })
  if (ok) {
    form.value = null
    load()
  }
}

async function guardarPin(quitar = false) {
  const ok = await attempt(() => postData('/usuario/pin', { usuario_id: pinForm.value.id, pin: quitar ? null : pinForm.value.pin }),
    { success: quitar ? 'PIN quitado.' : 'PIN asignado. Ya puede entrar en las tablets autorizadas.' })
  if (ok) {
    pinForm.value = null
    load()
  }
}

async function cambiarEstado(usuario) {
  await attempt(() => postData('/usuario/change_status', { usuario_id: usuario.id, activo: !usuario.activo }),
    { success: usuario.activo ? 'Usuario desactivado. Su sesión se cerró.' : 'Usuario activado.' })
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Personal</h1>
        <p>Cada persona entra con su propio usuario: así cada orden queda a nombre de quien la tomó.</p>
      </div>
      <button class="btn" type="button" @click="nuevo">Crear usuario</button>
    </header>

    <div class="panel table-wrap">
      <table class="table">
        <thead><tr><th>Nombre</th><th>Usuario</th><th>Roles</th><th>Atiende</th><th>Último ingreso</th><th></th></tr></thead>
        <tbody>
          <tr v-for="usuario in usuarios" :key="usuario.id" :class="{ muted: !usuario.activo }">
            <td><strong>{{ usuario.nombre }}</strong><span v-if="!usuario.activo"> (inactivo)</span></td>
            <td>{{ usuario.usuario }}</td>
            <td>{{ usuario.roles.map((r) => ROLES[r] || r).join(', ') }}</td>
            <td>{{ [...usuario.zonas.map(nombreZona), ...usuario.puntos.map(nombrePunto)].filter(Boolean).join(', ') || 'Todo el restaurante' }}</td>
            <td>{{ usuario.ultimo_acceso ? formatDateTime(usuario.ultimo_acceso) : 'Nunca' }}</td>
            <td class="actions">
              <button class="btn btn-secundario btn-sm" type="button" @click="editar(usuario)">Editar</button>
              <button class="btn btn-secundario btn-sm" type="button" @click="pinForm = { id: usuario.id, nombre: usuario.nombre, pin: '', tiene: usuario.tiene_pin }">
                {{ usuario.tiene_pin ? 'Cambiar PIN' : 'Asignar PIN' }}
              </button>
              <button v-if="usuario.id !== auth.user?.id" class="btn btn-secundario btn-sm" type="button" :disabled="busy"
                      @click="cambiarEstado(usuario)">{{ usuario.activo ? 'Desactivar' : 'Activar' }}</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <AppModal :open="!!pinForm" :title="`PIN de ${pinForm?.nombre}`" width="24rem" @close="pinForm = null">
      <form v-if="pinForm" @submit.prevent="guardarPin(false)">
        <div class="field">
          <label for="u-pin">PIN de 4 a 6 números</label>
          <input id="u-pin" v-model="pinForm.pin" class="input" inputmode="numeric" pattern="[0-9]{4,6}" maxlength="6" required autocomplete="off">
          <span class="hint">Sirve solo en tablets y pantallas autorizadas del restaurante.</span>
        </div>
        <div class="form-actions">
          <button v-if="pinForm.tiene" class="btn btn-secundario" type="button" :disabled="busy" @click="guardarPin(true)">Quitar PIN</button>
          <button class="btn" type="submit" :disabled="busy">Guardar</button>
        </div>
      </form>
    </AppModal>

    <AppModal :open="!!form" :title="form?.usuario_id ? `Editar ${form.nombre}` : 'Crear usuario'" width="40rem" @close="form = null">
      <form v-if="form" @submit.prevent="guardar">
        <div class="form-grid">
          <div class="field">
            <label for="u-nombre">Nombre</label>
            <input id="u-nombre" v-model="form.nombre" class="input" required maxlength="150">
          </div>
          <div class="field">
            <label for="u-usuario">Usuario para ingresar</label>
            <input id="u-usuario" v-model="form.usuario" class="input" required maxlength="60" autocapitalize="none"
                   :disabled="!!form.usuario_id" placeholder="carlos.mesero">
          </div>
          <div class="field">
            <label for="u-clave">{{ form.usuario_id ? 'Nueva clave' : 'Clave' }}</label>
            <input id="u-clave" v-model="form.password" class="input" type="password" minlength="8" autocomplete="new-password"
                   :required="!form.usuario_id" :placeholder="form.usuario_id ? 'Déjala vacía para no cambiarla' : 'Mínimo 8 caracteres'">
          </div>
          <div class="field">
            <label for="u-correo">Correo</label>
            <input id="u-correo" v-model="form.correo" class="input" type="email" maxlength="150" placeholder="Opcional">
          </div>
        </div>

        <fieldset class="grupo">
          <legend>Roles</legend>
          <label v-for="rol in roles" :key="rol.codigo" class="check">
            <input v-model="form.roles" type="checkbox" :value="rol.codigo" :disabled="form.usuario_id === auth.user?.id">
            {{ rol.nombre }}
          </label>
          <p v-if="form.usuario_id === auth.user?.id" class="hint">Tus propios roles los cambia otro administrador.</p>
        </fieldset>

        <fieldset v-if="pideZonas" class="grupo">
          <legend>Zonas que atiende como mesero</legend>
          <label v-for="zona in zonas" :key="zona.id" class="check">
            <input v-model="form.zonas" type="checkbox" :value="zona.id"> {{ zona.nombre }}
          </label>
        </fieldset>

        <fieldset v-if="pidePuntos" class="grupo">
          <legend>Puntos de producción</legend>
          <label v-for="punto in puntos" :key="punto.id" class="check">
            <input v-model="form.puntos" type="checkbox" :value="punto.id"> {{ punto.nombre }}
          </label>
        </fieldset>

        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="form = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy || !form.roles.length" :aria-busy="busy">Guardar</button>
        </div>
      </form>
    </AppModal>
  </div>
</template>

<style scoped>
.grupo {
  margin: var(--space-4) 0 0;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
}

.grupo legend {
  font-weight: 600;
  font-size: var(--text-sm);
}

.hint {
  color: var(--acero);
  font-size: var(--text-sm);
}
</style>
