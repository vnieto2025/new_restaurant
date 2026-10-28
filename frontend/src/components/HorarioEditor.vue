<script setup>
import { ref, watch } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'

/*
  Franjas semanales (doc 08A, sección 4). Sin franjas no hay restricción.
  Una franja que termina antes de empezar cruza la medianoche (ej. 18:00 a 02:00).
*/
const props = defineProps({
  tipo: { type: String, default: 'atencion' },
  zonaId: { type: Number, default: null },
  cartas: { type: Array, default: () => [] },
})

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
const { busy, attempt, quiet } = useAction()
const franjas = ref([])

async function load() {
  const data = await quiet(() => postData('/horario/get', { zona_id: props.zonaId }))
  franjas.value = (data?.[props.tipo] || []).map((f) => ({ ...f }))
}

watch(() => [props.zonaId, props.tipo], load, { immediate: true })

function agregar() {
  const ultima = franjas.value[franjas.value.length - 1]
  franjas.value.push({ dia_semana: ultima ? (ultima.dia_semana + 1) % 7 : 0, desde: ultima?.desde || '11:00',
    hasta: ultima?.hasta || '22:00', carta_id: ultima?.carta_id || props.cartas[0]?.id || null })
}

// Copia la primera franja a los siete días
function todosLosDias() {
  const base = franjas.value[0] || { desde: '11:00', hasta: '22:00', carta_id: props.cartas[0]?.id || null }
  franjas.value = DIAS.map((_, dia) => ({ dia_semana: dia, desde: base.desde, hasta: base.hasta, carta_id: base.carta_id }))
}

async function guardar() {
  const data = await attempt(() => postData('/horario/set', { tipo: props.tipo, zona_id: props.zonaId, franjas: franjas.value }),
    { success: franjas.value.length ? 'Horario guardado.' : 'Horario quitado.' })
  if (data) franjas.value = data.map((f) => ({ ...f }))
}
</script>

<template>
  <div class="horario">
    <p v-if="!franjas.length" class="muted">
      {{ tipo === 'carta' ? 'Sin franjas: la zona usa siempre su carta.' : 'Sin horario: se reciben órdenes a cualquier hora.' }}
    </p>
    <div v-for="(franja, index) in franjas" :key="index" class="fila">
      <select v-model.number="franja.dia_semana" class="select" :aria-label="`Día de la franja ${index + 1}`">
        <option v-for="(dia, valor) in DIAS" :key="valor" :value="valor">{{ dia }}</option>
      </select>
      <input v-model="franja.desde" class="input" type="time" :aria-label="`Desde, franja ${index + 1}`" required>
      <input v-model="franja.hasta" class="input" type="time" :aria-label="`Hasta, franja ${index + 1}`" required>
      <select v-if="tipo === 'carta'" v-model.number="franja.carta_id" class="select" :aria-label="`Carta de la franja ${index + 1}`">
        <option v-for="carta in cartas" :key="carta.id" :value="carta.id">{{ carta.nombre }}</option>
      </select>
      <button class="btn btn-secundario btn-sm" type="button" :aria-label="`Quitar franja ${index + 1}`" @click="franjas.splice(index, 1)">Quitar</button>
    </div>
    <div class="actions">
      <button class="btn btn-secundario btn-sm" type="button" @click="agregar">Agregar franja</button>
      <button class="btn btn-secundario btn-sm" type="button" @click="todosLosDias">Igual todos los días</button>
      <button class="btn btn-sm" type="button" :disabled="busy" @click="guardar">Guardar horario</button>
    </div>
  </div>
</template>

<style scoped>
.horario {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.fila {
  display: grid;
  grid-template-columns: minmax(7rem, 1fr) 7.5rem 7.5rem auto;
  gap: var(--space-2);
  align-items: center;
}

.fila:has(select:nth-of-type(2)) {
  grid-template-columns: minmax(7rem, 1fr) 7rem 7rem minmax(7rem, 1fr) auto;
}

@media (max-width: 34rem) {
  .fila,
  .fila:has(select:nth-of-type(2)) {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
