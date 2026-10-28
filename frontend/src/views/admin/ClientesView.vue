<script setup>
import { ref, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { formatMoney, formatDateLong, plural, CANALES } from '@/utils/format'
import AppModal from '@/components/AppModal.vue'
import ReasonDialog from '@/components/ReasonDialog.vue'

/*
  Clientes de la empresa (doc 25). Son datos personales (doc 32A): consultar una ficha queda
  registrado, y el titular puede pedir sus datos (exportar) o que se eliminen (anonimizar).
*/
const auth = useAuthStore()
const { busy, attempt, quiet } = useAction()

const clientes = ref([])
const total = ref(null)
const buscar = ref('')
const ficha = ref(null)
const form = ref(null)
const direccion = ref(null)
const anonimizar = ref(false)

async function load() {
  const data = await quiet(() => postData('/cliente/list', { buscar: buscar.value || null, limite: 100 }))
  clientes.value = data?.clientes || []
  total.value = data?.total ?? null
}

async function abrir(cliente) {
  ficha.value = await attempt(() => postData('/cliente/get', { cliente_id: cliente.id }))
}

function nuevo() {
  form.value = { nombre: '', telefono: '', correo: '', tipo_documento: '', documento: '', notas: '', acepta_datos: false, acepta_comercial: false, acepta_avisos: true }
}

function editar() {
  form.value = { ...ficha.value, cliente_id: ficha.value.id, telefono: ficha.value.telefono_legible || '' }
}

async function guardar() {
  const editando = !!form.value.cliente_id
  const data = await attempt(() => postData(editando ? '/cliente/update' : '/cliente/create', form.value),
    { success: editando ? 'Cliente actualizado.' : 'Cliente registrado.' })
  if (data) {
    form.value = null
    if (editando) abrir(data)
    load()
  }
}

async function guardarDireccion() {
  const data = await attempt(() => postData('/cliente/direccion/save', { ...direccion.value, cliente_id: ficha.value.id }),
    { success: 'Dirección guardada.' })
  if (data) {
    direccion.value = null
    ficha.value = { ...ficha.value, direcciones: data.direcciones }
  }
}

async function quitarDireccion(d) {
  const data = await attempt(() => postData('/cliente/direccion/delete', { direccion_id: d.id }), { success: 'Dirección eliminada.' })
  if (data) ficha.value = { ...ficha.value, direcciones: data.direcciones }
}

// Derecho de acceso: descarga todo lo que se guarda de la persona
async function exportar() {
  const data = await attempt(() => postData('/cliente/exportar', { cliente_id: ficha.value.id }))
  if (!data) return
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = `datos-cliente-${data.id}.json`
  enlace.click()
  URL.revokeObjectURL(url)
}

async function confirmarAnonimizar(motivo) {
  const ok = await attempt(() => postData('/cliente/anonimizar', { cliente_id: ficha.value.id, motivo }),
    { success: 'Datos personales eliminados. Las ventas se conservan.' })
  anonimizar.value = false
  if (ok) {
    ficha.value = null
    load()
  }
}

onMounted(load)
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Clientes</h1>
        <p>{{ total !== null ? `${plural(total, 'cliente registrado', 'clientes registrados')}.` : 'Resultados de la búsqueda.' }} Se registran con su autorización de datos.</p>
      </div>
      <button class="btn" type="button" @click="nuevo">Registrar cliente</button>
    </header>

    <form class="buscar" @submit.prevent="load">
      <input v-model="buscar" class="input" type="search" placeholder="Nombre, teléfono o correo" aria-label="Buscar cliente">
      <button class="btn btn-secundario" type="submit">Buscar</button>
    </form>

    <div class="panel table-wrap">
      <table class="table">
        <thead><tr><th>Cliente</th><th>Teléfono</th><th>Última compra</th><th>Comunicaciones</th><th></th></tr></thead>
        <tbody>
          <tr v-for="c in clientes" :key="c.id" :class="{ muted: c.estado !== 'activo' }">
            <td><strong>{{ c.nombre }}</strong><span v-if="c.estado === 'bloqueado'"> (bloqueado)</span></td>
            <td>{{ c.telefono_legible }}</td>
            <td>{{ c.ultima_compra ? formatDateLong(c.ultima_compra) : '—' }}</td>
            <td>{{ c.acepta_comercial ? 'Acepta promociones' : c.acepta_avisos ? 'Solo avisos de pedidos' : 'Sin avisos' }}</td>
            <td><button class="btn btn-secundario btn-sm" type="button" @click="abrir(c)">Ver ficha</button></td>
          </tr>
        </tbody>
      </table>
      <p v-if="!clientes.length" class="empty">No hay clientes que mostrar.</p>
    </div>

    <AppModal :open="!!ficha" :title="ficha?.nombre || ''" width="40rem" @close="ficha = null">
      <div v-if="ficha" class="ficha">
        <dl class="datos">
          <div><dt>Teléfono</dt><dd>{{ ficha.telefono_legible || '—' }}</dd></div>
          <div><dt>Correo</dt><dd>{{ ficha.correo || '—' }}</dd></div>
          <div><dt>Documento</dt><dd>{{ ficha.documento ? `${ficha.tipo_documento} ${ficha.documento}` : '—' }}</dd></div>
          <div><dt>Órdenes</dt><dd>{{ ficha.historial.ordenes }} · {{ formatMoney(ficha.historial.total_gastado) }}</dd></div>
        </dl>
        <p v-if="ficha.notas" class="notas">{{ ficha.notas }}</p>
        <p v-if="ficha.historial.favoritos.length" class="muted">
          Suele pedir: {{ ficha.historial.favoritos.map((f) => `${f.nombre} (${f.unidades})`).join(', ') }}
        </p>

        <h3>Direcciones</h3>
        <ul class="direcciones">
          <li v-for="d in ficha.direcciones" :key="d.id">
            <span><strong>{{ d.nombre || 'Dirección' }}:</strong> {{ d.direccion }}<template v-if="d.barrio">, {{ d.barrio }}</template>
              <small v-if="d.indicaciones" class="muted"> · {{ d.indicaciones }}</small></span>
            <span class="actions">
              <button class="btn btn-secundario btn-sm" type="button" @click="direccion = { ...d, direccion_id: d.id }">Editar</button>
              <button class="btn btn-secundario btn-sm" type="button" :disabled="busy" @click="quitarDireccion(d)">Quitar</button>
            </span>
          </li>
        </ul>
        <button class="btn btn-secundario btn-sm" type="button" @click="direccion = { nombre: '', direccion: '', barrio: '', indicaciones: '' }">Agregar dirección</button>

        <h3>Últimas órdenes</h3>
        <p v-if="!ficha.historial.ultimas.length" class="muted">Aún no tiene órdenes.</p>
        <p v-for="o in ficha.historial.ultimas" :key="o.numero_texto + o.jornada" class="orden">
          {{ formatDateLong(o.jornada) }} · {{ o.numero_texto }} · {{ CANALES[o.canal] || o.canal }} · {{ formatMoney(o.total) }}
        </p>

        <template v-if="ficha.cupones">
          <!-- Cupones del cliente (doc 25, sección 4; doc 25A) -->
          <h3>Cupones</h3>
          <p v-for="c in ficha.cupones.personales.filter((x) => ['activo', 'programado'].includes(x.estado_actual))" :key="c.id" class="orden">
            <strong>{{ c.codigo }}</strong> · {{ c.beneficio }}<template v-if="c.termina"> · hasta {{ formatDateLong(c.termina) }}</template>
          </p>
          <p v-for="u in ficha.cupones.usados" :key="u.codigo + u.fecha" class="orden muted">
            Usó {{ u.codigo }} · −{{ formatMoney(u.valor) }}
          </p>
          <p v-if="!ficha.cupones.usados.length && !ficha.cupones.personales.length" class="muted">No tiene cupones.</p>
          <RouterLink v-if="auth.can('cupones.gestionar')" class="btn btn-secundario btn-sm crear-cupon"
                      :to="{ name: 'admin-cupones', query: { cliente: ficha.id, nombre: ficha.nombre } }">Crear cupón personal</RouterLink>
        </template>

        <div class="form-actions">
          <button v-if="auth.can('clientes.gestionar')" class="btn btn-secundario" type="button" @click="anonimizar = true">Eliminar sus datos</button>
          <button v-if="auth.can('clientes.exportar')" class="btn btn-secundario" type="button" :disabled="busy" @click="exportar">Exportar sus datos</button>
          <button v-if="auth.can('clientes.gestionar')" class="btn" type="button" @click="editar">Editar</button>
        </div>
      </div>
    </AppModal>

    <AppModal :open="!!form" :title="form?.cliente_id ? `Editar ${form.nombre}` : 'Registrar cliente'" width="34rem" @close="form = null">
      <form v-if="form" @submit.prevent="guardar">
        <div class="form-grid">
          <div class="field"><label for="c-nombre">Nombre</label><input id="c-nombre" v-model="form.nombre" class="input" required maxlength="120"></div>
          <div class="field"><label for="c-tel">Celular</label><input id="c-tel" v-model="form.telefono" class="input" type="tel" inputmode="tel" required></div>
          <div class="field"><label for="c-correo">Correo</label><input id="c-correo" v-model="form.correo" class="input" type="email"></div>
          <div class="field">
            <label for="c-tipo">Documento (para factura)</label>
            <div class="doc">
              <select id="c-tipo" v-model="form.tipo_documento" class="select" aria-label="Tipo de documento">
                <option value="">Tipo</option>
                <option v-for="t in ['CC', 'CE', 'NIT', 'PAS', 'PPT']" :key="t" :value="t">{{ t }}</option>
              </select>
              <input v-model="form.documento" class="input" aria-label="Número de documento" maxlength="30">
            </div>
          </div>
        </div>
        <div class="field espacio"><label for="c-notas">Notas (preferencias, alergias que informó)</label>
          <input id="c-notas" v-model="form.notas" class="input" maxlength="500"></div>
        <label v-if="!form.cliente_id" class="check"><input v-model="form.acepta_datos" type="checkbox"> Le informé el aviso de tratamiento de datos y lo aceptó</label>
        <label class="check"><input v-model="form.acepta_comercial" type="checkbox"> Acepta recibir promociones y cupones</label>
        <label class="check"><input v-model="form.acepta_avisos" type="checkbox"> Recibe avisos de sus pedidos por WhatsApp (lista, en camino)</label>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="form = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy || (!form.cliente_id && !form.acepta_datos)">Guardar</button>
        </div>
      </form>
    </AppModal>

    <AppModal :open="!!direccion" title="Dirección" width="30rem" @close="direccion = null">
      <form v-if="direccion" @submit.prevent="guardarDireccion">
        <div class="form-grid">
          <div class="field"><label for="d-nom">Nombre</label><input id="d-nom" v-model="direccion.nombre" class="input" placeholder="Casa, Trabajo" maxlength="40"></div>
          <div class="field"><label for="d-barrio">Barrio</label><input id="d-barrio" v-model="direccion.barrio" class="input" maxlength="80"></div>
        </div>
        <div class="field espacio"><label for="d-dir">Dirección</label><input id="d-dir" v-model="direccion.direccion" class="input" required maxlength="200"></div>
        <div class="field espacio"><label for="d-ind">Indicaciones</label><input id="d-ind" v-model="direccion.indicaciones" class="input" maxlength="250" placeholder="Torre 2, apto 301"></div>
        <div class="form-actions"><button class="btn" type="submit" :disabled="busy">Guardar</button></div>
      </form>
    </AppModal>

    <ReasonDialog :open="anonimizar" :busy="busy" title="Eliminar los datos personales"
                  description="Se borran nombre, teléfono, correo, documento y direcciones. Las ventas se conservan sin ellos. No se puede deshacer."
                  :options="['Solicitud de supresión del titular']" confirm-label="Eliminar datos"
                  @close="anonimizar = false" @confirm="confirmarAnonimizar" />
  </div>
</template>

<style scoped>
.buscar {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.ficha {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.ficha h3 {
  margin-top: var(--space-3);
  font-size: var(--text-base);
}

.datos {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: var(--space-3);
  margin: 0;
}

.datos dt {
  color: var(--acero);
  font-size: var(--text-sm);
}

.datos dd {
  margin: 0;
  font-weight: 600;
}

.notas {
  padding: var(--space-2) var(--space-3);
  background: #fff2a8;
  border-radius: var(--radio-sm);
}

.direcciones {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.direcciones li {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--space-2);
}

.orden {
  font-size: var(--text-sm);
}

.crear-cupon {
  align-self: flex-start;
  margin-top: var(--space-2);
}

.doc {
  display: grid;
  grid-template-columns: 5.5rem 1fr;
  gap: var(--space-2);
}

.espacio {
  margin-top: var(--space-3);
}
</style>
