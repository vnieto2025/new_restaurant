<script setup>
import { computed, ref } from 'vue'
import StatusChip from '@/components/StatusChip.vue'
import { formatElapsed, CANALES } from '@/utils/format'

/*
  Tarjeta de comanda (doc 18, sección 3), en orden de prioridad visual:
  número y mesa/cliente, zona y canal, estado, ítems con notas resaltadas, tiempo, aviso de adición, acción.
*/
const props = defineProps({
  comanda: { type: Object, required: true },
  ahora: { type: Number, required: true },
  tiempoObjetivo: { type: Number, default: null },
  saltaEnProceso: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
})
const emit = defineEmits(['abrir', 'despachar', 'reabrir', 'imprimir', 'agotado'])

const seleccion = ref(new Set())

const vivos = computed(() => props.comanda.items.filter((i) => i.estado !== 'cancelado'))
const segundos = computed(() => (props.ahora - new Date(props.comanda.creado_en).getTime()) / 1000)
const demorada = computed(() =>
  props.tiempoObjetivo && props.comanda.pestana === 'en_proceso' && segundos.value > props.tiempoObjetivo * 60)

// Color del borde superior según el estado de la comanda (RG-24)
const COLORES = {
  nueva: 'var(--estado-nuevo)',
  en_proceso: 'var(--estado-proceso)',
  lista: 'var(--estado-despachado)',
  entregada: 'var(--estado-entregado)',
  cancelada: 'var(--estado-cancelado)',
}
const color = computed(() => COLORES[props.comanda.estado] || 'var(--estado-pendiente)')

const titulo = computed(() =>
  props.comanda.es_externa ? props.comanda.cliente_nombre || props.comanda.mesa : props.comanda.mesa)

const etiquetaCanal = computed(() => {
  if (props.comanda.canal === 'qr_rapido' || props.comanda.canal === 'mostrador') return 'Para llevar'
  if (props.comanda.canal === 'qr_mesa') return 'QR'
  return null
})

const hayNuevos = computed(() => vivos.value.some((i) => i.estado === 'nuevo'))
const despachables = computed(() =>
  vivos.value.filter((i) => i.estado === 'en_proceso' || (props.saltaEnProceso && i.estado === 'nuevo')))

const accion = computed(() => {
  if (props.comanda.pestana === 'listos') return null
  if (hayNuevos.value && !props.saltaEnProceso) return 'abrir'
  return despachables.value.length ? 'despachar' : null
})

function toggle(item) {
  if (accion.value !== 'despachar' || !despachables.value.includes(item)) return
  const next = new Set(seleccion.value)
  next.has(item.id) ? next.delete(item.id) : next.add(item.id)
  seleccion.value = next
}

function despachar() {
  emit('despachar', [...seleccion.value])
  seleccion.value = new Set()
}
</script>

<template>
  <article class="slip papel" :class="{ demorada }" :style="{ '--estado-color': color }"
           :aria-label="`Orden ${comanda.numero_texto}, ${titulo}`">
    <header class="top">
      <div class="numero">{{ comanda.numero_texto }}</div>
      <div class="donde">
        <strong>{{ titulo }}</strong>
        <span>{{ comanda.zona }}</span>
      </div>
    </header>

    <div class="marcas">
      <StatusChip :estado="comanda.estado" />
      <span v-if="etiquetaCanal" class="marca">{{ etiquetaCanal }}</span>
      <span v-if="comanda.es_adicion" class="marca marca-fuerte">Adición</span>
      <span v-if="comanda.modificada" class="marca marca-fuerte">Modificada</span>
    </div>

    <ul class="items">
      <li v-for="item in comanda.items" :key="item.id" :class="{ cancelado: item.estado === 'cancelado', elegido: seleccion.has(item.id) }"
          @click="toggle(item)">
        <span class="cant">{{ item.cantidad }}</span>
        <div class="desc">
          <span class="nombre">{{ item.nombre }}</span>
          <span v-for="mod in item.modificadores" :key="mod" class="mod">+ {{ mod }}</span>
          <span v-if="item.nota" class="nota">{{ item.nota }}</span>
          <span v-if="item.estado === 'cancelado'" class="nota">Cancelado: {{ item.motivo_cancelacion }}</span>
          <span v-else-if="comanda.pestana === 'en_proceso' && item.estado === 'despachado'" class="listo">Ya despachado</span>
        </div>
        <button v-if="['nuevo', 'en_proceso'].includes(item.estado)" class="agotado" type="button"
                :disabled="busy" @click.stop="emit('agotado', item)">Agotado</button>
      </li>
    </ul>

    <p v-if="comanda.notas" class="nota-orden">{{ comanda.notas }}</p>

    <footer class="pie">
      <span class="tiempo" :class="{ demora: demorada }">
        <span class="visually-hidden">Tiempo desde que llegó:</span>{{ formatElapsed(segundos) }}
        <span v-if="demorada" class="demora-texto">demorada</span>
      </span>
      <button class="btn-icono" type="button" :disabled="busy" @click="emit('imprimir')">Imprimir</button>
    </footer>

    <button v-if="accion === 'abrir'" class="accion abrir" type="button" :disabled="busy" @click="emit('abrir')">
      Abrir
    </button>
    <button v-else-if="accion === 'despachar'" class="accion despachar" type="button" :disabled="busy" @click="despachar">
      {{ seleccion.size ? `Despachar ${seleccion.size} de ${despachables.length}` : 'Despachar' }}
    </button>
    <button v-else-if="comanda.pestana === 'listos'" class="accion reabrir" type="button" :disabled="busy" @click="emit('reabrir')">
      Reabrir
    </button>
  </article>
