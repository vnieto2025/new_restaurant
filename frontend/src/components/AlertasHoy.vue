<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import AppModal from '@/components/AppModal.vue'

/*
  Alertas del dueño en Hoy (doc 27): lo que necesita atención ahora. Cada una se puede silenciar por
  el resto de la jornada o apagar y ajustar su umbral (RN-DAS-03). Se revisan cada minuto, porque
  varias dependen del tiempo (comandas demoradas, mesas abiertas).
*/
const auth = useAuthStore()
const router = useRouter()
const { busy, attempt } = useAction()

const alertas = ref([])
const verSilenciadas = ref(false)
const config = ref(null)

const configura = computed(() => auth.can('restaurante.configurar') && (!auth.acceso || auth.acceso.modo === 'completo'))
const activas = computed(() => alertas.value.filter((a) => !a.silenciada))
const silenciadas = computed(() => alertas.value.filter((a) => a.silenciada))

async function load() {
  if (!auth.can('reportes.ver')) return
  alertas.value = await postData('/alerta/list').catch(() => alertas.value)
}

// Solo se enlaza a pantallas que el usuario puede abrir
function enlace(alerta) {
  const ruta = router.getRoutes().find((r) => r.name === alerta.enlace)
  const permiso = ruta?.meta?.permiso
  return ruta && (!permiso || auth.can(permiso)) && alerta.enlace !== 'admin' ? { name: alerta.enlace } : null
}

async function silenciar(alerta, silenciar = true) {
  const ok = await attempt(() => postData('/alerta/silenciar', { codigo: alerta.codigo, silenciar }),
    { success: silenciar ? `«${alerta.nombre}» silenciada hasta mañana.` : `«${alerta.nombre}» activa de nuevo.` })
  if (ok !== undefined) await load()
}

async function abrirConfig() {
  const filas = await attempt(() => postData('/alerta/config/get'))
  if (filas) config.value = filas.map((f) => ({ ...f }))
}

async function guardarConfig() {
  const filas = await attempt(() => postData('/alerta/config/save', {
    alertas: config.value.map(({ codigo, activa, umbral }) => ({ codigo, activa, umbral })),
  }), { success: 'Alertas guardadas.' })
  if (filas) {
    config.value = null
    await load()
  }
}

let reloj = null
// La primera carga la hace la pantalla que lo contiene, con el resto de sus datos
onMounted(() => {
  reloj = setInterval(load, 60000)
})
onBeforeUnmount(() => clearInterval(reloj))
defineExpose({ load })
</script>

<template>
  <section v-if="auth.can('reportes.ver')" class="alertas" aria-labelledby="alertas-titulo">
    <div class="cabeza">
      <h2 id="alertas-titulo">Alertas</h2>
      <button v-escribe v-if="configura" class="enlace" type="button" @click="abrirConfig">Configurar alertas</button>
    </div>

    <p v-if="!activas.length" class="calma">Nada que atender por ahora.</p>
    <ul v-else class="lista">
      <li v-for="alerta in activas" :key="alerta.codigo" :class="['alerta', alerta.nivel]">
        <div class="texto">
          <strong>{{ alerta.titulo }}</strong>
          <span class="nombre">{{ alerta.nombre }}</span>
          <ul class="detalle">
            <li v-for="linea in alerta.detalle" :key="linea">{{ linea }}</li>
            <li v-if="alerta.cantidad > alerta.detalle.length && alerta.codigo !== 'comandas_demoradas'">y {{ alerta.cantidad - alerta.detalle.length }} más</li>
          </ul>
        </div>
        <div class="acciones">
          <RouterLink v-if="enlace(alerta)" :to="enlace(alerta)" class="btn btn-secundario btn-sm">Revisar</RouterLink>
          <button v-escribe v-if="configura" class="btn btn-secundario btn-sm" type="button" :disabled="busy"
                  :aria-label="`Silenciar hoy ${alerta.nombre}`" @click="silenciar(alerta)">Silenciar hoy</button>
        </div>
      </li>
    </ul>

    <div v-if="silenciadas.length" class="silenciadas">
      <button class="enlace" type="button" :aria-expanded="verSilenciadas" @click="verSilenciadas = !verSilenciadas">
        {{ silenciadas.length === 1 ? '1 alerta silenciada' : `${silenciadas.length} alertas silenciadas` }} hoy
      </button>
      <ul v-if="verSilenciadas" class="lista">
        <li v-for="alerta in silenciadas" :key="alerta.codigo" class="alerta silenciada">
          <div class="texto">
            <strong>{{ alerta.titulo }}</strong>
            <span class="nombre">{{ alerta.nombre }}</span>
          </div>
          <button v-escribe v-if="configura" class="btn btn-secundario btn-sm" type="button" :disabled="busy"
                  :aria-label="`Volver a mostrar ${alerta.nombre}`" @click="silenciar(alerta, false)">Volver a mostrar</button>
        </li>
      </ul>
    </div>

    <AppModal :open="!!config" title="Configurar alertas" width="40rem" @close="config = null">
      <form v-escribe v-if="config" @submit.prevent="guardarConfig">
        <p class="muted">Cada alerta aparece en Hoy cuando pasa su umbral. Apaga las que no te sirvan.</p>
        <div v-for="fila in config" :key="fila.codigo" class="config-fila">
          <label class="check"><input v-model="fila.activa" type="checkbox"> {{ fila.nombre }}</label>
          <div v-if="fila.umbral_sugerido !== null" class="umbral">
            <input v-model.number="fila.umbral" class="input" type="number" min="1" :disabled="!fila.activa"
                   :aria-label="`Umbral de ${fila.nombre} en ${fila.unidad}`">
            <span class="muted">{{ fila.unidad }}<template v-if="fila.ayuda"> · {{ fila.ayuda }}</template></span>
          </div>
        </div>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="config = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy" :aria-busy="busy">Guardar</button>
        </div>
      </form>
    </AppModal>
  </section>
</template>

<style scoped>
.alertas {
  padding: var(--space-4);
  background: var(--superficie);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
}

.cabeza {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-2);
}

h2 {
  font-size: var(--text-lg);
}

.calma {
  margin-top: var(--space-2);
  color: var(--acero);
}

.lista {
  margin: var(--space-3) 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.alerta {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-2) var(--space-4);
  padding: var(--space-3);
  border: 1px solid var(--linea);
  border-left: 6px solid var(--estado-pendiente);
  border-radius: var(--radio-sm);
}

/* Las alertas no usan los colores de estado de las órdenes (RN-EST-06): urgente es tinta, aviso es gris */
.alerta.urgente {
  border-left-color: var(--tinta);
  border-left-style: double;
  border-left-width: 8px;
}

.alerta.silenciada {
  opacity: 0.75;
}

.texto {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.nombre,
.detalle {
  color: var(--acero);
  font-size: var(--text-sm);
}

.detalle {
  margin: var(--space-1) 0 0;
  padding-left: var(--space-4);
}

.acciones {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.silenciadas {
  margin-top: var(--space-3);
}

.enlace {
  border: 0;
  background: none;
  padding: 0;
  color: var(--accion);
  font: inherit;
  font-weight: 600;
  text-decoration: underline;
  cursor: pointer;
}

.config-fila {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3) 0;
  border-top: 1px solid var(--linea);
}

.umbral {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  padding-left: var(--space-5);
}

.umbral .input {
  width: 7rem;
}
</style>
