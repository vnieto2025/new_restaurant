<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { formatDateTime, plural } from '@/utils/format'
import AppModal from '@/components/AppModal.vue'

/*
  Restaurante de práctica (ADR-053): una copia de la carta, las mesas y el inventario para entrenar al
  personal y hacer el ensayo en vacío sin que nada quede en los reportes ni en la caja del real.
*/
const auth = useAuthStore()
const router = useRouter()
const { busy, attempt, quiet } = useAction()

const estado = ref(null)
const confirmando = ref(false)

const NOMBRES = { facturacion: 'facturación electrónica', pagos_linea: 'pagos en línea' }

async function load() {
  estado.value = await quiet(() => postData('/practica/estado'))
}

async function crear() {
  const data = await attempt(() => postData('/practica/crear'), { success: 'Restaurante de práctica listo.' })
  if (data) {
    estado.value = data
    await auth.refresh()
  }
}

async function reiniciar() {
  const data = await attempt(() => postData('/practica/reiniciar'), { success: 'Práctica reiniciada.' })
  confirmando.value = false
  if (data) estado.value = data
}

async function entrar() {
  const ok = await attempt(() => auth.changeRestaurant(estado.value.practica.id), { success: 'Estás en el restaurante de práctica.' })
  if (ok !== undefined) router.push({ name: 'inicio', query: { menu: 1 } })
}

onMounted(load)
</script>

<template>
  <section v-if="estado" class="panel practica" aria-labelledby="practica-titulo">
    <h2 id="practica-titulo">Restaurante de práctica</h2>
    <p class="muted">
      Una copia de la carta, las mesas, los puntos de producción y el inventario. El personal entra con su mismo usuario
      a tomar órdenes, cocinar, cobrar y cerrar la jornada; nada cuenta en el restaurante real.
      <template v-if="estado.sin_modulos.length"> Allí no hay {{ estado.sin_modulos.map((m) => NOMBRES[m] || m).join(' ni ') }}.</template>
    </p>

    <template v-if="estado.practica">
      <p class="dato">
        <strong>{{ estado.practica.nombre }}</strong>
        <span class="muted"> · creada {{ formatDateTime(estado.practica.creada_en) }} · {{ plural(estado.practica.ordenes, 'orden', 'órdenes') }} de práctica</span>
      </p>
      <div class="actions">
        <button v-if="!estado.en_practica" class="btn" type="button" :disabled="busy" @click="entrar">Entrar a la práctica</button>
        <button class="btn btn-secundario" type="button" :disabled="busy" @click="confirmando = true">Reiniciar práctica</button>
      </div>
    </template>
    <div v-else class="actions">
      <button class="btn" type="button" :disabled="busy" :aria-busy="busy" @click="crear">Crear restaurante de práctica</button>
    </div>

    <AppModal :open="confirmando" title="¿Reiniciar la práctica?" width="30rem" @close="confirmando = false">
      <p>Se borran las órdenes, cobros, turnos y clientes de la práctica, y se copia de nuevo lo que tiene hoy
        {{ estado.real.nombre }}: carta, mesas e inventario.</p>
      <p class="muted">El restaurante real no se toca. Quien esté practicando debe salir y volver a entrar a la práctica.</p>
      <div class="form-actions">
        <button class="btn btn-secundario" type="button" @click="confirmando = false">Cancelar</button>
        <button class="btn" type="button" :disabled="busy" :aria-busy="busy" @click="reiniciar">Reiniciar</button>
      </div>
    </AppModal>
  </section>
</template>

<style scoped>
.practica {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
}

h2 {
  font-size: var(--text-lg);
}
</style>
