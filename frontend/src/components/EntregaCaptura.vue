<script setup>
import { computed } from 'vue'
import { formatMoney } from '@/utils/format'

/*
  Datos de un domicilio (doc 15B, RN-DOM-01): zona de envío, dirección y referencias.
  Si el cliente ya pidió antes, sus direcciones guardadas se eligen con un toque.
*/
const entrega = defineModel({ type: Object, required: true }) // { zona_envio_id, direccion, barrio, indicaciones, guardar_direccion }
const props = defineProps({
  zonas: { type: Array, required: true },
  direcciones: { type: Array, default: () => [] },
  valorPedido: { type: Number, default: 0 },
  puedeGuardar: { type: Boolean, default: false },
})

const zona = computed(() => props.zonas.find((z) => z.id === Number(entrega.value.zona_envio_id)))
const faltaMinimo = computed(() => zona.value?.pedido_minimo && props.valorPedido < zona.value.pedido_minimo)

// Si el barrio escrito aparece en la lista de una zona, se sugiere esa zona
const sugerida = computed(() => {
  const barrio = (entrega.value.barrio || '').trim().toLowerCase()
  if (barrio.length < 3 || entrega.value.zona_envio_id) return null
  return props.zonas.find((z) => (z.barrios || '').toLowerCase().split(',').some((b) => b.trim().includes(barrio))) || null
})

function usarDireccion(d) {
  entrega.value = { ...entrega.value, direccion: d.direccion, barrio: d.barrio || '', indicaciones: d.indicaciones || '', guardar_direccion: false }
}
</script>

<template>
  <fieldset class="entrega">
    <legend>Entrega a domicilio</legend>
    <div v-if="direcciones.length" class="guardadas" role="group" aria-label="Direcciones guardadas del cliente">
      <button v-for="d in direcciones" :key="d.id" type="button" class="guardada"
              :aria-pressed="entrega.direccion === d.direccion" @click="usarDireccion(d)">
        <strong>{{ d.nombre || 'Dirección' }}</strong> {{ d.direccion }}
      </button>
    </div>
    <div class="field">
      <label for="en-dir">Dirección</label>
      <input id="en-dir" v-model="entrega.direccion" class="input" maxlength="200" autocomplete="off" placeholder="Calle 10 # 5-20 apto 301">
    </div>
    <div class="field">
      <label for="en-barrio">Barrio</label>
      <input id="en-barrio" v-model="entrega.barrio" class="input" maxlength="80" autocomplete="off">
      <button v-if="sugerida" type="button" class="sugerencia" @click="entrega.zona_envio_id = sugerida.id">
        ¿Zona {{ sugerida.nombre }}? Toca para elegirla
      </button>
    </div>
    <div class="field">
      <label for="en-zona">Zona de envío</label>
      <select id="en-zona" v-model="entrega.zona_envio_id" class="select">
        <option value="" disabled>Elige la zona</option>
        <option v-for="z in zonas" :key="z.id" :value="z.id">{{ z.nombre }} · {{ formatMoney(z.tarifa) }}</option>
      </select>
      <span v-if="zona?.barrios" class="hint">{{ zona.barrios }}</span>
    </div>
    <p v-if="faltaMinimo" class="aviso" role="alert">El pedido mínimo para {{ zona.nombre }} es {{ formatMoney(zona.pedido_minimo) }}.</p>
    <div class="field">
      <label for="en-ind">Indicaciones</label>
      <input id="en-ind" v-model="entrega.indicaciones" class="input" maxlength="250" placeholder="Portería, color de la casa…">
    </div>
    <label v-if="puedeGuardar" class="check">
      <input v-model="entrega.guardar_direccion" type="checkbox"> Guardar esta dirección para el próximo pedido
    </label>
  </fieldset>
</template>

<style scoped>
.entrega {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin: 0;
  padding: var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio-sm);
}

.entrega legend {
  padding: 0 var(--space-1);
  font-weight: 700;
}

.guardadas {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.guardada {
  min-height: var(--toque);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio-sm);
  background: var(--papel);
  text-align: left;
  cursor: pointer;
}

.guardada[aria-pressed='true'] {
  border-color: var(--accion);
  background: var(--accion-suave);
}

.sugerencia {
  align-self: flex-start;
  margin-top: var(--space-1);
  padding: var(--space-1) var(--space-2);
  border: none;
  border-radius: var(--radio-sm);
  background: var(--accion-suave);
  font-weight: 600;
  cursor: pointer;
}

.aviso {
  padding: var(--space-2) var(--space-3);
  border-left: 4px solid var(--estado-pendiente);
  border-radius: var(--radio-sm);
  background: var(--estado-pendiente-suave);
  font-size: var(--text-sm);
}

.check {
  font-size: var(--text-sm);
}
</style>
