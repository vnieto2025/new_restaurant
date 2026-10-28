<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { postData } from '@/services/api'
import { formatMoney, newKey } from '@/utils/format'

/*
  Pago desde el celular (doc 20A). Se llega con el QR de la mesa (?token), con el enlace del pedido
  (?seguimiento) o de vuelta de la pasarela (?pago). El resultado lo confirma la pasarela con su aviso
  firmado: esta pantalla solo consulta el estado, nunca decide si se pagó (RN-PAG-01).
*/
const route = useRoute()
const POLL_MS = 2000

const cuenta = ref(null)
const pago = ref(null)
const error = ref('')
const enviando = ref(false)
const opcion = ref('ninguna')
const otra = ref(null)
// Cupón: el servidor lo valida (RN-CUP-05); aquí solo se muestra el resultado
const codigo = ref('')
const cuponError = ref('')
const aplicando = ref(false)
// Una clave por visita: un doble toque o un reintento no crea dos cobros
let clave = newKey()
let timer = null

const origen = computed(() => (route.query.token ? { token: route.query.token } : { seguimiento: route.query.seguimiento }))
const sugerida = computed(() => cuenta.value ? Math.round((cuenta.value.saldo * (cuenta.value.propina_porcentaje || 0)) / 100) : 0)
const propina = computed(() => {
  if (!cuenta.value?.permitir_propina) return 0
  if (opcion.value === 'sugerida') return sugerida.value
  if (opcion.value === 'otra') return Math.max(Math.round(Number(otra.value) || 0), 0)
  return 0
})
const total = computed(() => (cuenta.value?.saldo || 0) + propina.value)

async function cargarCuenta() {
  try {
    cuenta.value = await postData('/publico/pago/cuenta', origen.value)
    error.value = ''
  } catch (e) {
    error.value = e.message
  }
}

async function consultarPago() {
  try {
    pago.value = await postData('/publico/pago/estado', { pago: route.query.pago })
    if (pago.value.estado !== 'pendiente') clearInterval(timer)
  } catch (e) {
    error.value = e.message
    clearInterval(timer)
  }
}

async function aplicarCupon() {
  aplicando.value = true
  cuponError.value = ''
  try {
    cuenta.value = await postData('/publico/pago/cupon', { ...origen.value, codigo: codigo.value.trim() })
    codigo.value = ''
  } catch (e) {
    cuponError.value = e.message
  } finally {
    aplicando.value = false
  }
}

async function pagar() {
  enviando.value = true
  error.value = ''
  try {
    const intento = await postData('/publico/pago/crear', { ...origen.value, propina: propina.value, clave_idempotencia: clave })
    // A la página segura de la pasarela: los datos de pago nunca pasan por el restaurante (RG-19)
    window.location.assign(intento.url)
  } catch (e) {
    error.value = e.message
    enviando.value = false
  }
}

function iniciar() {
  clearInterval(timer)
  cuenta.value = null
  pago.value = null
  error.value = ''
  enviando.value = false
  clave = newKey()
  if (route.query.pago) {
    consultarPago()
    timer = setInterval(consultarPago, POLL_MS)
  } else {
    cargarCuenta()
  }
}

