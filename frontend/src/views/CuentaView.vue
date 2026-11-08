<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { useToastStore } from '@/stores/toast'
import { formatDateTime } from '@/utils/format'

/*
  Mi cuenta: cambiar la clave y la verificación en dos pasos (ADR-054). Si la empresa la exige a los
  administradores y esta persona no la tiene, esta es la única pantalla disponible hasta activarla.
*/
const auth = useAuthStore()
const toast = useToastStore()
const { busy, attempt, quiet } = useAction()

const estado = ref(null)
// Activación: clave -> QR -> código -> códigos de respaldo
const paso = ref(null)
const clave = ref('')
const qr = ref(null)
const codigo = ref('')
const respaldo = ref(null)
// Desactivar o generar códigos nuevos
const gestion = ref(null)
const cambio = ref({ actual: '', nueva: '', repetida: '' })

const debeActivar = computed(() => auth.seguridad.debe_activar)

async function load() {
  estado.value = await quiet(() => postData('/auth/2fa/estado'))
}

async function iniciar() {
  const data = await attempt(() => postData('/auth/2fa/iniciar', { password: clave.value }))
  clave.value = ''
  if (data) {
    qr.value = data
    paso.value = 'codigo'
  }
}

async function activar() {
  const data = await attempt(() => postData('/auth/2fa/activar', { codigo: codigo.value.trim() }), { success: 'Verificación en dos pasos activa.' })
  codigo.value = ''
  if (data) {
    respaldo.value = data.codigos_respaldo
    paso.value = 'respaldo'
    qr.value = null
  }
}

async function terminar() {
  respaldo.value = null
  paso.value = null
  await Promise.all([load(), auth.refresh()])
}

async function gestionar() {
  const { accion, password, codigo: valor } = gestion.value
  if (accion === 'desactivar') {
    const ok = await attempt(() => postData('/auth/2fa/desactivar', { password, codigo: valor.trim() }),
      { success: 'Verificación en dos pasos desactivada.' })
    if (ok !== undefined) {
      gestion.value = null
      await Promise.all([load(), auth.refresh()])
    }
    return
  }
  const data = await attempt(() => postData('/auth/2fa/codigos', { codigo: valor.trim() }))
  if (data) {
    gestion.value = null
    respaldo.value = data.codigos_respaldo
    paso.value = 'respaldo'
  }
}

async function copiarCodigos() {
  try {
    await navigator.clipboard.writeText(respaldo.value.join('\n'))
    toast.success('Códigos copiados. Guárdalos fuera de este celular.')
  } catch {
    toast.error('El navegador no dejó copiar. Anótalos a mano.')
  }
}

async function cambiarClave() {
  if (cambio.value.nueva !== cambio.value.repetida) {
    toast.error('La clave nueva no coincide en los dos campos.')
    return
  }
  const ok = await attempt(() => postData('/auth/cambiar_password', {
    password_actual: cambio.value.actual, password_nueva: cambio.value.nueva,
  }), { success: 'Clave actualizada.' })
  if (ok !== undefined) cambio.value = { actual: '', nueva: '', repetida: '' }
}

onMounted(load)
</script>

