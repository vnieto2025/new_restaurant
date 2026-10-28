<script setup>
import { ref, computed } from 'vue'
import { formatMoney } from '@/utils/format'
import OpcionesProducto from '@/components/OpcionesProducto.vue'

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
const buscar = ref('')

// Un toque agrega; si el producto tiene modificadores, primero se eligen
function elegir(producto) {
  if (producto.grupos?.length) conOpciones.value = producto
  else emit('add', producto, [])
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
    return props.categorias.flatMap((c) => c.productos).filter((p) => normalize(p.nombre).includes(texto))
  }
  const categoria = props.categorias.find((c) => c.id === categoriaId.value) || props.categorias[0]
  return categoria ? categoria.productos : []
})

const activa = computed(() => (buscar.value.trim() ? null : categoriaId.value ?? props.categorias[0]?.id))
</script>

<template>
  <section class="picker">
    <div class="buscar">
      <input v-model="buscar" class="input" type="search" placeholder="Buscar producto" aria-label="Buscar producto">
    </div>

    <div class="categorias" role="tablist" aria-label="Categorías">
      <button v-for="categoria in categorias" :key="categoria.id" role="tab" type="button" class="categoria"
              :aria-selected="activa === categoria.id" @click="categoriaId = categoria.id; buscar = ''">
        {{ categoria.nombre }}
      </button>
    </div>

    <div class="productos">
      <button v-for="producto in productos" :key="producto.id" type="button" class="producto"
              :disabled="producto.agotado" @click="elegir(producto)">
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
</style>