onMounted(iniciar)
// "Intentar de nuevo" vuelve a esta misma pantalla con otros parámetros: se empieza de cero
watch(() => route.fullPath, iniciar)
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <div class="pagar">
    <header class="cabecera">
      <p class="lugar">{{ cuenta?.titulo || 'Tu cuenta' }}</p>
      <h1>{{ cuenta?.restaurante || pago?.restaurante || 'Pagar' }}</h1>
    </header>

    <main class="cuerpo">
      <p v-if="error" class="aviso" role="alert">{{ error }}</p>

      <!-- De vuelta de la pasarela -->
      <section v-if="pago" class="resultado" aria-live="polite">
        <template v-if="pago.estado === 'pendiente'">
          <p class="grande">Confirmando tu pago…</p>
          <p class="muted">Esperamos la respuesta de la pasarela. No cierres esta página.</p>
        </template>
        <template v-else-if="pago.estado === 'aprobado'">
          <p class="grande ok">Pago aprobado</p>
          <p>Pagaste {{ formatMoney(pago.monto) }}<template v-if="pago.propina"> con {{ formatMoney(pago.propina) }} de propina</template>. ¡Gracias!</p>
          <p v-if="pago.excedente" class="muted">Tu cuenta ya estaba paga o cambió: el restaurante te devolverá {{ formatMoney(pago.excedente) }}.</p>
          <p v-else-if="!pago.cuenta_pagada" class="muted">Se pidió algo más mientras pagabas: el resto se paga en caja.</p>
        </template>
        <template v-else>
          <p class="grande">{{ pago.estado === 'rechazado' ? 'El pago no fue aprobado' : 'El pago no se completó' }}</p>
          <p class="muted">No se hizo ningún cobro. Puedes intentar de nuevo o pagar en caja.</p>
        </template>
        <RouterLink v-if="pago.seguimiento" class="btn btn-secundario btn-bloque"
                    :to="pago.estado === 'aprobado' ? { name: 'seguimiento', params: { seguimiento: pago.seguimiento } } : { name: 'pagar', query: { seguimiento: pago.seguimiento } }">
          {{ pago.estado === 'aprobado' ? 'Ver mi pedido' : 'Intentar de nuevo' }}</RouterLink>
      </section>

      <!-- Cuenta por pagar -->
      <template v-else-if="cuenta">
        <p v-if="cuenta.estado === 'pagada'" class="resultado grande ok">Esta cuenta ya está pagada.</p>
        <p v-else-if="!cuenta.disponible" class="aviso">{{ cuenta.mensaje || 'No se puede pagar en línea en este momento. Paga en caja.' }}</p>

        <ul class="lineas">
          <li v-for="(l, i) in cuenta.lineas" :key="i">
            <span>{{ l.cantidad }} × {{ l.nombre }}<small v-if="l.modificadores.length">{{ l.modificadores.join(', ') }}</small></span>
            <span>{{ formatMoney(l.total) }}</span>
          </li>
        </ul>
        <dl class="totales">
          <div v-if="cuenta.descuento"><dt>Descuento</dt><dd>−{{ formatMoney(cuenta.descuento) }}</dd></div>
          <div v-for="c in cuenta.cupones.filter((x) => x.valor)" :key="c.codigo"><dt>Cupón {{ c.codigo }}</dt><dd>−{{ formatMoney(c.valor) }}</dd></div>
          <div v-if="cuenta.envio"><dt>Domicilio</dt><dd>{{ formatMoney(cuenta.envio) }}</dd></div>
          <div v-if="cuenta.propina"><dt>Propina</dt><dd>{{ formatMoney(cuenta.propina) }}</dd></div>
          <div v-if="cuenta.pagado"><dt>Ya pagado</dt><dd>−{{ formatMoney(cuenta.pagado) }}</dd></div>
          <div class="fuerte"><dt>Por pagar</dt><dd>{{ formatMoney(cuenta.saldo) }}</dd></div>
        </dl>

        <template v-if="cuenta.disponible">
          <form v-if="cuenta.acepta_cupones" class="cupon" @submit.prevent="aplicarCupon">
            <label for="cupon">¿Tienes un cupón?</label>
            <div class="fila">
              <input id="cupon" v-model="codigo" class="input" maxlength="30" autocomplete="off" placeholder="Código"
                     :aria-invalid="!!cuponError" aria-describedby="cupon-error">
              <button class="btn btn-secundario" type="submit" :disabled="aplicando || codigo.trim().length < 3">Aplicar</button>
            </div>
            <p id="cupon-error" class="cupon-error" role="alert">{{ cuponError }}</p>
            <p v-for="c in cuenta.cupones.filter((x) => x.nota)" :key="c.codigo" class="cupon-error">Cupón {{ c.codigo }}: {{ c.nota }}</p>
          </form>
          <fieldset v-if="cuenta.permitir_propina" class="propina">
            <legend>Propina voluntaria</legend>
            <div class="opciones">
              <button type="button" :aria-pressed="opcion === 'ninguna'" @click="opcion = 'ninguna'">Sin propina</button>
              <button v-if="sugerida" type="button" :aria-pressed="opcion === 'sugerida'" @click="opcion = 'sugerida'">
                {{ cuenta.propina_porcentaje }} % · {{ formatMoney(sugerida) }}</button>
              <button type="button" :aria-pressed="opcion === 'otra'" @click="opcion = 'otra'">Otro valor</button>
            </div>
            <input v-if="opcion === 'otra'" v-model.number="otra" class="input" type="number" min="0" inputmode="numeric"
                   aria-label="Valor de la propina">
          </fieldset>
          <button class="btn btn-grande btn-bloque" type="button" :disabled="enviando || total <= 0" :aria-busy="enviando" @click="pagar">
            {{ enviando ? 'Abriendo la pasarela…' : `Pagar ${formatMoney(total)}` }}</button>
          <p class="muted seguro">Pagas en la página segura de la pasarela. El restaurante nunca ve los datos de tu tarjeta.</p>
        </template>
        <p v-if="cuenta.ultimo_pago?.estado === 'pendiente'" class="muted">Tienes un pago en curso. Si ya lo terminaste, espera la confirmación.</p>
      </template>
    </main>
  </div>
</template>

<style scoped>
.pagar {
  min-height: 100dvh;
  background: var(--papel);
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

.cuerpo {
  max-width: 34rem;
  margin: 0 auto;
  padding: var(--space-5) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.aviso {
  padding: var(--space-3);
  border-left: 4px solid var(--estado-cancelado);
  border-radius: var(--radio-sm);
  background: var(--estado-cancelado-suave);
}

.lineas {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.lineas li {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
}

.lineas small {
  display: block;
  color: var(--acero);
}

.totales {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin: 0;
  padding-top: var(--space-3);
  border-top: 1px solid var(--linea);
}

.totales div {
  display: flex;
  justify-content: space-between;
}

.totales dd {
  margin: 0;
  font-variant-numeric: tabular-nums;
}

.totales .fuerte {
  font-size: var(--text-xl);
  font-weight: 700;
}

.propina {
  margin: 0;
  padding: 0;
  border: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.propina legend {
  font-weight: 700;
  margin-bottom: var(--space-2);
}

.opciones {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.opciones button {
  min-height: var(--toque);
  padding: 0 var(--space-3);
  border: 1px solid var(--linea);
  border-radius: 999px;
  background: var(--superficie);
  font-weight: 600;
  cursor: pointer;
}

.opciones [aria-pressed='true'] {
  border-color: var(--accion);
  background: var(--accion-suave);
}

.cupon {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.cupon label {
  font-weight: 700;
}

.cupon .fila {
  display: flex;
  gap: var(--space-2);
}

.cupon .input {
  flex: 1;
  min-width: 0;
  text-transform: uppercase;
}

.cupon-error {
  margin: 0;
  color: var(--estado-cancelado);
  font-weight: 600;
}

.cupon-error:empty {
  display: none;
}

.seguro {
  font-size: var(--text-sm);
  text-align: center;
}

.resultado {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  text-align: center;
}

.grande {
  font-size: var(--text-2xl);
  font-weight: 700;
}

.ok {
  color: var(--estado-entregado);
}
</style>