</template>

<style scoped>
.slip {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-4) calc(var(--space-4) + var(--diente));
  border-top: 8px solid var(--estado-color, var(--estado-nuevo));
  border-radius: 3px 3px 0 0;
  min-height: 14rem;
}

/* Demora: borde rayado de precaución, distinto de cualquier color de estado (doc 16, sección 7) */
.slip.demorada {
  border-top-width: 14px;
  border-image: repeating-linear-gradient(-45deg, var(--tinta) 0 10px, var(--papel) 10px 20px) 14 / 14px 0 0 0;
}

.top {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}

.numero {
  font-family: var(--font-ui);
  font-weight: 800;
  font-stretch: 62%;
  font-size: var(--text-3xl);
  line-height: 0.9;
  letter-spacing: -0.02em;
}

.donde {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.donde strong {
  font-family: var(--font-ui);
  font-stretch: 75%;
  font-size: var(--text-xl);
  line-height: 1.1;
  overflow-wrap: anywhere;
}

.donde span {
  color: var(--acero);
  font-size: var(--text-sm);
}

.marcas {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.marca {
  padding: 0.15em 0.6em;
  border: 1.5px solid var(--tinta);
  border-radius: 999px;
  font-family: var(--font-ui);
  font-weight: 600;
  font-size: var(--text-sm);
}

.marca-fuerte {
  background: var(--tinta);
  color: var(--papel);
}

.items {
  list-style: none;
  margin: 0;
  padding: var(--space-3) 0 0;
  border-top: 1.5px dashed var(--linea-fuerte);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  flex: 1;
}

.items li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-1) var(--space-1);
  border-radius: var(--radio-sm);
  font-size: 1.125rem;
}

.items li.elegido {
  background: var(--estado-despachado-suave);
  outline: 2px solid var(--estado-despachado);
}

.cant {
  min-width: 2ch;
  font-weight: 600;
  font-size: var(--text-lg);
}

.desc {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.nombre {
  font-weight: 600;
  line-height: 1.25;
}

.mod {
  font-size: var(--text-base);
  font-weight: 600;
}

/* Las notas se leen primero: fondo amarillo de resaltador, no de estado */
.nota {
  align-self: flex-start;
  margin-top: 2px;
  padding: 0 0.35em;
  background: #fff2a8;
  font-size: var(--text-base);
}

.cancelado .nombre,
.cancelado .cant {
  text-decoration: line-through;
  color: var(--acero);
}

.cancelado .nota {
  background: var(--estado-cancelado-suave);
}

.listo {
  color: var(--estado-entregado);
  font-size: var(--text-sm);
}

.agotado {
  border: 1px solid var(--linea-fuerte);
  background: transparent;
  border-radius: var(--radio-sm);
  font-family: var(--font-ui);
  font-size: var(--text-sm);
  padding: 0.3em 0.6em;
  min-height: 2.25rem;
  cursor: pointer;
  color: var(--acero);
}

.nota-orden {
  padding: var(--space-2);
  background: #fff2a8;
}

.pie {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
}

.tiempo {
  font-size: var(--text-xl);
  font-weight: 600;
}

.tiempo.demora {
  text-decoration: underline wavy;
}

.demora-texto {
  margin-left: var(--space-2);
  font-family: var(--font-ui);
  font-size: var(--text-sm);
}

.btn-icono {
  border: 1px solid var(--linea-fuerte);
  background: transparent;
  border-radius: var(--radio-sm);
  min-height: 2.5rem;
  padding: 0 var(--space-3);
  font-family: var(--font-ui);
  cursor: pointer;
}

.accion {
  min-height: var(--toque-grande);
  border: none;
  border-radius: var(--radio);
  font-family: var(--font-ui);
  font-weight: 700;
  font-stretch: 85%;
  font-size: var(--text-xl);
  cursor: pointer;
  touch-action: manipulation;
}

.accion:disabled {
  opacity: 0.5;
}

.abrir {
  background: var(--tinta);
  color: var(--papel);
}

.despachar {
  background: var(--accion);
  color: #fff;
}

.reabrir {
  background: transparent;
  border: 1.5px solid var(--tinta);
  font-size: var(--text-base);
  min-height: var(--toque);
}
</style>
