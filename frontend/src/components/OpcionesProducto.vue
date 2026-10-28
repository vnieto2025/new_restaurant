<script setup>
import { ref, computed, watch } from 'vue'
import AppModal from '@/components/AppModal.vue'
import { formatMoney } from '@/utils/format'

/*
  Elegir modificadores de un producto antes de agregarlo (doc 12, sección 3).
  Los grupos obligatorios (mínimo > 0) deben completarse para poder agregar (RN-PRO-03).
  En grupos de una sola opción se comporta como radio; en los demás, como casillas con tope.
*/
const props = defineProps({
  producto: { type: Object, default: null },
})
const emit = defineEmits(['close', 'confirm'])

const elegidas = ref({})

watch(() => props.producto, (producto) => {
  elegidas.value = Object.fromEntries((producto?.grupos || []).map((g) => [g.id, []]))
})

const grupos = computed(() => props.producto?.grupos || [])

const extra = computed(() => grupos.value.reduce((sum, g) =>
  sum + g.opciones.filter((o) => elegidas.value[g.id]?.includes(o.id)).reduce((s, o) => s + o.precio_extra, 0), 0))

const faltantes = computed(() => grupos.value.filter((g) => (elegidas.value[g.id]?.length || 0) < g.minimo))

function toggle(grupo, opcion) {
  const actuales = elegidas.value[grupo.id] || []
  if (grupo.maximo === 1) {
    elegidas.value[grupo.id] = actuales.includes(opcion.id) && grupo.minimo === 0 ? [] : [opcion.id]
    return
  }
  if (actuales.includes(opcion.id)) elegidas.value[grupo.id] = actuales.filter((id) => id !== opcion.id)
  else if (actuales.length < grupo.maximo) elegidas.value[grupo.id] = [...actuales, opcion.id]
}

function regla(grupo) {
  if (grupo.minimo > 0 && grupo.maximo === grupo.minimo) return grupo.minimo === 1 ? 'Elige una' : `Elige ${grupo.minimo}`
  if (grupo.minimo > 0) return `Elige de ${grupo.minimo} a ${grupo.maximo}`
  return grupo.maximo === 1 ? 'Opcional' : `Opcional, hasta ${grupo.maximo}`
}

function confirmar() {
  if (faltantes.value.length) return
  const opciones = grupos.value.flatMap((g) => g.opciones.filter((o) => elegidas.value[g.id]?.includes(o.id)))
  emit('confirm', opciones)
}
</script>

<template>
  <AppModal :open="!!producto" :title="producto?.nombre || ''" width="30rem" @close="emit('close')">
    <form v-if="producto" class="opciones" @submit.prevent="confirmar">
      <fieldset v-for="grupo in grupos" :key="grupo.id" class="grupo">
        <legend>
          <span class="nombre">{{ grupo.nombre }}</span>
          <span class="regla" :class="{ falta: faltantes.includes(grupo) }">{{ regla(grupo) }}</span>
        </legend>
        <button v-for="opcion in grupo.opciones" :key="opcion.id" type="button" class="opcion"
                :aria-pressed="elegidas[grupo.id]?.includes(opcion.id)" @click="toggle(grupo, opcion)">
          <span>{{ opcion.nombre }}</span>
          <span v-if="opcion.precio_extra" class="precio">+ {{ formatMoney(opcion.precio_extra) }}</span>
        </button>
      </fieldset>
      <button class="btn btn-grande btn-bloque" type="submit" :disabled="faltantes.length > 0">
        {{ faltantes.length ? `Falta: ${faltantes[0].nombre.toLowerCase()}` : `Agregar · ${formatMoney(producto.precio + extra)}` }}
      </button>
    </form>
  </AppModal>
</template>

<style scoped>
.opciones {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.grupo {
  margin: 0;
  padding: 0;
  border: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.grupo legend {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  width: 100%;
  margin-bottom: var(--space-2);
}

.nombre {
  font-weight: 700;
  font-size: var(--text-lg);
}

.regla {
  color: var(--acero);
  font-size: var(--text-sm);
}

.regla.falta {
  color: var(--peligro);
  font-weight: 600;
}

.opcion {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: var(--toque);
  padding: 0 var(--space-4);
  border: 1px solid var(--linea-fuerte);
  border-radius: var(--radio);
  background: var(--superficie);
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  touch-action: manipulation;
}

.opcion[aria-pressed='true'] {
  border: 2px solid var(--accion);
  background: var(--accion-suave);
  font-weight: 700;
}

.precio {
  color: var(--acero);
  font-size: var(--text-sm);
}
</style>
