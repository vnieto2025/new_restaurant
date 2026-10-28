<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { postData } from '@/services/api'
import { formatMoney } from '@/utils/format'

/*
  Página de pago de la pasarela simulada (solo ambiente de pruebas). Hace el papel de la página segura
  de una pasarela real: aquí se "paga" y la pasarela avisa el resultado al sistema con un webhook firmado.
*/
const props = defineProps({ referencia: { type: String, required: true } })
const router = useRouter()

const pago = ref(null)
const error = ref('')
const enviando = ref(false)

onMounted(async () => {
  try {
    pago.value = await postData('/publico/pasarela/ver', { referencia: props.referencia })
  } catch (e) {
    error.value = e.message
  }
})

async function responder(decision) {
  enviando.value = true
  try {
    const respuesta = await postData('/publico/pasarela/responder', { referencia: props.referencia, decision })
    // Como una pasarela real: vuelve al restaurante, que consulta el estado confirmado
    router.replace({ name: 'pagar', query: { pago: respuesta.pago } })
  } catch (e) {
    error.value = e.message
    enviando.value = false
  }
}
</script>

<template>
  <div class="pasarela">
    <main class="caja">
      <p class="marca">Pasarela de pruebas</p>
      <p class="aviso-pruebas">Ambiente de pruebas: no se cobra dinero real.</p>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <template v-if="pago">
        <p class="muted">Pago a</p>
        <h1>{{ pago.restaurante }}</h1>
        <p class="monto">{{ formatMoney(pago.monto) }}</p>
        <p class="muted">Referencia {{ pago.referencia }}</p>
        <template v-if="pago.estado === 'pendiente'">
          <button class="btn btn-grande btn-bloque" type="button" :disabled="enviando" @click="responder('aprobar')">Aprobar pago</button>
          <button class="btn btn-secundario btn-bloque" type="button" :disabled="enviando" @click="responder('rechazar')">Rechazar pago</button>
        </template>
        <button v-else class="btn btn-secundario btn-bloque" type="button" @click="router.replace({ name: 'pagar', query: { pago: pago.pago } })">
          Volver al restaurante</button>
      </template>
    </main>
  </div>
</template>

<style scoped>
.pasarela {
  min-height: 100dvh;
  display: grid;
  place-items: center;
  padding: var(--space-4);
  background: #e8edf2;
}

.caja {
  width: min(100%, 26rem);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-5);
  border-radius: var(--radio);
  background: #fff;
  box-shadow: 0 8px 30px rgb(0 0 0 / 0.08);
  text-align: center;
}

.marca {
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #2b4c7e;
}

.aviso-pruebas {
  padding: var(--space-2);
  border-radius: var(--radio-sm);
  background: #fff4cc;
  font-size: var(--text-sm);
}

h1 {
  font-size: var(--text-2xl);
}

.monto {
  font-size: var(--text-3xl);
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.error {
  color: var(--estado-cancelado);
}
</style>
