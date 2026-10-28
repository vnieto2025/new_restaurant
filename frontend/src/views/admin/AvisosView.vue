<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'
import { formatDateTime } from '@/utils/format'
import { enlaceWhatsapp } from '@/utils/inventario'

/*
  Avisos por WhatsApp a los clientes (doc 31B): qué se avisa, con qué texto y cómo sale.
  - Manual: el encargado toca "Enviar por WhatsApp" y se abre con el mensaje escrito. Sin costo ni riesgo.
  - Automático: lo envía un proveedor de la API oficial; tiene costo por mensaje y plantillas aprobadas.
  Nunca herramientas no oficiales: arriesgan el número del restaurante.
*/
const { busy, attempt, quiet } = useAction()

const config = ref(null)
const form = ref(null)
const historial = ref([])
const filtro = ref('')
const prueba = ref({ telefono: '', resultado: null })
const vista = ref('config')

const ESTADOS = { pendiente: 'En cola', manual: 'Por enviar', enviada: 'Enviada', fallida: 'No se pudo enviar', omitida: 'No se envió', descartada: 'Descartada' }

const variables = computed(() => (config.value?.variables || []).map((v) => `{${v}}`).join(', '))

async function load() {
  const data = await quiet(() => postData('/notificacion/config/get'))
  if (!data) return
  config.value = data
  form.value = {
    modo: data.modo, proveedor: data.proveedor, numero_remitente: data.numero_remitente || '', limite_diario: data.limite_diario,
    credenciales: { modo: '' },
    eventos: Object.fromEntries(data.eventos.map((e) => [e.codigo, e.activo])),
    plantillas: Object.fromEntries(data.eventos.map((e) => [e.codigo, e.plantilla])),
  }
}

async function loadHistorial() {
  historial.value = (await quiet(() => postData('/notificacion/list', filtro.value ? { estado: filtro.value } : {}))) || []
}

// Vista previa con datos de ejemplo, igual que la arma el servidor
function vistaPrevia(texto) {
  const ejemplo = { nombre: 'Ana', numero: '#012', restaurante: config.value?.restaurante || '', direccion: 'Calle 10 # 5-20' }
  return (texto || '').replace(/\{(\w+)\}/g, (todo, v) => (v in ejemplo ? ejemplo[v] : todo))
}

async function guardar() {
  const f = form.value
  const credenciales = f.credenciales.modo ? { modo: f.credenciales.modo } : null
  const data = await attempt(() => postData('/notificacion/config/save', {
    modo: f.modo, proveedor: f.proveedor, numero_remitente: f.numero_remitente.trim() || null,
    limite_diario: Number(f.limite_diario) || 5, eventos: f.eventos, plantillas: f.plantillas, credenciales,
  }), { success: 'Avisos guardados.' })
  if (data) load()
}

async function probar() {
  const data = await attempt(() => postData('/notificacion/prueba', { telefono: prueba.value.telefono }))
  prueba.value.resultado = data || null
}

async function reintentar(aviso) {
  await attempt(() => postData('/notificacion/reintentar', { notificacion_id: aviso.id }), { success: 'Aviso de nuevo en la cola.' })
  loadHistorial()
}

