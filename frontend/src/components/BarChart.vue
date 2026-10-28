<script setup>
import { ref, computed } from 'vue'

/*
  Barras de una sola serie (ventas por jornada). Sin librerías.
  Una serie no lleva leyenda: el título la nombra. Barras finas con extremo redondeado,
  separación de 2 px, cuadrícula discreta, tooltip al pasar o enfocar y vista de tabla.
  El color no reutiliza los de estado de órdenes (RG-24); validado con la guía de visualización.
*/
const props = defineProps({
  titulo: { type: String, required: true },
  datos: { type: Array, required: true }, // [{ etiqueta, valor, detalle }]
  formato: { type: Function, default: (v) => String(v) },
  formatoCorto: { type: Function, default: (v) => String(v) },
})

const ANCHO = 640
const ALTO = 220
const MARGEN = { arriba: 16, derecha: 8, abajo: 28, izquierda: 56 }

const verTabla = ref(false)
const activo = ref(null)

const maximo = computed(() => Math.max(1, ...props.datos.map((d) => d.valor)))
// Escala con tres líneas de referencia "redondas"
const escala = computed(() => {
  const crudo = maximo.value / 3
  const potencia = 10 ** Math.floor(Math.log10(crudo))
  const paso = [1, 2, 2.5, 5, 10].map((m) => m * potencia).find((p) => p >= crudo)
  return { paso, tope: paso * 3 }
})
const lineas = computed(() => [0, 1, 2, 3].map((i) => i * escala.value.paso))

const areaAncho = ANCHO - MARGEN.izquierda - MARGEN.derecha
const areaAlto = ALTO - MARGEN.arriba - MARGEN.abajo
const banda = computed(() => areaAncho / Math.max(1, props.datos.length))
const anchoBarra = computed(() => Math.max(2, Math.min(28, banda.value - 2)))

function y(valor) {
  return MARGEN.arriba + areaAlto - (valor / escala.value.tope) * areaAlto
}

// Barra con las esquinas superiores redondeadas (4 px) y la base recta sobre el eje
function barra(d, i) {
  const x = MARGEN.izquierda + i * banda.value + (banda.value - anchoBarra.value) / 2
  const base = MARGEN.arriba + areaAlto
  const top = y(d.valor)
  const r = Math.min(4, anchoBarra.value / 2, base - top)
  if (d.valor <= 0) return ''
  return `M${x},${base} V${top + r} Q${x},${top} ${x + r},${top} H${x + anchoBarra.value - r} Q${x + anchoBarra.value},${top} ${x + anchoBarra.value},${top + r} V${base} Z`
}

function centro(i) {
  return MARGEN.izquierda + i * banda.value + banda.value / 2
}

// Con muchos días solo se rotulan algunos en el eje
const cadaCuanto = computed(() => Math.ceil(props.datos.length / 10))
const indiceMaximo = computed(() => props.datos.reduce((m, d, i, arr) => (d.valor > arr[m].valor ? i : m), 0))

const tooltip = computed(() => {
  if (activo.value === null) return null
  const d = props.datos[activo.value]
  return { d, x: (centro(activo.value) / ANCHO) * 100, y: (y(d.valor) / ALTO) * 100 }
})
</script>

