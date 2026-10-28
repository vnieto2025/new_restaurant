<script setup>
import { ref, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import AppModal from '@/components/AppModal.vue'
import HorarioEditor from '@/components/HorarioEditor.vue'

const auth = useAuthStore()
const { busy, attempt, quiet } = useAction()

const restaurante = ref(null)
const form = ref(null)
const medios = ref([])
const medioForm = ref(null)

const TIPOS_MEDIO = { efectivo: 'Efectivo', tarjeta: 'Tarjeta', transferencia: 'Transferencia', otro: 'Otro' }

const TIPOS = {
  restaurante: 'Restaurante', comida_rapida: 'Comida rápida', bar: 'Bar', panaderia: 'Panadería',
  cocina_oculta: 'Cocina oculta', otro: 'Otro',
}
const ESTADOS = { activo: 'Recibiendo pedidos', pausado: 'En pausa', cerrado: 'Cerrado temporalmente' }
const MODULOS = { base: 'Base', pedidos: 'Pedidos', caja: 'Caja', inventario: 'Inventario', propinas: 'Propinas', domicilios: 'Domicilios' }

async function load() {
  restaurante.value = await quiet(() => postData('/restaurante/get'))
  if (restaurante.value) form.value = { ...restaurante.value }
  if (auth.modulos.has('caja') && auth.can('caja.medios')) {
    medios.value = (await quiet(() => postData('/caja/medio_pago/list', { todos: true }))) || []
  }
}

async function guardar() {
  const data = await attempt(() => postData('/restaurante/update', form.value), { success: 'Configuración guardada.' })
  if (data) {
    restaurante.value = data
    auth.refresh()
  }
}

async function guardarMedio() {
  const ok = await attempt(() => postData('/caja/medio_pago/save', medioForm.value), { success: 'Medio de pago guardado.' })
  if (ok) {
    medioForm.value = null
    load()
  }
}

async function cambiarEstado(estado) {
  const data = await attempt(() => postData('/restaurante/change_status', { estado, mensaje_carta: form.value.mensaje_carta }),
    { success: ESTADOS[estado] })
  if (data) restaurante.value = data
}

onMounted(load)
</script>

<template>
  <div v-if="restaurante">
    <header class="page-head">
      <div>
        <h1>Configuración</h1>
        <p>Estado actual: <strong>{{ ESTADOS[restaurante.estado] || restaurante.estado }}</strong></p>
      </div>
      <div v-if="auth.can('restaurante.pausar')" class="actions">
        <button v-for="(label, estado) in ESTADOS" :key="estado" class="btn btn-secundario" type="button"
                :aria-pressed="restaurante.estado === estado" :disabled="busy || restaurante.estado === estado"
                @click="cambiarEstado(estado)">{{ label }}</button>
      </div>
    </header>

    <form v-if="auth.can('restaurante.configurar')" class="panel bloque" @submit.prevent="guardar">
      <div class="form-grid">
        <div class="field">
          <label for="r-nombre">Nombre</label>
          <input id="r-nombre" v-model="form.nombre" class="input" required maxlength="150">
        </div>
        <div class="field">
          <label for="r-tipo">Tipo de negocio</label>
          <select id="r-tipo" v-model="form.tipo" class="select">
            <option v-for="(label, value) in TIPOS" :key="value" :value="value">{{ label }}</option>
          </select>
        </div>
        <div class="field">
          <label for="r-dir">Dirección</label>
          <input id="r-dir" v-model="form.direccion" class="input" maxlength="200">
        </div>
        <div class="field">
          <label for="r-tel">Teléfono</label>
          <input id="r-tel" v-model="form.telefono" class="input" type="tel" maxlength="30">
        </div>
        <div class="field">
          <label for="r-jornada">La jornada empieza a las</label>
          <input id="r-jornada" v-model="form.hora_inicio_jornada" class="input" type="time" required>
          <span class="hint">Las órdenes de la madrugada cuentan para el día anterior. Solo se cambia sin mesas abiertas.</span>
        </div>
        <div class="field">
          <label for="r-tz">Zona horaria</label>
          <input id="r-tz" v-model="form.zona_horaria" class="input" maxlength="50">
        </div>
        <div v-if="auth.modulos.has('caja')" class="field">
          <label for="r-propina">Propina sugerida al cobrar (%)</label>
          <input id="r-propina" v-model.number="form.propina_sugerida" class="input" type="number" min="0" max="30">
          <span class="hint">Pon 0 para no sugerir propina. Siempre es voluntaria para el cliente.</span>
        </div>
      </div>
      <label class="check"><input v-model="form.reiniciar_agotados" type="checkbox"> Al cerrar la jornada, los productos agotados vuelven a estar disponibles</label>
      <div class="field mensaje">
        <label for="r-aviso">Aviso de tratamiento de datos (lo ve el cliente antes de dejar su celular)</label>
        <textarea id="r-aviso" v-model="form.aviso_datos" class="textarea" maxlength="600"
                  placeholder="Si lo dejas vacío se usa un aviso básico. Pídele a tu abogado el texto definitivo."></textarea>
        <span class="hint">Versión actual: {{ restaurante.aviso_version }}. Cada cambio crea una versión nueva y cada cliente guarda la que aceptó.</span>
      </div>
      <div class="field mensaje">
        <label for="r-politica">Enlace a la política de datos</label>
        <input id="r-politica" v-model="form.politica_url" class="input" type="url" maxlength="250" placeholder="https://…">
      </div>
      <div class="field mensaje">
        <label for="r-msg">Mensaje para los clientes cuando estés en pausa o cerrado</label>
        <input id="r-msg" v-model="form.mensaje_carta" class="input" maxlength="250"
               placeholder="Estamos llenos, vuelve a intentarlo en 15 minutos">
      </div>
      <div class="form-actions">
        <button class="btn" type="submit" :disabled="busy" :aria-busy="busy">Guardar</button>
      </div>
    </form>

    <section v-if="auth.can('restaurante.configurar')" class="panel bloque">
      <h2>Horario de atención</h2>
      <p class="muted espacio">Fuera de este horario no se reciben órdenes por ningún canal y la carta muestra cuándo abren.</p>
      <HorarioEditor tipo="atencion" />
    </section>

    <section v-if="medios.length" class="panel bloque">
      <div class="page-head">
        <h2>Medios de pago</h2>
        <button class="btn btn-secundario" type="button" @click="medioForm = { nombre: '', tipo: 'otro', pide_referencia: false, activo: true }">Agregar medio</button>
      </div>
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>Medio</th><th>Tipo</th><th>Pide referencia</th><th></th></tr></thead>
          <tbody>
            <tr v-for="medio in medios" :key="medio.id" :class="{ muted: !medio.activo }">
              <td><strong>{{ medio.nombre }}</strong><span v-if="!medio.activo"> (inactivo)</span></td>
              <td>{{ TIPOS_MEDIO[medio.tipo] }}</td>
              <td>{{ medio.pide_referencia ? 'Sí' : 'No' }}</td>
              <td class="actions">
                <button class="btn btn-secundario btn-sm" type="button" @click="medioForm = { ...medio, medio_pago_id: medio.id }">Editar</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <AppModal :open="!!medioForm" :title="medioForm?.medio_pago_id ? `Editar ${medioForm.nombre}` : 'Agregar medio de pago'" width="28rem"
              @close="medioForm = null">
      <form v-if="medioForm" @submit.prevent="guardarMedio">
        <div class="form-grid">
          <div class="field">
            <label for="mp-nombre">Nombre</label>
            <input id="mp-nombre" v-model="medioForm.nombre" class="input" required maxlength="40">
          </div>
          <div class="field">
            <label for="mp-tipo">Tipo</label>
            <select id="mp-tipo" v-model="medioForm.tipo" class="select" :disabled="medioForm.tipo === 'efectivo' && !!medioForm.medio_pago_id">
              <option v-for="(label, value) in TIPOS_MEDIO" :key="value" :value="value" :disabled="value === 'efectivo' && !medioForm.medio_pago_id">{{ label }}</option>
            </select>
          </div>
        </div>
        <label class="check"><input v-model="medioForm.pide_referencia" type="checkbox"> Pedir número de referencia al cobrar</label>
        <label v-if="medioForm.tipo !== 'efectivo'" class="check"><input v-model="medioForm.activo" type="checkbox"> Activo</label>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="medioForm = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy">Guardar</button>
        </div>
      </form>
    </AppModal>

    <section v-if="restaurante.contrato" class="panel bloque">
      <h2>Contrato</h2>
      <dl class="contrato">
        <div><dt>Estado</dt><dd>{{ restaurante.contrato.estado }}</dd></div>
        <div><dt>Vigente hasta</dt><dd>{{ restaurante.contrato.fecha_fin || 'Sin vencimiento' }}</dd></div>
        <div><dt>Módulos</dt><dd>{{ restaurante.contrato.modulos.map((m) => MODULOS[m] || m).join(', ') }}</dd></div>
      </dl>
    </section>
  </div>
</template>

<style scoped>
.bloque {
  padding: var(--space-5);
  margin-bottom: var(--space-5);
}

.espacio {
  margin: var(--space-2) 0 var(--space-4);
}

.mensaje {
  margin-top: var(--space-4);
}

[aria-pressed='true'] {
  background: var(--tinta);
  color: #fff;
  opacity: 1;
}

.contrato {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
  gap: var(--space-4);
  margin: var(--space-4) 0 0;
}

.contrato dt {
  color: var(--acero);
  font-size: var(--text-sm);
}

.contrato dd {
  margin: 0;
  font-weight: 600;
}
</style>
