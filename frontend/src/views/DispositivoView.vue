<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'

/*
  Tablet o pantalla compartida (doc 08, sección 2): se autoriza una vez con el código que da el
  administrador y después cada persona entra con su PIN. El PIN solo funciona aquí (RN-USR-03).
*/
const auth = useAuthStore()
const router = useRouter()

const info = ref(null)
const codigo = ref('')
const pin = ref('')
const error = ref('')
const busy = ref(false)

const emparejado = computed(() => !!auth.deviceToken && !!info.value)

async function cargarInfo() {
  if (!auth.deviceToken) return
  try {
    info.value = await postData('/dispositivo/info', { token: auth.deviceToken })
  } catch (e) {
    if (e.status === 401) auth.setDeviceToken(null)
    error.value = e.message
  }
}

async function emparejar() {
  error.value = ''
  busy.value = true
  try {
    const data = await postData('/dispositivo/emparejar', { codigo: codigo.value.trim() })
    auth.setDeviceToken(data.token)
    info.value = data
    codigo.value = ''
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

function tecla(valor) {
  error.value = ''
  if (valor === 'borrar') pin.value = pin.value.slice(0, -1)
  else if (pin.value.length < 6) pin.value += valor
}

async function entrar() {
  if (pin.value.length < 4 || busy.value) return
  busy.value = true
  error.value = ''
  try {
    await auth.loginWithPin(pin.value)
    const destino = auth.dispositivo?.tipo === 'produccion'
      ? { name: 'cocina-punto', params: { puntoId: auth.dispositivo.punto_produccion_id } }
      : { name: 'mesero' }
    router.replace(destino)
  } catch (e) {
    error.value = e.message
    if (e.status === 401) {
      auth.setDeviceToken(null)
      info.value = null
    }
  } finally {
    pin.value = ''
    busy.value = false
  }
}

function olvidar() {
  auth.setDeviceToken(null)
  info.value = null
}

onMounted(cargarInfo)
</script>

<template>
  <main class="dispositivo">
    <section v-if="emparejado" class="pin">
      <p class="lugar">{{ info.restaurante }} · {{ info.destino }}</p>
      <h1>{{ info.nombre }}</h1>
      <p class="instruccion">Escribe tu PIN</p>
      <div class="puntos" aria-hidden="true">
        <span v-for="i in 6" :key="i" :class="{ lleno: i <= pin.length, opcional: i > 4 }"></span>
      </div>
      <p class="visually-hidden" aria-live="polite">{{ pin.length }} números escritos</p>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <div class="teclado">
        <button v-for="n in ['1', '2', '3', '4', '5', '6', '7', '8', '9']" :key="n" type="button" :disabled="busy" @click="tecla(n)">{{ n }}</button>
        <button type="button" :disabled="busy || !pin" aria-label="Borrar" @click="tecla('borrar')">⌫</button>
        <button type="button" :disabled="busy" @click="tecla('0')">0</button>
        <button type="button" class="entrar" :disabled="busy || pin.length < 4" @click="entrar">Entrar</button>
      </div>
      <button class="olvidar" type="button" @click="olvidar">Este dispositivo ya no es del restaurante</button>
    </section>

    <form v-else class="emparejar" @submit.prevent="emparejar">
      <h1>Autorizar este dispositivo</h1>
      <p>El administrador crea el dispositivo en Administración → Dispositivos y te da un código de 6 números.</p>
      <label class="field">
        <span class="label">Código</span>
        <input v-model="codigo" class="input codigo" inputmode="numeric" maxlength="6" autocomplete="one-time-code" required>
      </label>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button class="btn btn-grande btn-bloque" type="submit" :disabled="busy || codigo.trim().length !== 6">Autorizar</button>
      <RouterLink :to="{ name: 'login' }" class="enlace">Entrar con usuario y clave</RouterLink>
    </form>
  </main>
</template>

<style scoped>
.dispositivo {
  min-height: 100dvh;
  display: grid;
  place-items: center;
  padding: var(--space-4);
  background: var(--tinta);
  color: #fff;
}

.pin,
.emparejar {
  width: min(24rem, 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  text-align: center;
}

.lugar {
  color: #aab4b8;
}

h1 {
  font-size: var(--text-3xl);
  font-stretch: 68%;
}

.instruccion {
  font-size: var(--text-lg);
}

.puntos {
  display: flex;
  gap: var(--space-3);
  margin: var(--space-2) 0;
}

.puntos span {
  width: 1rem;
  height: 1rem;
  border-radius: 50%;
  border: 2px solid #fff;
}

.puntos span.opcional {
  border-style: dashed;
  opacity: 0.6;
}

.puntos span.lleno {
  background: #fff;
  opacity: 1;
}

.teclado {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
  width: 100%;
}

.teclado button {
  min-height: 4.5rem;
  border: 1px solid #4a5458;
  border-radius: var(--radio);
  background: var(--tinta-suave);
  color: #fff;
  font-size: 1.75rem;
  font-weight: 600;
  cursor: pointer;
  touch-action: manipulation;
}

.teclado button:active {
  background: #3a4448;
}

.teclado .entrar {
  background: var(--accion);
  border-color: var(--accion);
  font-size: var(--text-lg);
}

.teclado button:disabled {
  opacity: 0.45;
}

.error {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radio-sm);
  background: var(--estado-cancelado);
  color: #fff;
}

.olvidar,
.enlace {
  margin-top: var(--space-4);
  border: none;
  background: none;
  color: #aab4b8;
  text-decoration: underline;
  font-size: var(--text-sm);
  cursor: pointer;
}

.emparejar {
  text-align: left;
  align-items: stretch;
}

.emparejar p {
  color: #cfd6d9;
}

.emparejar .label {
  color: #fff;
}

.codigo {
  font-size: var(--text-2xl);
  letter-spacing: 0.4em;
  text-align: center;
}
</style>
