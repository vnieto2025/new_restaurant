<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const usuario = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)
// Segundo paso: la clave fue correcta y la cuenta tiene verificación en dos pasos (ADR-054)
const pideCodigo = ref(false)
const codigo = ref('')

async function submit() {
  error.value = ''
  busy.value = true
  try {
    const data = await auth.login(usuario.value.trim(), password.value, pideCodigo.value ? codigo.value.trim() : null)
    if (data.requiere_codigo) {
      pideCodigo.value = true
      return
    }
    router.replace(route.query.redirect || { name: 'inicio' })
  } catch (e) {
    error.value = e.message
    codigo.value = ''
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="login">
    <form class="card" @submit.prevent="submit">
      <h1>Ingresar</h1>
      <p class="muted">Usa el usuario y la clave que te dio el administrador del restaurante.</p>

      <template v-if="!pideCodigo">
      <div class="field">
        <label for="usuario">Usuario</label>
        <input id="usuario" v-model="usuario" class="input" autocomplete="username" autocapitalize="none"
               spellcheck="false" required>
      </div>
      <div class="field">
        <label for="password">Clave</label>
        <input id="password" v-model="password" class="input" type="password" autocomplete="current-password" required>
      </div>
      </template>
      <template v-else>
        <div class="field">
          <label for="codigo">Código de verificación</label>
          <input id="codigo" v-model="codigo" class="input" inputmode="numeric" autocomplete="one-time-code"
                 autocapitalize="characters" spellcheck="false" maxlength="12" required autofocus>
          <span class="hint">El de 6 números que muestra tu aplicación, o uno de tus códigos de respaldo.</span>
        </div>
        <button class="otro enlace-boton" type="button" @click="pideCodigo = false; codigo = ''; error = ''">Volver a usuario y clave</button>
      </template>

      <p v-if="error" class="error" role="alert">{{ error }}</p>

      <button class="btn btn-grande btn-bloque" type="submit" :disabled="busy" :aria-busy="busy">
        {{ busy ? 'Ingresando…' : pideCodigo ? 'Verificar' : 'Ingresar' }}
      </button>
      <RouterLink :to="{ name: 'dispositivo' }" class="otro">Es una tablet o pantalla del restaurante: entrar con PIN</RouterLink>
    </form>
  </main>
</template>

<style scoped>
.login {
  min-height: 100dvh;
  display: grid;
  place-items: center;
  padding: var(--space-4);
  background:
    repeating-linear-gradient(90deg, transparent 0 39px, rgba(28, 34, 37, 0.035) 39px 40px),
    var(--fondo);
}

.card {
  width: min(24rem, 100%);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-6) var(--space-5);
  background: var(--superficie);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
}

h1 {
  font-size: var(--text-3xl);
  font-stretch: 70%;
}

.enlace-boton {
  border: 0;
  background: none;
  font: inherit;
  cursor: pointer;
}

.otro {
  color: var(--acero);
  font-size: var(--text-sm);
  text-align: center;
}

.error {
  padding: var(--space-3);
  border-radius: var(--radio-sm);
  background: var(--estado-cancelado-suave);
  color: #7a1f19;
  font-size: var(--text-sm);
}
</style>
