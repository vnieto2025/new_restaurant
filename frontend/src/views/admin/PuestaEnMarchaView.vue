<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'
import { formatDateTime, plural } from '@/utils/format'
import AppModal from '@/components/AppModal.vue'
import ImportarProductos from '@/components/ImportarProductos.vue'

/*
  Asistente de configuración inicial (doc 41, sección 2). Cada paso se deduce de los datos: lo hecho en su pantalla
  cuenta aquí. Mesas y carta se pueden resolver desde esta misma pantalla. Termina con el ensayo en vacío (RN-ONB-01).
*/
const { busy, attempt, quiet } = useAction()

const estado = ref(null)
const zonas = ref([])
const importando = ref(false)
const lote = ref(null)

const siguiente = computed(() => estado.value?.pasos.find((p) => p.obligatorio && !p.hecho)?.clave)
const avance = computed(() => (estado.value?.total ? Math.round((estado.value.hechos * 100) / estado.value.total) : 0))
const faltan = computed(() => (estado.value ? estado.value.total - estado.value.hechos : 0))

async function load() {
  const data = await quiet(() => postData('/restaurante/puesta_en_marcha'))
  if (data) estado.value = data
}

async function marcar(paso, hecho) {
  const data = await attempt(() => postData('/restaurante/puesta_en_marcha/marcar', { paso: paso.clave, hecho }))
  if (data) estado.value = data
}

async function abrirMesas() {
  const data = await attempt(() => postData('/zona/list'))
  zonas.value = (data || []).filter((z) => !z.es_mostrador)
  if (zonas.value.length) lote.value = { zona_id: zonas.value[0].id, prefijo: 'Mesa', desde: 1, hasta: 10 }
}

async function crearMesas() {
  const v = lote.value
  const data = await attempt(() => postData('/mesa/create_lote', {
    zona_id: v.zona_id, prefijo: v.prefijo.trim() || 'Mesa', desde: Number(v.desde), hasta: Number(v.hasta),
  }), { success: (d) => `${plural(d.creadas, 'mesa')} en la zona.` })
  if (data) {
    lote.value = null
    load()
  }
}

