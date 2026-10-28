<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { postData } from '@/services/api'
import { useDraft } from '@/composables/useDraft'
import { useAction } from '@/composables/useAction'
import { formatMoney } from '@/utils/format'
import OpcionesProducto from '@/components/OpcionesProducto.vue'

/*
  Carta digital del cliente (doc 11 y 10A): ligera, cero registro, contexto fijado por el token.
  Pide nombre solo en "para llevar".
*/
const props = defineProps({ token: { type: String, required: true } })

const router = useRouter()
const { busy, attempt } = useAction()
const draft = useDraft(`qr:${props.token}`)
const STORAGE = `carta.${props.token}`

const carta = ref(null)
const error = ref('')
const verPedido = ref(false)
const conOpciones = ref(null)

const piezas = computed(() => draft.lineas.value.reduce((s, l) => s + l.cantidad, 0))
const total = computed(() => draft.lineas.value.reduce((s, l) => s + l.precio * l.cantidad, 0))
const misPedidos = ref([])

function restore() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE) || 'null')
    if (saved?.draft) Object.assign(draft.draft.value, saved.draft)
    misPedidos.value = saved?.pedidos || []
  } catch {
    // Sin almacenamiento el carrito dura mientras la página esté abierta
  }
}

function persist() {
  try {
    localStorage.setItem(STORAGE, JSON.stringify({ draft: draft.draft.value, pedidos: misPedidos.value.slice(-5) }))
  } catch {
    // Sin almacenamiento no se recuerda el carrito
  }
}

watch(() => draft.draft.value, persist, { deep: true })

async function load() {
  try {
    carta.value = await postData('/publico/qr', { token: props.token })
    error.value = ''
  } catch (e) {
    error.value = e.message
  }
}

function cantidad(producto) {
  return draft.cantidades.value[producto.id] || 0
}

function quitarUno(producto) {
  const linea = [...draft.lineas.value].reverse().find((l) => l.producto_id === producto.id)
  if (!linea) return
  if (linea.cantidad > 1) draft.change({ ...linea, cantidad: linea.cantidad - 1 })
  else draft.remove(linea)
}

function agregar(producto) {
  if (producto.grupos?.length) conOpciones.value = producto
  else draft.add(producto)
}

function confirmarOpciones(opciones) {
  draft.add(conOpciones.value, opciones)
  conOpciones.value = null
}

