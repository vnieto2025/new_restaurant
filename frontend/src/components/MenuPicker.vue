<script setup>
import { ref, computed } from 'vue'
import { formatMoney, mediaUrl } from '@/utils/format'
import OpcionesProducto from '@/components/OpcionesProducto.vue'
import OpcionesCombo from '@/components/OpcionesCombo.vue'
import { useEscaner } from '@/composables/useEscaner'
import { useToastStore } from '@/stores/toast'

/*
  Selector de productos para tomar órdenes (doc 34): categorías, búsqueda y botones grandes.
  Agregar un producto es un toque y no pide confirmación (doc 33, principio 5).
*/
const props = defineProps({
  categorias: { type: Array, default: () => [] },
  cantidades: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['add'])

const categoriaId = ref(null)
const conOpciones = ref(null)
const combo = ref(null)
const buscar = ref('')

// Cómo se ven los productos, como en el explorador de archivos; cada equipo recuerda la suya (ADR-059)
const VISTAS = [
  { valor: 'cuadricula', titulo: 'Cuadrícula' },
  { valor: 'lista', titulo: 'Lista' },
  { valor: 'mediana', titulo: 'Fotos medianas' },
  { valor: 'grande', titulo: 'Fotos grandes' },
]
const CLAVE_VISTA = 'carta.vista'
function leerVista() {
  try {
    const guardada = localStorage.getItem(CLAVE_VISTA)
    return VISTAS.some((v) => v.valor === guardada) ? guardada : 'cuadricula'
  } catch {
    return 'cuadricula'
  }
}
const vista = ref(leerVista())
function cambiarVista(valor) {
  vista.value = valor
  try {
    localStorage.setItem(CLAVE_VISTA, valor)
  } catch {
    // Sin almacenamiento la vista dura hasta recargar
  }
}
const conFoto = computed(() => ['mediana', 'grande'].includes(vista.value))
const toast = useToastStore()
const escaneado = ref(null)

// Código de barras -> producto, de toda la carta (ADR-058)
const porCodigo = computed(() => new Map(props.categorias.flatMap((c) => c.productos)
  .filter((p) => p.codigo_barras).map((p) => [p.codigo_barras, p])))

function pitido() {
  try {
    const audio = new AudioContext()
    const osc = audio.createOscillator()
    osc.frequency.value = 220
    osc.connect(audio.destination)
    osc.start()
    osc.stop(audio.currentTime + 0.25)
  } catch {
    // Navegador sin audio
  }
}

useEscaner((codigo, campo) => {
  // Si el lector escribió en el buscador, se limpia: no era una búsqueda
  if (campo?.closest?.('.buscar')) buscar.value = ''
  if (conOpciones.value || combo.value) return
  const producto = porCodigo.value.get(codigo)
  if (!producto) {
    pitido()
    toast.error(`El código ${codigo} no está registrado en ningún producto de esta carta.`)
    return
  }
  if (producto.agotado) {
    pitido()
    toast.error(`${producto.nombre} está agotado.`)
    return
  }
  escaneado.value = producto.nombre
  elegir(producto)
})

// Un toque agrega; si el producto tiene modificadores, primero se eligen
function elegir(producto) {
  if (producto.tipo === 'combo') combo.value = producto
  else if (producto.grupos?.length) conOpciones.value = producto
  else emit('add', producto, [])
}

function confirmarCombo(seleccion) {
  emit('add', combo.value, [], seleccion)
  combo.value = null
}

function confirmar(opciones) {
  emit('add', conOpciones.value, opciones)
  conOpciones.value = null
}

function normalize(text) {
  return String(text || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
}

const productos = computed(() => {
  const texto = normalize(buscar.value.trim())
  if (texto) {
    return props.categorias.flatMap((c) => c.productos)
      .filter((p) => normalize(p.nombre).includes(texto) || (p.codigo_barras && p.codigo_barras.includes(texto)))
  }
  const categoria = props.categorias.find((c) => c.id === categoriaId.value) || props.categorias[0]
  return categoria ? categoria.productos : []
})

const activa = computed(() => (buscar.value.trim() ? null : categoriaId.value ?? props.categorias[0]?.id))
</script>

<template>
  <section class="picker">
    <div class="buscar">
      <div class="barra">
        <input v-model="buscar" class="input" type="search" placeholder="Buscar producto o escanear código" aria-label="Buscar producto">
        <div class="vistas" role="group" aria-label="Ver productos como">
          <button v-for="v in VISTAS" :key="v.valor" type="button" class="vista" :aria-pressed="vista === v.valor"
                  :title="v.titulo" :aria-label="v.titulo" @click="cambiarVista(v.valor)">
            <svg viewBox="0 0 20 20" aria-hidden="true">
              <template v-if="v.valor === 'cuadricula'">
                <rect x="2" y="2" width="7" height="7" rx="1" /><rect x="11" y="2" width="7" height="7" rx="1" />
                <rect x="2" y="11" width="7" height="7" rx="1" /><rect x="11" y="11" width="7" height="7" rx="1" />
              </template>
              <template v-else-if="v.valor === 'lista'">
                <rect x="2" y="3" width="16" height="2.5" rx="1" /><rect x="2" y="8.75" width="16" height="2.5" rx="1" />
                <rect x="2" y="14.5" width="16" height="2.5" rx="1" />
              </template>
              <template v-else-if="v.valor === 'mediana'">
                <rect x="2" y="2" width="7" height="5" rx="1" /><rect x="11" y="2" width="7" height="5" rx="1" />
                <rect x="2" y="8.5" width="7" height="1.5" rx=".5" /><rect x="11" y="8.5" width="7" height="1.5" rx=".5" />
                <rect x="2" y="11" width="7" height="5" rx="1" /><rect x="11" y="11" width="7" height="5" rx="1" />
              </template>
              <template v-else>
                <rect x="2" y="2" width="16" height="11" rx="1.5" /><rect x="2" y="15" width="11" height="2.5" rx="1" />
              </template>
            </svg>
          </button>
        </div>
      </div>
      <p v-if="escaneado" class="escaneado" role="status">Escaneado: {{ escaneado }}</p>
    </div>

    <div class="categorias" role="tablist" aria-label="Categorías">
      <button v-for="categoria in categorias" :key="categoria.id" role="tab" type="button" class="categoria"
              :aria-selected="activa === categoria.id" @click="categoriaId = categoria.id; buscar = ''">
        {{ categoria.nombre }}
      </button>
    </div>

    <div class="productos" :class="`vista-${vista}`">
      <button v-for="producto in productos" :key="producto.id" type="button" class="producto"
              :disabled="producto.agotado" @click="elegir(producto)">
        <span v-if="conFoto" class="foto" aria-hidden="true">
          <img v-if="producto.imagen" :src="mediaUrl(producto.imagen)" alt="" loading="lazy">
          <span v-else class="inicial">{{ producto.nombre.charAt(0) }}</span>
        </span>
        <span class="nombre">{{ producto.nombre }}</span>
        <span class="precio">{{ producto.agotado ? 'Agotado' : formatMoney(producto.precio) }}<template v-if="producto.grupos?.length && !producto.agotado"> · con opciones</template></span>
        <span v-if="cantidades[producto.id]" class="en-carrito" :aria-label="`${cantidades[producto.id]} en la orden`">
          {{ cantidades[producto.id] }}
        </span>
      </button>
      <p v-if="!productos.length" class="empty">
        {{ buscar ? 'Ningún producto coincide con la búsqueda.' : 'Esta carta no tiene productos todavía.' }}
      </p>
    </div>
    <OpcionesProducto :producto="conOpciones" @close="conOpciones = null" @confirm="confirmar" />
    <OpcionesCombo :combo="combo" @close="combo = null" @confirm="confirmarCombo" />
  </section>
</template>

<style scoped>
.picker {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  min-width: 0;
  min-height: 0;
}

/* En pantallas angostas el buscador va en su propio renglón y las vistas debajo */
.barra {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.barra .input {
  flex: 1 1 12rem;
  min-width: 0;
}

.vistas {
  flex: none;
  display: flex;
  border: 1px solid var(--linea-fuerte);
  border-radius: var(--radio);
  background: var(--superficie);
  overflow: hidden;
}

.vista {
  display: grid;
  place-items: center;
  width: var(--toque);
  min-height: var(--toque);
  border: 0;
  border-left: 1px solid var(--linea);
  background: transparent;
  color: var(--acero);
  cursor: pointer;
}

.vista:first-child {
  border-left: 0;
}

.vista svg {
  width: 1.25rem;
  height: 1.25rem;
  fill: currentColor;
}

.vista[aria-pressed='true'] {
  background: var(--tinta);
  color: #fff;
}

.escaneado {
  margin-top: var(--space-1);
  color: var(--acero);
  font-size: var(--text-sm);
}

.categorias {
  display: flex;
  gap: var(--space-2);
  overflow-x: auto;
  padding-bottom: var(--space-1);
  scrollbar-width: thin;
}

.categoria {
  flex: none;
  min-height: var(--toque);
  padding: 0 var(--space-4);
  border: 1px solid var(--linea-fuerte);
  border-radius: 999px;
  background: var(--superficie);
  font-weight: 600;
  cursor: pointer;
}

.categoria[aria-selected='true'] {
  background: var(--tinta);
  border-color: var(--tinta);
  color: #fff;
}

.productos {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(9.5rem, 1fr));
  gap: var(--space-2);
  align-content: start;
}

.producto {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: var(--space-2);
  min-height: 5.5rem;
  padding: var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
  background: var(--superficie);
  text-align: left;
  cursor: pointer;
  touch-action: manipulation;
}

.producto:active {
  background: var(--accion-suave);
}

.producto:disabled {
  cursor: not-allowed;
  background: var(--fondo);
  color: var(--acero);
}

.nombre {
  font-weight: 600;
  line-height: 1.2;
}

.precio {
  color: var(--acero);
  font-size: var(--text-sm);
}

.en-carrito {
  position: absolute;
  top: -0.4rem;
  right: -0.4rem;
  min-width: 1.75rem;
  height: 1.75rem;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: var(--accion);
  color: #fff;
  font-weight: 700;
  font-size: var(--text-sm);
}

.empty {
  grid-column: 1 / -1;
}

/* Lista: solo texto, una fila por producto con el precio a la derecha */
.vista-lista {
  grid-template-columns: 1fr;
  gap: 0;
  border: 1px solid var(--linea);
  border-radius: var(--radio);
  background: var(--superficie);
}

.vista-lista .producto {
  flex-direction: row;
  align-items: center;
  min-height: var(--toque);
  padding: var(--space-2) var(--space-3);
  border: 0;
  border-top: 1px solid var(--linea);
  border-radius: 0;
}

.vista-lista .producto:first-child {
  border-top: 0;
}

.vista-lista .nombre {
  flex: 1 1 auto;
}

.vista-lista .precio {
  flex: none;
  text-align: right;
}

.vista-lista .en-carrito {
  position: static;
  flex: none;
}

/* Fotos: la imagen del producto arriba, en dos tamaños */
.vista-mediana {
  grid-template-columns: repeat(auto-fill, minmax(9.5rem, 1fr));
}

.vista-grande {
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 15rem), 1fr));
  gap: var(--space-3);
}

.vista-mediana .producto,
.vista-grande .producto {
  justify-content: flex-start;
  padding: 0 0 var(--space-3);
  overflow: hidden;
}

.vista-mediana .producto > :not(.foto, .en-carrito),
.vista-grande .producto > :not(.foto, .en-carrito) {
  padding: 0 var(--space-3);
}

/* El marco tiene siempre la misma proporción y la foto se recorta para llenarlo: con cualquier tamaño o
   forma de imagen, las tarjetas quedan parejas y el nombre y el precio a la misma altura */
.foto {
  position: relative;
  flex: none;
  display: block;
  width: 100%;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  background: var(--fondo);
  border-bottom: 1px solid var(--linea);
}

.foto img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.inicial {
  display: grid;
  place-items: center;
  height: 100%;
  color: var(--acero);
  font-size: var(--text-2xl);
  font-weight: 800;
  font-stretch: 70%;
}

.vista-grande .inicial {
  font-size: var(--text-3xl);
}

.vista-grande .nombre {
  font-size: var(--text-lg);
}

.producto:disabled .foto {
  opacity: 0.5;
}

.vista-mediana .en-carrito,
.vista-grande .en-carrito {
  top: var(--space-2);
  right: var(--space-2);
}
</style>