<template>
  <main class="cuenta">
    <header class="cabeza">
      <div>
        <h1>Mi cuenta</h1>
        <p class="muted">{{ auth.user?.nombre }} · {{ auth.user?.usuario }}</p>
      </div>
      <RouterLink v-if="!debeActivar" class="btn btn-secundario" :to="{ name: 'inicio', query: { menu: 1 } }">Volver</RouterLink>
      <button v-else class="btn btn-secundario" type="button" @click="auth.logout()">Salir</button>
    </header>

    <p v-if="debeActivar" class="exigida" role="alert">
      <strong>Tu empresa exige la verificación en dos pasos a los administradores.</strong>
      Actívala para seguir usando el sistema; tarda un par de minutos.
    </p>

    <section class="panel bloque" aria-labelledby="dos-pasos">
      <h2 id="dos-pasos">Verificación en dos pasos</h2>
      <p class="muted">Además de tu clave, al entrar te pedimos un código que cambia cada 30 segundos en una aplicación
        de tu celular (Google Authenticator, Microsoft Authenticator o Authy). Si alguien consigue tu clave, sin tu celular no entra.</p>

      <template v-if="paso === 'respaldo'">
        <h3>Guarda tus códigos de respaldo</h3>
        <p>Sirven para entrar si pierdes o cambias el celular. Cada uno funciona una sola vez y <strong>no los vuelves a ver</strong>:
          anótalos o imprímelos y guárdalos fuera del celular.</p>
        <ol class="codigos">
          <li v-for="c in respaldo" :key="c"><code>{{ c }}</code></li>
        </ol>
        <div class="actions">
          <button class="btn btn-secundario" type="button" @click="copiarCodigos">Copiar</button>
          <button class="btn" type="button" @click="terminar">Ya los guardé</button>
        </div>
      </template>

      <template v-else-if="estado?.activo">
        <p class="activa"><strong>Activa</strong> desde {{ formatDateTime(estado.activo_en) }} ·
          {{ estado.codigos_restantes === 1 ? 'te queda 1 código de respaldo' : `te quedan ${estado.codigos_restantes} códigos de respaldo` }}</p>
        <p v-if="estado.codigos_restantes <= 3" class="aviso">Te quedan pocos códigos de respaldo: genera unos nuevos.</p>
        <form v-if="gestion" class="form-grid" @submit.prevent="gestionar">
          <div v-if="gestion.accion === 'desactivar'" class="field">
            <label for="g-clave">Tu clave</label>
            <input id="g-clave" v-model="gestion.password" class="input" type="password" autocomplete="current-password" required>
          </div>
          <div class="field">
            <label for="g-codigo">Código de la aplicación</label>
            <input id="g-codigo" v-model="gestion.codigo" class="input" inputmode="numeric" autocomplete="one-time-code" maxlength="12" required>
          </div>
          <div class="form-actions">
            <button class="btn btn-secundario" type="button" @click="gestion = null">Cancelar</button>
            <button class="btn" type="submit" :disabled="busy">{{ gestion.accion === 'desactivar' ? 'Desactivar' : 'Generar códigos' }}</button>
          </div>
        </form>
        <div v-else class="actions">
          <button class="btn btn-secundario" type="button" @click="gestion = { accion: 'codigos', codigo: '' }">Generar códigos de respaldo nuevos</button>
          <button v-if="!estado.exigido" class="btn btn-secundario" type="button"
                  @click="gestion = { accion: 'desactivar', password: '', codigo: '' }">Desactivar</button>
        </div>
        <p v-if="estado.exigido" class="muted">Tu empresa la exige: no se puede desactivar.</p>
      </template>

      <template v-else-if="paso === 'codigo' && qr">
        <ol class="pasos">
          <li>Abre la aplicación del celular y elige agregar una cuenta con código QR.</li>
          <li>Escanea este código:
            <!-- SVG generado por el servidor a partir del secreto: no trae nada del usuario -->
            <div class="qr" v-html="qr.qr_svg"></div>
            <p class="muted">¿No puedes escanear? Escribe esta clave en la aplicación: <code class="secreto">{{ qr.secreto }}</code></p>
          </li>
          <li>
            <form class="confirmar" @submit.prevent="activar">
              <label for="a-codigo">Escribe el código de 6 números que muestra la aplicación</label>
              <div class="fila">
                <input id="a-codigo" v-model="codigo" class="input" inputmode="numeric" autocomplete="one-time-code" maxlength="6" required>
                <button class="btn" type="submit" :disabled="busy" :aria-busy="busy">Activar</button>
              </div>
            </form>
          </li>
        </ol>
      </template>

      <form v-else-if="estado" class="confirmar" @submit.prevent="iniciar">
        <p v-if="estado.recomendado && !debeActivar" class="aviso">Recomendada para quien administra: tu cuenta puede cambiar precios, usuarios y la caja.</p>
        <label for="i-clave">Para empezar, escribe tu clave</label>
        <div class="fila">
          <input id="i-clave" v-model="clave" class="input" type="password" autocomplete="current-password" required>
          <button class="btn" type="submit" :disabled="busy" :aria-busy="busy">Activar verificación</button>
        </div>
      </form>
    </section>

    <section v-if="!debeActivar" class="panel bloque" aria-labelledby="cambiar-clave">
      <h2 id="cambiar-clave">Cambiar la clave</h2>
      <form class="form-grid" @submit.prevent="cambiarClave">
        <div class="field">
          <label for="c-actual">Clave actual</label>
          <input id="c-actual" v-model="cambio.actual" class="input" type="password" autocomplete="current-password" required>
        </div>
        <div class="field">
          <label for="c-nueva">Clave nueva</label>
          <input id="c-nueva" v-model="cambio.nueva" class="input" type="password" autocomplete="new-password" minlength="8" required>
          <span class="hint">Mínimo 8 caracteres.</span>
        </div>
        <div class="field">
          <label for="c-repetida">Repite la clave nueva</label>
          <input id="c-repetida" v-model="cambio.repetida" class="input" type="password" autocomplete="new-password" minlength="8" required>
        </div>
        <div class="form-actions">
          <button class="btn" type="submit" :disabled="busy">Cambiar clave</button>
        </div>
      </form>
    </section>
  </main>
</template>

<style scoped>
.cuenta {
  width: min(48rem, 100%);
  margin: 0 auto;
  padding: var(--space-5) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.cabeza {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-3);
}

h1 {
  font-size: var(--text-3xl);
  font-stretch: 70%;
}

.bloque {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
}

h2 {
  font-size: var(--text-lg);
}

h3 {
  font-size: var(--text-base);
}

.exigida {
  padding: var(--space-3) var(--space-4);
  border: 2px solid var(--tinta);
  border-radius: var(--radio);
  background: var(--superficie);
}

.aviso {
  padding: var(--space-2) var(--space-3);
  border-left: 4px solid var(--linea-fuerte);
  background: var(--papel);
}

.pasos {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding-left: var(--space-5);
}

.qr {
  width: fit-content;
  margin: var(--space-2) 0;
  padding: var(--space-2);
  background: #fff;
  border: 1px solid var(--linea);
  border-radius: var(--radio-sm);
}

.qr :deep(svg) {
  display: block;
  max-width: 100%;
  height: auto;
}

.secreto,
.codigos code {
  font-family: var(--font-papel);
  letter-spacing: 0.08em;
  overflow-wrap: anywhere;
}

.confirmar {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.fila {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.fila .input {
  flex: 1 1 12rem;
  max-width: 20rem;
}

.codigos {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr));
  gap: var(--space-2) var(--space-4);
  padding-left: var(--space-5);
  font-size: var(--text-lg);
}
</style>
