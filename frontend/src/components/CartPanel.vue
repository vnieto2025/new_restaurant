<script setup>
import { computed } from 'vue'
import { formatMoney } from '@/utils/format'

// Lo que se va a enviar: cantidades con +/-, nota por ítem y total estimado
const props = defineProps({
  lineas: { type: Array, required: true },
  titulo: { type: String, default: 'Por enviar' },
})
const emit = defineEmits(['change', 'remove'])

const total = computed(() => props.lineas.reduce((sum, l) => sum + l.precio * l.cantidad, 0))

function step(linea, delta) {
  const cantidad = linea.cantidad + delta
  if (cantidad <= 0) emit('remove', linea)
  else emit('change', { ...linea, cantidad })
}
</script>

<template>
  <section class="cart">
    <h2>{{ titulo }}</h2>
    <p v-if="!lineas.length" class="muted vacio">Toca un producto para agregarlo.</p>
    <ul v-else class="lineas">
      <li v-for="linea in lineas" :key="linea.uid" class="linea">
        <div class="fila">
          <span class="nombre">{{ linea.nombre }}<small v-if="linea.modificadores?.length" class="mods">{{ linea.modificadores.map((m) => m.nombre).join(', ') }}</small></span>
          <span class="precio">{{ formatMoney(linea.precio * linea.cantidad) }}</span>
        </div>
        <div class="fila">
          <div class="stepper" role="group" :aria-label="`Cantidad de ${linea.nombre}`">
            <button type="button" :aria-label="linea.cantidad === 1 ? 'Quitar' : 'Uno menos'" @click="step(linea, -1)">
              {{ linea.cantidad === 1 ? '×' : '−' }}
            </button>
            <span class="cantidad">{{ linea.cantidad }}</span>
            <button type="button" aria-label="Uno más" @click="step(linea, 1)">+</button>
          </div>
          <input class="input nota" :value="linea.nota" maxlength="200" placeholder="Nota: sin cebolla…"
                 :aria-label="`Nota para ${linea.nombre}`" @input="emit('change', { ...linea, nota: $event.target.value })">
        </div>
      </li>
    </ul>
    <p v-if="lineas.length" class="total"><span>Total</span><strong>{{ formatMoney(total) }}</strong></p>
    <slot />
  </section>
</template>

<style scoped>
.cart {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.vacio {
  padding: var(--space-3) 0;
}

.lineas {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.linea {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--linea);
}

.fila {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.nombre {
  font-weight: 600;
}

.mods {
  display: block;
  color: var(--acero);
  font-weight: 400;
  font-size: var(--text-sm);
}

.stepper {
  display: flex;
  align-items: center;
  border: 1px solid var(--linea-fuerte);
  border-radius: var(--radio);
  flex: none;
}

.stepper button {
  width: var(--toque);
  height: var(--toque);
  border: none;
  background: transparent;
  font-size: 1.375rem;
  cursor: pointer;
  touch-action: manipulation;
}

.cantidad {
  min-width: 2ch;
  text-align: center;
  font-weight: 700;
  font-size: var(--text-lg);
}

.nota {
  min-height: var(--toque);
  font-size: var(--text-sm);
}

.total {
  display: flex;
  justify-content: space-between;
  font-size: var(--text-lg);
}
</style>
