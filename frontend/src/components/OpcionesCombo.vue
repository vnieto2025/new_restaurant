<script setup>
import { ref, computed, watch } from 'vue'
import AppModal from '@/components/AppModal.vue'
import { formatMoney } from '@/utils/format'

/*
  Armar un combo antes de agregarlo (doc 12, sección 4): en cada componente se elige un producto (si solo hay uno,
  viene fijo) y, si ese producto tiene opciones obligatorias (el término de la carne), también se eligen aquí.
*/
const props = defineProps({
  combo: { type: Object, default: null },
})
const emit = defineEmits(['close', 'confirm'])

// Por componente: producto elegido y opciones de sus modificadores
const elegido = ref({})
const mods = ref({})

watch(() => props.combo, (combo) => {
  elegido.value = {}
  mods.value = {}
  for (const c of combo?.componentes || []) {
    if (c.opciones.length === 1) elegir(c, c.opciones[0])
  }
})

const componentes = computed(() => props.combo?.componentes || [])

function opcionDe(c) {
  return c.opciones.find((o) => o.producto_id === elegido.value[c.id])
}

function elegir(c, opcion) {
  elegido.value[c.id] = opcion.producto_id
  mods.value[c.id] = Object.fromEntries((opcion.grupos || []).map((g) => [g.id, []]))
}

function toggle(c, grupo, opcion) {
  const actuales = mods.value[c.id][grupo.id] || []
  if (grupo.maximo === 1) {
    mods.value[c.id][grupo.id] = actuales.includes(opcion.id) && grupo.minimo === 0 ? [] : [opcion.id]
  } else if (actuales.includes(opcion.id)) {
    mods.value[c.id][grupo.id] = actuales.filter((id) => id !== opcion.id)
  } else if (actuales.length < grupo.maximo) {
    mods.value[c.id][grupo.id] = [...actuales, opcion.id]
  }
}

// Lo primero que falta, para decirlo en el botón
const falta = computed(() => {
  for (const c of componentes.value) {
    const opcion = opcionDe(c)
    if (!opcion) return c.nombre
    const grupo = (opcion.grupos || []).find((g) => (mods.value[c.id]?.[g.id]?.length || 0) < g.minimo)
    if (grupo) return `${grupo.nombre.toLowerCase()} de ${opcion.nombre}`
  }
  return null
})

const extra = computed(() => componentes.value.reduce((suma, c) => {
  const opcion = opcionDe(c)
  if (!opcion) return suma
  const deMods = (opcion.grupos || []).reduce((s, g) => s + g.opciones.filter((o) => mods.value[c.id]?.[g.id]?.includes(o.id))
    .reduce((t, o) => t + o.precio_extra, 0), 0)
  return suma + (opcion.precio_extra + deMods) * c.cantidad
}, 0))

function confirmar() {
  if (falta.value) return
  emit('confirm', {
    extra: extra.value,
    componentes: componentes.value.map((c) => {
      const opcion = opcionDe(c)
      const elegidas = (opcion.grupos || []).flatMap((g) => g.opciones.filter((o) => mods.value[c.id]?.[g.id]?.includes(o.id)))
      return {
        componente_id: c.id,
        producto_id: opcion.producto_id,
        modificadores: elegidas.map((o) => o.id),
        // Para mostrar en el carrito; el precio lo calcula el servidor
        detalle: opcion.nombre + (elegidas.length ? ` (${elegidas.map((o) => o.nombre).join(', ')})` : ''),
      }
    }),
  })
}
</script>

<template>
  <AppModal :open="!!combo" :title="combo?.nombre || ''" width="34rem" @close="emit('close')">
    <form v-if="combo" class="opciones" @submit.prevent="confirmar">
      <fieldset v-for="c in componentes" :key="c.id" class="grupo">
        <legend>
          <span class="nombre">{{ c.cantidad > 1 ? `${c.cantidad} × ` : '' }}{{ c.nombre }}</span>
          <span class="regla">{{ c.opciones.length === 1 ? 'Incluido' : 'Elige uno' }}</span>
        </legend>
        <button v-for="opcion in c.opciones" :key="opcion.producto_id" type="button" class="opcion"
                :aria-pressed="elegido[c.id] === opcion.producto_id" @click="elegir(c, opcion)">
          <span>{{ opcion.nombre }}</span>
          <span v-if="opcion.precio_extra" class="precio">+ {{ formatMoney(opcion.precio_extra) }}</span>
        </button>
        <template v-if="opcionDe(c)">
          <div v-for="grupo in opcionDe(c).grupos" :key="grupo.id" class="subgrupo" role="group" :aria-label="`${grupo.nombre} de ${opcionDe(c).nombre}`">
            <p class="subtitulo">{{ grupo.nombre }}<span v-if="grupo.minimo" class="regla"> · obligatorio</span></p>
            <div class="chips">
              <button v-for="o in grupo.opciones" :key="o.id" type="button" class="chip" :aria-pressed="mods[c.id]?.[grupo.id]?.includes(o.id)"
                      @click="toggle(c, grupo, o)">{{ o.nombre }}<template v-if="o.precio_extra"> +{{ formatMoney(o.precio_extra) }}</template></button>
            </div>
          </div>
        </template>
      </fieldset>
      <button class="btn btn-grande btn-bloque" type="submit" :disabled="!!falta">
        {{ falta ? `Falta: ${falta.toLowerCase()}` : `Agregar · ${formatMoney(combo.precio + extra)}` }}
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

.subgrupo {
  margin-left: var(--space-4);
  padding-left: var(--space-3);
  border-left: 3px solid var(--linea);
}

.subtitulo {
  font-weight: 600;
  margin-bottom: var(--space-1);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.chip {
  min-height: var(--toque);
  padding: 0 var(--space-3);
  border: 1px solid var(--linea-fuerte);
  border-radius: 999px;
  background: var(--superficie);
  cursor: pointer;
  touch-action: manipulation;
}

.chip[aria-pressed='true'] {
  border: 2px solid var(--accion);
  background: var(--accion-suave);
  font-weight: 700;
}
</style>
