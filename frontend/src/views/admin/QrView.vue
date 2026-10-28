<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'
import { usePrintStore } from '@/stores/print'
import AppModal from '@/components/AppModal.vue'

/*
  Códigos QR de las mesas (doc 10A): ver, imprimir y, si alguien abusa de uno, revocarlo y generar otro.
  El QR solo lleva un token opaco; la mesa no se puede cambiar editando el enlace.
*/
const { busy, attempt, quiet } = useAction()
const printer = usePrintStore()

const qrs = ref([])
const zonaId = ref('')
const revocar = ref(null)
const cargado = ref(false)

const zonas = computed(() => [...new Map(qrs.value.map((q) => [q.zona_id, q.zona])).entries()])
const visibles = computed(() => qrs.value.filter((q) => !zonaId.value || q.zona_id === Number(zonaId.value)))

async function load() {
  qrs.value = (await quiet(() => postData('/qr/list', { con_imagen: true }))) || []
  cargado.value = true
}

function imprimir(lista) {
  printer.print('qr', lista)
}

async function confirmarRevocar() {
  const qr = revocar.value
  const ok = await attempt(() => postData('/qr/regenerar', { mesa_id: qr.mesa_id }),
    { success: `QR de ${qr.mesa} regenerado. El anterior ya no funciona: imprime el nuevo.` })
  revocar.value = null
  if (ok) load()
}

onMounted(load)
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Códigos QR</h1>
        <p>Imprime el QR de cada mesa. Quien lo escanee verá la carta de esa zona.</p>
      </div>
      <div class="actions">
        <select v-model="zonaId" class="select" aria-label="Zona">
          <option value="">Todas las zonas</option>
          <option v-for="[id, nombre] in zonas" :key="id" :value="id">{{ nombre }}</option>
        </select>
        <button class="btn" type="button" :disabled="!visibles.length" @click="imprimir(visibles)">
          Imprimir {{ visibles.length }} QR
        </button>
      </div>
    </header>

    <div class="qrs">
      <article v-for="qr in visibles" :key="qr.id" class="qr panel">
        <div class="imagen" v-html="qr.svg"></div>
        <div class="datos">
          <strong>{{ qr.tipo === 'rapido' ? 'Para llevar' : qr.mesa }}</strong>
          <span class="muted">{{ qr.zona }}</span>
          <a :href="qr.url" target="_blank" rel="noopener" class="enlace">Abrir la carta</a>
        </div>
        <div class="actions">
          <button class="btn btn-secundario btn-sm" type="button" @click="imprimir([qr])">Imprimir</button>
          <button class="btn btn-secundario btn-sm" type="button" @click="revocar = qr">Revocar</button>
        </div>
      </article>
    </div>
    <p v-if="!cargado" class="empty">Cargando códigos…</p>
    <p v-else-if="!visibles.length" class="empty">Todavía no hay mesas. Crea mesas y sus QR aparecerán aquí.</p>

    <AppModal :open="!!revocar" :title="`Revocar el QR de ${revocar?.mesa}`" width="28rem" @close="revocar = null">
      <p>El QR impreso dejará de funcionar de inmediato y se genera uno nuevo. Úsalo si alguien está pidiendo con una foto del código desde fuera del local.</p>
      <div class="form-actions">
        <button class="btn btn-secundario" type="button" @click="revocar = null">Volver</button>
        <button class="btn btn-peligro" type="button" :disabled="busy" @click="confirmarRevocar">Revocar y generar otro</button>
      </div>
    </AppModal>
  </div>
</template>

<style scoped>
.qrs {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
  gap: var(--space-3);
}

.qr {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
}

.imagen :deep(svg) {
  width: 100%;
  max-width: 10rem;
  height: auto;
  display: block;
  margin: 0 auto;
}

.datos {
  display: flex;
  flex-direction: column;
}

.datos strong {
  font-size: var(--text-xl);
  font-stretch: 75%;
}

.enlace {
  font-size: var(--text-sm);
  color: var(--accion);
}
</style>
