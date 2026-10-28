<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import AppModal from '@/components/AppModal.vue'

// Trasladar, unir mesas y cambiar el mesero responsable (doc 10, sección 4)
const props = defineProps({
  mesaId: { type: Number, required: true },
  mesaNombre: { type: String, default: '' },
})
const emit = defineEmits(['changed'])

const auth = useAuthStore()
const router = useRouter()
const { busy, attempt, quiet } = useAction()

const accion = ref(null)
const mesas = ref([])
const meseros = ref([])
const destino = ref(null)
const otras = ref([])
const mesero = ref(null)

const libres = computed(() => mesas.value.filter((m) => m.id !== props.mesaId && m.estado === 'libre'))
const ocupadas = computed(() => mesas.value.filter((m) => m.id !== props.mesaId && m.sesion))

async function abrir(tipo) {
  accion.value = tipo
  destino.value = null
  otras.value = []
  mesero.value = null
  if (tipo === 'reasignar') meseros.value = (await quiet(() => postData('/mesa/meseros', { mesa_id: props.mesaId }))) || []
  else mesas.value = (await quiet(() => postData('/mesa/list'))) || []
}

async function confirmar() {
  let ok
  if (accion.value === 'trasladar') {
    ok = await attempt(() => postData('/mesa/trasladar', { mesa_id: props.mesaId, destino_id: destino.value }),
      { success: 'Mesa trasladada.' })
    if (ok) router.replace({ name: 'mesa', params: { mesaId: destino.value } })
  } else if (accion.value === 'unir') {
    ok = await attempt(() => postData('/mesa/unir', { mesa_id: props.mesaId, otras: otras.value }), { success: 'Mesas unidas.' })
  } else {
    ok = await attempt(() => postData('/mesa/reasignar', { mesa_id: props.mesaId, mesero_id: mesero.value }),
      { success: 'Mesero cambiado.' })
  }
  if (ok) {
    accion.value = null
    emit('changed')
  }
}

const TITULOS = {
  trasladar: 'Trasladar a otra mesa',
  unir: 'Unir mesas',
  reasignar: 'Cambiar el mesero',
}
</script>

<template>
  <div v-if="auth.can(['mesas.trasladar', 'mesas.reasignar'])" class="acciones">
    <button v-if="auth.can('mesas.trasladar')" class="btn btn-secundario btn-sm" type="button" @click="abrir('trasladar')">Trasladar</button>
    <button v-if="auth.can('mesas.trasladar')" class="btn btn-secundario btn-sm" type="button" @click="abrir('unir')">Unir mesas</button>
    <button v-if="auth.can('mesas.reasignar')" class="btn btn-secundario btn-sm" type="button" @click="abrir('reasignar')">Cambiar mesero</button>

    <AppModal :open="!!accion" :title="accion ? `${TITULOS[accion]}: ${mesaNombre}` : ''" width="30rem" @close="accion = null">
      <form v-if="accion" @submit.prevent="confirmar">
        <template v-if="accion === 'trasladar'">
          <p class="muted">Las órdenes, la cuenta y lo que está en cocina pasan a la mesa elegida.</p>
          <div class="opciones">
            <label v-for="m in libres" :key="m.id" class="check">
              <input v-model="destino" type="radio" :value="m.id" name="destino"> {{ m.nombre }}
            </label>
            <p v-if="!libres.length" class="muted">No hay mesas libres en tus zonas.</p>
          </div>
        </template>
        <template v-else-if="accion === 'unir'">
          <p class="muted">Lo pedido en las mesas elegidas pasa a {{ mesaNombre }} y se cobra en una sola cuenta.</p>
          <div class="opciones">
            <label v-for="m in ocupadas" :key="m.id" class="check">
              <input v-model="otras" type="checkbox" :value="m.id"> {{ m.nombre }}
            </label>
            <p v-if="!ocupadas.length" class="muted">No hay otras mesas ocupadas.</p>
          </div>
        </template>
        <template v-else>
          <div class="opciones">
            <label v-for="m in meseros" :key="m.id" class="check">
              <input v-model="mesero" type="radio" :value="m.id" name="mesero"> {{ m.nombre }}
            </label>
          </div>
        </template>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="accion = null">Cancelar</button>
          <button class="btn" type="submit" :aria-busy="busy"
                  :disabled="busy || (accion === 'trasladar' && !destino) || (accion === 'unir' && !otras.length) || (accion === 'reasignar' && !mesero)">
            Confirmar
          </button>
        </div>
      </form>
    </AppModal>
  </div>
</template>

<style scoped>
.acciones {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.opciones {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(8rem, 1fr));
  gap: var(--space-1) var(--space-3);
  margin-top: var(--space-3);
  max-height: 50dvh;
  overflow-y: auto;
}
</style>
