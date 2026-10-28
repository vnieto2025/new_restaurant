<script setup>
import { ref, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'
import { useDraft } from '@/composables/useDraft'
import MenuPicker from '@/components/MenuPicker.vue'
import CartPanel from '@/components/CartPanel.vue'

/*
  Venta directa en caja (doc 20, sección 9; ADR-007): se eligen productos y se pasa a cobrar, sin mesas ni cocina.
  Funciona sin el módulo de pedidos. El cobro usa el mismo panel que las mesas.
*/
const props = defineProps({ turnoAbierto: { type: Boolean, default: false } })
const emit = defineEmits(['cobrar'])

const { busy, attempt, quiet } = useAction()
const draft = useDraft('venta-directa')
const carta = ref(null)
const nombre = ref('')

onMounted(async () => {
  carta.value = await quiet(() => postData('/pos/carta'))
})

async function cobrar() {
  const cuenta = await attempt(() => postData('/pos/vender', {
    clave_idempotencia: draft.draft.value.clave,
    cliente_nombre: nombre.value.trim() || null,
    items: draft.items(),
  }))
  if (!cuenta) return
  draft.clear()
  nombre.value = ''
  emit('cobrar', cuenta)
}
</script>

<template>
  <div class="venta">
    <MenuPicker :categorias="carta?.categorias || []" :cantidades="draft.cantidades.value" @add="draft.add" />
    <aside class="lado">
      <CartPanel :lineas="draft.lineas.value" titulo="Venta directa" @change="draft.change" @remove="draft.remove">
        <div v-if="draft.lineas.value.length" class="field">
          <label for="vd-nombre">Nombre del cliente</label>
          <input id="vd-nombre" v-model="nombre" class="input" maxlength="100" placeholder="Opcional">
        </div>
        <p v-if="!props.turnoAbierto" class="aviso">Abre el turno de caja para vender.</p>
        <button class="btn btn-grande btn-bloque" type="button" :disabled="busy || !draft.lineas.value.length || !props.turnoAbierto"
                :aria-busy="busy" @click="cobrar">{{ busy ? 'Registrando…' : 'Cobrar' }}</button>
      </CartPanel>
    </aside>
  </div>
</template>

<style scoped>
.venta {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(18rem, 24rem);
  gap: var(--space-4);
  align-items: start;
}

.lado {
  position: sticky;
  top: var(--space-4);
}

.aviso {
  padding: var(--space-2) var(--space-3);
  border: 2px dashed var(--tinta);
  border-radius: var(--radio-sm);
  font-size: var(--text-sm);
}

@media (max-width: 760px) {
  .venta {
    grid-template-columns: 1fr;
  }

  .lado {
    position: static;
  }
}
</style>