onMounted(() => {
  load()
  loadHistorial()
})
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Avisos por WhatsApp</h1>
        <p>Avisos a los clientes sobre sus propios pedidos: cuando está listo, cuando sale el domicilio.</p>
      </div>
    </header>

    <div class="vistas" role="tablist">
      <button role="tab" type="button" :aria-selected="vista === 'config'" @click="vista = 'config'">Configuración</button>
      <button role="tab" type="button" :aria-selected="vista === 'historial'" @click="vista = 'historial'; loadHistorial()">Historial</button>
    </div>

    <form v-if="vista === 'config' && form" class="config" @submit.prevent="guardar">
      <fieldset class="panel bloque">
        <legend>¿Cómo se envían?</legend>
        <label class="opcion-modo" :class="{ elegida: form.modo === 'manual' }">
          <input v-model="form.modo" type="radio" value="manual">
          <span><strong>Manual, con un toque</strong>
            <small>En mostrador y domicilios aparece «Enviar por WhatsApp» con el mensaje ya escrito. Lo envía el encargado desde el WhatsApp del restaurante. Sin costo.</small></span>
        </label>
        <label class="opcion-modo" :class="{ elegida: form.modo === 'automatico' }">
          <input v-model="form.modo" type="radio" value="automatico">
          <span><strong>Automático</strong>
            <small>Los envía un proveedor de la API oficial de WhatsApp. Tiene costo por mensaje y los textos deben estar aprobados por Meta. Si un envío falla, aparece para enviarlo a mano.</small></span>
        </label>
        <div v-if="form.modo === 'automatico'" class="form-grid espacio">
          <div class="field"><label for="av-prov">Proveedor</label>
            <select id="av-prov" v-model="form.proveedor" class="select">
              <option v-for="p in config.proveedores" :key="p" :value="p">{{ p === 'simulado' ? 'Simulado (pruebas)' : p }}</option>
            </select></div>
          <div v-if="form.proveedor === 'simulado'" class="field"><label for="av-cred">Respuesta del simulador</label>
            <select id="av-cred" v-model="form.credenciales.modo" class="select">
              <option value="">{{ config.tiene_credenciales ? 'Mantener la guardada' : 'Elige una' }}</option>
              <option value="aceptar">Envía todo</option>
              <option value="rechazar">Rechaza todo</option>
              <option value="caido">No responde</option>
            </select></div>
          <div class="field"><label for="av-num">Número del restaurante</label>
            <input id="av-num" v-model="form.numero_remitente" class="input" maxlength="20" inputmode="tel" placeholder="WhatsApp Business"></div>
        </div>
        <p v-if="form.modo === 'automatico'" class="muted">Credenciales {{ config.tiene_credenciales ? 'guardadas: no se muestran' : 'sin configurar' }}.</p>
      </fieldset>

      <fieldset class="panel bloque">
        <legend>Qué se avisa</legend>
        <p class="muted">Puedes usar {{ variables }}. El cliente puede pedir no recibir avisos desde su ficha.</p>
        <div v-for="e in config.eventos" :key="e.codigo" class="evento">
          <label class="check"><input v-model="form.eventos[e.codigo]" type="checkbox"> <strong>{{ e.nombre }}</strong></label>
          <template v-if="form.eventos[e.codigo]">
            <label class="visually-hidden" :for="`pl-${e.codigo}`">Texto de {{ e.nombre }}</label>
            <textarea :id="`pl-${e.codigo}`" v-model="form.plantillas[e.codigo]" class="input" rows="2" maxlength="500"></textarea>
            <div class="pie-evento">
              <small class="muted">Así llega: «{{ vistaPrevia(form.plantillas[e.codigo]) }}»</small>
              <button v-if="form.plantillas[e.codigo] !== e.plantilla_defecto" class="enlace" type="button"
                      @click="form.plantillas[e.codigo] = e.plantilla_defecto">Restaurar texto</button>
            </div>
          </template>
        </div>
        <div class="field limite">
          <label for="av-lim">Máximo de avisos por teléfono al día</label>
          <input id="av-lim" v-model.number="form.limite_diario" class="input" type="number" min="1" max="50">
        </div>
      </fieldset>

      <div class="form-actions">
        <button class="btn" type="submit" :disabled="busy">Guardar</button>
      </div>

      <fieldset class="panel bloque">
        <legend>Probar</legend>
        <div class="probar">
          <label class="visually-hidden" for="av-prueba">Celular para la prueba</label>
          <input id="av-prueba" v-model="prueba.telefono" class="input" inputmode="tel" placeholder="Celular para la prueba">
          <button class="btn btn-secundario" type="button" :disabled="busy || prueba.telefono.length < 7" @click="probar">Enviar prueba</button>
        </div>
        <p v-if="prueba.resultado?.modo === 'manual'">
          <a :href="enlaceWhatsapp(prueba.resultado.telefono, prueba.resultado.mensaje)" target="_blank" rel="noopener">Abrir WhatsApp con el mensaje de prueba</a>
        </p>
        <p v-else-if="prueba.resultado" class="muted">Enviado por el proveedor ({{ prueba.resultado.referencia }}).</p>
      </fieldset>
    </form>

    <section v-else-if="vista === 'historial'">
      <div class="filtros">
        <select v-model="filtro" class="select" aria-label="Estado" @change="loadHistorial">
          <option value="">Todos los estados</option>
          <option v-for="(label, valor) in ESTADOS" :key="valor" :value="valor">{{ label }}</option>
        </select>
      </div>
      <div class="panel table-wrap">
        <table class="table">
          <thead><tr><th>Fecha</th><th>Orden</th><th>Aviso</th><th>Para</th><th>Estado</th><th></th></tr></thead>
          <tbody>
            <tr v-for="a in historial" :key="a.id">
              <td class="nowrap">{{ formatDateTime(a.hora_local || a.creado_en) }}</td>
              <td>{{ a.orden || '—' }}</td>
              <td>{{ a.evento_texto }}<small class="muted bloque-texto">{{ a.mensaje }}</small></td>
              <td>{{ a.nombre || '—' }}<small class="muted bloque-texto">{{ a.telefono_legible || 'Sin teléfono' }}</small></td>
              <td>{{ a.estado_texto }}<small v-if="a.error" class="muted bloque-texto">{{ a.error }}</small>
                <small v-else-if="a.enviada_por" class="muted bloque-texto">por {{ a.enviada_por }}</small></td>
              <td><button v-if="a.estado === 'fallida' && config?.modo === 'automatico'" class="btn btn-secundario btn-sm" type="button"
                          @click="reintentar(a)">Reintentar</button></td>
            </tr>
          </tbody>
        </table>
        <p v-if="!historial.length" class="empty">Aún no hay avisos con ese filtro.</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.vistas {
  display: flex;
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

.bloque {
  margin: 0 0 var(--space-4);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.bloque legend {
  padding: 0 var(--space-1);
  font-weight: 700;
}

.opcion-modo {
  display: flex;
  gap: var(--space-3);
  align-items: flex-start;
  padding: var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio-sm);
  cursor: pointer;
}

.opcion-modo.elegida {
  border-color: var(--accion);
  background: var(--accion-suave);
}

.opcion-modo input {
  margin-top: 0.3em;
}

.opcion-modo span {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.opcion-modo small {
  color: var(--acero);
}

.evento {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--linea);
}

.pie-evento {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--space-2);
}

.enlace {
  border: none;
  background: none;
  color: var(--accion);
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
}

.limite {
  max-width: 20rem;
}

.probar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.probar .input {
  flex: 1 1 12rem;
  max-width: 18rem;
}

.espacio {
  margin-top: var(--space-2);
}

.filtros {
  margin-bottom: var(--space-4);
}

.filtros .select {
  width: auto;
  min-width: 12rem;
}

.nowrap {
  white-space: nowrap;
}

.bloque-texto {
  display: block;
}
</style>
