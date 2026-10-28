<script setup>
import { ref, watch, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'
import { formatTime } from '@/utils/format'
import { enlaceWhatsapp } from '@/utils/inventario'

/*
  Avisos por WhatsApp que alguien debe enviar (doc 31B, opción B): el botón abre WhatsApp con el mensaje
  ya escrito y lo marca como enviado. También aparecen los automáticos que fallaron, para avisar a mano.
*/
const props = defineProps({
  // Cambia cuando la pantalla recibe un evento en tiempo real: se vuelve a consultar
  refresco: { type: Number, default: 0 },
})
const emit = defineEmits(['cuenta'])

const { attempt, quiet } = useAction()
const avisos = ref([])

async function load() {
  avisos.value = (await quiet(() => postData('/notificacion/pendientes'))) || []
  emit('cuenta', avisos.value.length)
}

// Se abre WhatsApp desde el enlace y, en paralelo, se registra el envío (RN-NOT-03)
async function enviado(aviso) {
  await attempt(() => postData('/notificacion/enviada', { notificacion_id: aviso.id }))
  load()
}

async function descartar(aviso) {
  await attempt(() => postData('/notificacion/descartar', { notificacion_id: aviso.id }), { success: 'Aviso descartado.' })
  load()
}

watch(() => props.refresco, load)
onMounted(load)
defineExpose({ load })
</script>

<template>
  <section v-if="avisos.length" class="avisos" aria-label="Avisos por WhatsApp por enviar">
    <h2>Avisar por WhatsApp <span class="cuenta">{{ avisos.length }}</span></h2>
    <ul>
      <li v-for="a in avisos" :key="a.id" :class="{ fallida: a.estado === 'fallida' }">
        <div class="texto">
          <strong>{{ a.orden }} · {{ a.nombre || 'Cliente' }}</strong>
          <span class="muted">{{ a.evento_texto }} · {{ a.telefono_legible }} · {{ formatTime(a.hora_local || a.creado_en) }}</span>
          <span v-if="a.estado === 'fallida'" class="error">No salió automático: {{ a.error }}</span>
          <q>{{ a.mensaje }}</q>
        </div>
        <div class="acciones">
          <a class="btn btn-sm" :href="enlaceWhatsapp(a.telefono, a.mensaje)" target="_blank" rel="noopener" @click="enviado(a)">
            Enviar por WhatsApp</a>
          <button class="btn btn-secundario btn-sm" type="button" @click="descartar(a)">Descartar</button>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.avisos {
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--linea);
  border-left: 4px solid var(--estado-despachado);
  border-radius: var(--radio);
  background: var(--superficie);
}

h2 {
  font-size: var(--text-base);
  margin-bottom: var(--space-2);
}

.cuenta {
  margin-left: var(--space-1);
  padding: 0.05em 0.55em;
  border-radius: 999px;
  background: var(--estado-despachado-suave);
  font-size: var(--text-sm);
}

ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2) var(--space-3);
  padding-top: var(--space-2);
  border-top: 1px solid var(--linea);
}

li:first-child {
  border-top: none;
  padding-top: 0;
}

.texto {
  display: flex;
  flex-direction: column;
  flex: 1 1 18rem;
  min-width: 0;
}

q {
  font-size: var(--text-sm);
  color: var(--acero);
}

.error {
  color: var(--estado-cancelado);
  font-size: var(--text-sm);
  font-weight: 600;
}

.acciones {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
</style>