function saltar(categoria) {
  document.getElementById(`cat-${categoria.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function enviar() {
  if (draft.draft.value.cliente_telefono?.trim() && !draft.draft.value.acepta_datos) {
    error.value = 'Para dejar tu celular debes aceptar el aviso de datos, o déjalo vacío.'
    return
  }
  if (carta.value.pide_nombre && !draft.draft.value.cliente_nombre.trim()) {
    error.value = 'Escribe tu nombre para que te llamemos cuando esté listo.'
    return
  }
  error.value = ''
  const pedido = await attempt(() => postData('/publico/orden/create', {
    token: props.token,
    clave_idempotencia: draft.draft.value.clave,
    cliente_nombre: draft.draft.value.cliente_nombre.trim() || null,
    cliente_telefono: draft.draft.value.cliente_telefono?.trim() || null,
    acepta_datos: !!draft.draft.value.acepta_datos,
    notas: draft.draft.value.notas.trim() || null,
    items: draft.items(),
  }))
  if (!pedido) {
    load()
    return
  }
  misPedidos.value = [...misPedidos.value, pedido.seguimiento]
  draft.clear()
  persist()
  router.push({ name: 'seguimiento', params: { seguimiento: pedido.seguimiento }, query: { q: props.token } })
}

onMounted(() => {
  restore()
  load()
})
</script>

<template>
  <div class="carta">
    <header class="cabecera">
      <p v-if="carta" class="lugar">{{ carta.tipo === 'mesa' ? `${carta.zona} · ${carta.mesa}` : carta.mesa }}</p>
      <h1>{{ carta?.restaurante || 'Carta' }}</h1>
      <RouterLink v-if="misPedidos.length" class="mis-pedidos"
                  :to="{ name: 'seguimiento', params: { seguimiento: misPedidos[misPedidos.length - 1] }, query: { q: token } }">
        Ver mi último pedido
      </RouterLink>
      <RouterLink v-if="carta?.pago_en_linea" class="mis-pedidos" :to="{ name: 'pagar', query: { token } }">Pagar la cuenta</RouterLink>
    </header>

    <p v-if="error && !carta" class="cerrado">{{ error }}</p>
    <p v-else-if="carta && !carta.disponible" class="cerrado">{{ carta.mensaje }}</p>

    <template v-if="carta?.disponible">
      <nav class="saltos" aria-label="Categorías">
        <button v-for="categoria in carta.categorias" :key="categoria.id" type="button" @click="saltar(categoria)">
          {{ categoria.nombre }}
        </button>
      </nav>

      <main class="secciones">
        <p v-if="!carta.categorias.length" class="cerrado">La carta todavía no tiene productos.</p>
        <section v-for="categoria in carta.categorias" :id="`cat-${categoria.id}`" :key="categoria.id" class="seccion">
          <h2>{{ categoria.nombre }}</h2>
          <ul>
            <li v-for="producto in categoria.productos" :key="producto.id" class="producto" :class="{ agotado: producto.agotado }">
              <div class="info">
                <span class="nombre">{{ producto.nombre }}</span>
                <span v-if="producto.descripcion" class="desc">{{ producto.descripcion }}</span>
                <span v-if="producto.grupos?.length && !producto.agotado" class="desc">Puedes elegir: {{ producto.grupos.map((g) => g.nombre.toLowerCase()).join(', ') }}</span>
                <span class="precio">{{ producto.agotado ? 'Agotado por hoy' : formatMoney(producto.precio) }}</span>
              </div>
              <div v-if="!producto.agotado" class="control">
                <template v-if="cantidad(producto)">
                  <button type="button" :aria-label="`Uno menos de ${producto.nombre}`" @click="quitarUno(producto)">−</button>
                  <span class="cuantos">{{ cantidad(producto) }}</span>
                </template>
                <button type="button" class="mas" :aria-label="`Agregar ${producto.nombre}`" @click="agregar(producto)">+</button>
              </div>
            </li>
          </ul>
        </section>
      </main>

      <OpcionesProducto :producto="conOpciones" @close="conOpciones = null" @confirm="confirmarOpciones" />

      <button v-if="piezas" class="carrito" type="button" @click="verPedido = true">
        <span>Ver pedido ({{ piezas }})</span>
        <strong>{{ formatMoney(total) }}</strong>
      </button>

      <div v-if="verPedido" class="hoja-fondo" @click.self="verPedido = false">
        <section class="hoja" role="dialog" aria-modal="true" aria-labelledby="titulo-pedido">
          <header class="hoja-head">
            <h2 id="titulo-pedido">Tu pedido</h2>
            <button type="button" class="cerrar" aria-label="Seguir viendo la carta" @click="verPedido = false">×</button>
          </header>
          <ul class="lineas">
            <li v-for="linea in draft.lineas.value" :key="linea.uid">
              <div class="linea-fila">
                <span>{{ linea.cantidad }} × {{ linea.nombre }}<small v-if="linea.modificadores?.length" class="mods">{{ linea.modificadores.map((m) => m.nombre).join(', ') }}</small></span>
                <span>{{ formatMoney(linea.precio * linea.cantidad) }}</span>
              </div>
              <input class="input" :value="linea.nota" maxlength="200" placeholder="¿Alguna indicación? Sin cebolla…"
                     :aria-label="`Indicación para ${linea.nombre}`"
                     @input="draft.change({ ...linea, nota: $event.target.value })">
            </li>
          </ul>
          <template v-if="carta.pide_nombre">
            <div class="field">
              <label for="nombre">Tu nombre</label>
              <input id="nombre" v-model="draft.draft.value.cliente_nombre" class="input" maxlength="100" autocomplete="given-name">
            </div>
            <div class="field">
              <label for="telefono">Tu celular (opcional)</label>
              <input id="telefono" v-model="draft.draft.value.cliente_telefono" class="input" type="tel" inputmode="tel" autocomplete="tel">
            </div>
            <div v-if="draft.draft.value.cliente_telefono" class="aviso-datos">
              <p>{{ carta.aviso_datos }} <a v-if="carta.politica_url" :href="carta.politica_url" target="_blank" rel="noopener">Política de datos</a></p>
              <label class="check"><input v-model="draft.draft.value.acepta_datos" type="checkbox"> Acepto</label>
            </div>
          </template>
          <p class="total"><span>Total</span><strong>{{ formatMoney(total) }}</strong></p>
          <p v-if="carta.con_aprobacion" class="muted nota">El mesero confirmará tu pedido antes de prepararlo.</p>
          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <button class="btn btn-grande btn-bloque" type="button" :disabled="busy" :aria-busy="busy" @click="enviar">
            {{ busy ? 'Enviando…' : 'Enviar pedido' }}
          </button>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.carta {
  min-height: 100dvh;
  background: var(--papel);
  padding-bottom: 6rem;
}

.cabecera {
  padding: var(--space-6) var(--space-4) var(--space-4);
  background: var(--tinta);
  color: #fff;
}

.lugar {
  color: #c4ccd0;
  font-weight: 600;
}

.cabecera h1 {
  font-size: var(--text-3xl);
  font-stretch: 68%;
  line-height: 1;
  margin-top: var(--space-1);
}

.mis-pedidos {
  display: inline-block;
  margin-top: var(--space-3);
  color: #fff;
}

.cerrado {
  margin: var(--space-6) var(--space-4);
  padding: var(--space-5);
  border-radius: var(--radio);
  background: var(--superficie);
  border: 1px solid var(--linea);
  font-size: var(--text-lg);
  text-align: center;
}

.saltos {
  position: sticky;
  top: 0;
  z-index: 5;
  display: flex;
  gap: var(--space-2);
  overflow-x: auto;
  padding: var(--space-3) var(--space-4);
  background: var(--papel);
  border-bottom: 1px solid var(--linea);
}

.saltos button {
  flex: none;
  min-height: 2.75rem;
  padding: 0 var(--space-4);
  border: 1px solid var(--linea-fuerte);
  border-radius: 999px;
  background: var(--superficie);
  font-weight: 600;
  cursor: pointer;
}

.secciones {
  max-width: 40rem;
  margin: 0 auto;
  padding: 0 var(--space-4);
}

.seccion {
  scroll-margin-top: 4rem;
  padding-top: var(--space-5);
}

.seccion h2 {
  font-size: var(--text-xl);
  font-stretch: 75%;
  padding-bottom: var(--space-2);
  border-bottom: 2px solid var(--tinta);
}

.seccion ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.producto {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) 0;
  border-bottom: 1px dashed var(--linea-fuerte);
}

.info {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.nombre {
  font-weight: 600;
  font-size: var(--text-lg);
}

.desc {
  color: var(--acero);
  font-size: var(--text-sm);
}

.precio {
  margin-top: var(--space-1);
  font-weight: 600;
}

.agotado .nombre,
.agotado .precio {
  color: var(--acero);
}

.control {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.control button {
  width: var(--toque);
  height: var(--toque);
  border: 1px solid var(--linea-fuerte);
  border-radius: 50%;
  background: var(--superficie);
  font-size: 1.5rem;
  cursor: pointer;
  touch-action: manipulation;
}

.control .mas {
  background: var(--accion);
  border-color: var(--accion);
  color: #fff;
}

.cuantos {
  min-width: 1.5ch;
  text-align: center;
  font-weight: 700;
  font-size: var(--text-lg);
}

.carrito {
  position: fixed;
  inset: auto var(--space-3) calc(var(--space-3) + env(safe-area-inset-bottom)) var(--space-3);
  z-index: 10;
  max-width: 40rem;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: var(--toque-grande);
  padding: 0 var(--space-5);
  border: none;
  border-radius: var(--radio);
  background: var(--accion);
  color: #fff;
  font-size: var(--text-lg);
  cursor: pointer;
}

.hoja-fondo {
  position: fixed;
  inset: 0;
  z-index: 30;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  background: rgba(28, 34, 37, 0.5);
}

.hoja {
  width: min(40rem, 100%);
  max-height: 90dvh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-5) var(--space-4) calc(var(--space-5) + env(safe-area-inset-bottom));
  border-radius: var(--radio) var(--radio) 0 0;
  background: var(--superficie);
}

.hoja-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.cerrar {
  width: var(--toque);
  height: var(--toque);
  border: none;
  background: transparent;
  font-size: 1.75rem;
  cursor: pointer;
}

.lineas {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.lineas li {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.linea-fila {
  display: flex;
  justify-content: space-between;
  gap: var(--space-2);
  font-weight: 600;
}

.mods {
  display: block;
  color: var(--acero);
  font-weight: 400;
  font-size: var(--text-sm);
}

.aviso-datos {
  padding: var(--space-3);
  border-radius: var(--radio-sm);
  background: var(--fondo);
  font-size: var(--text-sm);
}

.total {
  display: flex;
  justify-content: space-between;
  font-size: var(--text-lg);
}

.nota {
  font-size: var(--text-sm);
}

.error {
  padding: var(--space-3);
  border-radius: var(--radio-sm);
  background: var(--estado-cancelado-suave);
  color: #7a1f19;
}
</style>