<template>
  <figure class="grafico">
    <figcaption class="cabeza">
      <span class="titulo">{{ titulo }}</span>
      <button type="button" class="alternar" @click="verTabla = !verTabla">{{ verTabla ? 'Ver gráfico' : 'Ver como tabla' }}</button>
    </figcaption>

    <div v-if="!verTabla" class="lienzo" @mouseleave="activo = null">
      <svg :viewBox="`0 0 ${ANCHO} ${ALTO}`" role="img" :aria-label="titulo" preserveAspectRatio="none">
        <g class="cuadricula">
          <g v-for="valor in lineas" :key="valor">
            <line :x1="MARGEN.izquierda" :x2="ANCHO - MARGEN.derecha" :y1="y(valor)" :y2="y(valor)" />
          </g>
        </g>
        <g class="barras">
          <path v-for="(d, i) in datos" :key="i" :d="barra(d, i)" :class="{ resaltada: activo === i }" />
        </g>
        <!-- Zonas de toque más anchas que la barra -->
        <rect v-for="(d, i) in datos" :key="`h${i}`" class="toque" :x="MARGEN.izquierda + i * banda" :y="MARGEN.arriba"
              :width="banda" :height="areaAlto" tabindex="0" :aria-label="`${d.etiqueta}: ${formato(d.valor)}`"
              @mouseenter="activo = i" @focus="activo = i" @blur="activo = null" />
      </svg>
      <!-- Ejes en HTML para que el texto no se deforme con el ancho -->
      <span v-for="valor in lineas" :key="`e${valor}`" class="eje-y" :style="{ top: `${(y(valor) / ALTO) * 100}%` }">
        {{ formatoCorto(valor) }}
      </span>
      <span v-for="(d, i) in datos" v-show="i % cadaCuanto === 0" :key="`x${i}`" class="eje-x"
            :style="{ left: `${(centro(i) / ANCHO) * 100}%` }">{{ d.etiqueta }}</span>
      <span v-if="datos.length && datos[indiceMaximo].valor > 0 && activo === null" class="etiqueta-max"
            :style="{ left: `${(centro(indiceMaximo) / ANCHO) * 100}%`, top: `${(y(datos[indiceMaximo].valor) / ALTO) * 100}%` }">
        {{ formatoCorto(datos[indiceMaximo].valor) }}
      </span>
      <div v-if="tooltip" class="tooltip" :style="{ left: `${tooltip.x}%`, top: `${tooltip.y}%` }" role="status">
        <strong>{{ tooltip.d.etiqueta }}</strong>
        <span>{{ formato(tooltip.d.valor) }}</span>
        <span v-if="tooltip.d.detalle" class="detalle">{{ tooltip.d.detalle }}</span>
      </div>
    </div>

    <div v-else class="table-wrap">
      <table class="table">
        <thead><tr><th>Jornada</th><th class="num">Ventas</th><th v-if="datos[0]?.detalle">Detalle</th></tr></thead>
        <tbody>
          <tr v-for="(d, i) in datos" :key="i">
            <td>{{ d.etiqueta }}</td><td class="num">{{ formato(d.valor) }}</td><td v-if="d.detalle">{{ d.detalle }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </figure>
</template>

<style scoped>
.grafico {
  --serie-1: #00899b;
  margin: 0;
  padding: var(--space-4);
  background: var(--superficie);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
}

.cabeza {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.titulo {
  font-weight: 700;
}

.alternar {
  border: none;
  background: none;
  color: var(--accion);
  text-decoration: underline;
  font-size: var(--text-sm);
  cursor: pointer;
}

.lienzo {
  position: relative;
  height: 15rem;
  margin: 0 0 var(--space-5);
}

svg {
  width: 100%;
  height: 100%;
  display: block;
  overflow: visible;
}

.cuadricula line {
  stroke: var(--linea);
  stroke-width: 1;
  vector-effect: non-scaling-stroke;
}

.barras path {
  fill: var(--serie-1);
}

.barras path.resaltada {
  fill: #006a78;
}

.toque {
  fill: transparent;
  outline: none;
  cursor: default;
}

.eje-y {
  position: absolute;
  left: 0;
  width: calc(56 / 640 * 100% - 6px);
  transform: translateY(-50%);
  text-align: right;
  color: var(--acero);
  font-size: 0.75rem;
}

.eje-x {
  position: absolute;
  bottom: -1.5rem;
  transform: translateX(-50%);
  color: var(--acero);
  font-size: 0.75rem;
  white-space: nowrap;
}

.etiqueta-max {
  position: absolute;
  transform: translate(-50%, calc(-100% - 4px));
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--tinta);
  white-space: nowrap;
}

.tooltip {
  position: absolute;
  transform: translate(-50%, calc(-100% - 8px));
  display: flex;
  flex-direction: column;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radio-sm);
  background: var(--tinta);
  color: #fff;
  font-size: var(--text-sm);
  white-space: nowrap;
  pointer-events: none;
  z-index: 2;
}

.detalle {
  color: #c4ccd0;
}
</style>
