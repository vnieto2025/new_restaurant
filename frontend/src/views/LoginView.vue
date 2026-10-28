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

async function submit() {
  error.value = ''
  busy.value = true
  try {
    await auth.login(usuario.value.trim(), password.value)
    router.replace(route.query.redirect || { name: 'inicio' })
  } catch (e) {
    error.value = e.message
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

      <div class="field">
        <label for="usuario">Usuario</label>
        <input id="usuario" v-model="usuario" class="input" autocomplete="username" autocapitalize="none"
               spellcheck="false" required>
      </div>
      <div class="field">
        <label for="password">Clave</label>
        <input id="password" v-model="password" class="input" type="password" autocomplete="current-password" required>
      </div>

      <p v-if="error" class="error" role="alert">{{ error }}</p>

      <button class="btn btn-grande btn-bloque" type="submit" :disabled="busy" :aria-busy="busy">
        {{ busy ? 'Ingresando…' : 'Ingresar' }}
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