onMounted(load)
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Puesta en marcha</h1>
        <p>Lo que falta para abrir. Avanza en el orden que quieras: cada paso se marca solo al hacerlo.</p>
      </div>
    </header>

    <p v-if="!estado" class="empty">Cargando…</p>
    <template v-else>
      <section class="panel progreso" aria-live="polite">
        <p v-if="estado.listo"><strong>¡Listo para abrir!</strong> Haz el primer servicio en un día de poco volumen y ten el método anterior a la mano los primeros días.</p>
        <p v-else-if="!faltan"><strong>Todo listo.</strong></p>
        <p v-else><strong>{{ estado.hechos }} de {{ estado.total }} pasos.</strong> {{ faltan === 1 ? 'Falta 1.' : `Faltan ${faltan}.` }}</p>
        <div class="barra" role="progressbar" :aria-valuenow="avance" aria-valuemin="0" aria-valuemax="100" aria-label="Avance"><span :style="{ width: `${avance}%` }"></span></div>
      </section>

      <ol class="pasos">
        <li v-for="p in estado.pasos" :key="p.clave" class="panel paso" :class="{ hecho: p.hecho, actual: p.clave === siguiente }">
          <span class="marca" aria-hidden="true">{{ p.hecho ? '✓' : '' }}</span>
          <div class="info">
            <h2>{{ p.titulo }} <small v-if="!p.obligatorio" class="muted">Opcional</small></h2>
            <p class="muted">{{ p.descripcion }}</p>
            <template v-if="p.clave === 'ensayo' && !p.hecho">
              <ul class="ensayo">
                <li>Órdenes de prueba por cada canal: mesa, QR y mostrador{{ estado.pasos.some((x) => x.clave === 'domicilios') ? ' y domicilio' : '' }}.</li>
                <li>Que lleguen a cocina, se despachen y se entreguen.</li>
                <li>Cobro, arqueo y cierre de la jornada.</li>
              </ul>
              <p class="aviso">Hazlo mínimo un día antes de abrir: cerrar la jornada no deja recibir más órdenes ese día, y las ventas de prueba quedan en los reportes de esa fecha.</p>
            </template>
            <p v-if="p.marca" class="muted confirmado">{{ p.marca.por }} · {{ formatDateTime(p.marca.en) }}</p>
            <p class="visually-hidden">{{ p.hecho ? 'Hecho' : 'Pendiente' }}</p>
          </div>
          <div class="actions">
            <button v-if="p.accion === 'mesas'" class="btn btn-sm" :class="{ 'btn-secundario': p.hecho }" type="button" :disabled="busy" @click="abrirMesas">Crear mesas</button>
            <button v-if="p.accion === 'importar'" class="btn btn-sm" :class="{ 'btn-secundario': p.hecho }" type="button" @click="importando = true">Importar productos</button>
            <RouterLink v-if="p.ruta" class="btn btn-secundario btn-sm" :to="{ name: p.ruta }">Abrir</RouterLink>
            <template v-if="p.manual">
              <button v-if="!p.hecho" class="btn btn-sm" type="button" :disabled="busy || (p.clave === 'ensayo' && faltan > 1)" @click="marcar(p, true)">{{ p.boton }}</button>
              <button v-else class="btn btn-secundario btn-sm" type="button" :disabled="busy" @click="marcar(p, false)">Reabrir</button>
            </template>
          </div>
        </li>
      </ol>
    </template>

    <ImportarProductos :open="importando" @close="importando = false" @imported="load" />

    <AppModal :open="!!lote" title="Crear mesas" width="30rem" @close="lote = null">
      <form v-if="lote" @submit.prevent="crearMesas">
        <div class="form-grid">
          <div class="field">
            <label for="lote-zona">Zona</label>
            <select id="lote-zona" v-model="lote.zona_id" class="select">
              <option v-for="z in zonas" :key="z.id" :value="z.id">{{ z.nombre }}</option>
            </select>
          </div>
          <div class="field">
            <label for="lote-prefijo">Nombre</label>
            <input id="lote-prefijo" v-model="lote.prefijo" class="input" maxlength="30">
          </div>
          <div class="field">
            <label for="lote-desde">Desde el número</label>
            <input id="lote-desde" v-model.number="lote.desde" class="input" type="number" min="1" required>
          </div>
          <div class="field">
            <label for="lote-hasta">Hasta el número</label>
            <input id="lote-hasta" v-model.number="lote.hasta" class="input" type="number" min="1" required>
          </div>
        </div>
        <p class="muted espacio">Quedarán de «{{ lote.prefijo || 'Mesa' }} {{ lote.desde }}» a «{{ lote.prefijo || 'Mesa' }} {{ lote.hasta }}», cada una con su QR.</p>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="lote = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy">Crear</button>
        </div>
      </form>
    </AppModal>
  </div>
</template>

<style scoped>
.progreso {
  padding: var(--space-4);
  margin-bottom: var(--space-4);
}

.barra {
  height: 0.5rem;
  margin-top: var(--space-3);
  border-radius: 999px;
  background: var(--linea);
  overflow: hidden;
}

.barra span {
  display: block;
  height: 100%;
  background: var(--estado-entregado);
}

.pasos {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.paso {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
}

.paso.actual {
  border: 2px solid var(--accion);
}

.marca {
  flex: none;
  display: grid;
  place-items: center;
  width: 1.75rem;
  height: 1.75rem;
  border: 2px solid var(--linea-fuerte);
  border-radius: 50%;
  font-weight: 700;
}

.hecho .marca {
  border-color: var(--estado-entregado);
  background: var(--estado-entregado);
  color: #fff;
}

.info {
  flex: 1 1 16rem;
  min-width: 0;
}

.info h2 {
  font-size: var(--text-base, 1rem);
}

.info h2 small {
  font-weight: 400;
}

.ensayo {
  margin: var(--space-2) 0;
  padding-left: var(--space-5);
}

.aviso {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radio-sm);
  background: var(--estado-proceso-suave);
  font-size: var(--text-sm);
}

.confirmado {
  font-size: var(--text-sm);
}

.espacio {
  margin-top: var(--space-3);
}
</style>
