<script setup>
import { ref, computed } from 'vue'
import { post } from '@/services/api'
import { useAction } from '@/composables/useAction'
import { formatMoney } from '@/utils/format'
import { formatCantidad } from '@/utils/inventario'
import AppModal from '@/components/AppModal.vue'

/*
  Recepción de mercancía (doc 23, sección 4): se confirma cuánto llegó de cada insumo, que puede
  diferir de lo pedido. Lo que falta queda pendiente en la compra (RN-COM-02).
*/
const props = defineProps({
  compra: { type: Object, required: true },
})
const emit = defineEmits(['close', 'done'])

const { busy, attempt } = useAction()

const lineas = ref(props.compra.lineas.filter((l) => l.pendiente > 0).map((l) => ({
  ...l, llego: l.pendiente, precio: l.precio_unitario, novedad: '',
})))
const notas = ref('')
const factura = ref(props.compra.factura_proveedor || '')

const valor = computed(() => lineas.value.reduce((s, l) => s + Math.round((Number(l.llego) || 0) * (Number(l.precio) || 0)), 0))
const algo = computed(() => lineas.value.some((l) => Number(l.llego) > 0))
const faltantes = computed(() => lineas.value.filter((l) => (Number(l.llego) || 0) < l.pendiente).length)

function medida(l) {
  return l.presentacion || l.unidad
}

async function recibir() {
  const body = {
    compra_id: props.compra.id, notas: notas.value.trim() || null, factura_proveedor: factura.value.trim() || null,
    lineas: lineas.value.map((l) => ({
      compra_linea_id: l.id, cantidad: Number(l.llego) || 0, novedad: l.novedad.trim() || null,
      ...(l.cantidad_recibida === 0 && Number(l.precio) !== l.precio_unitario ? { precio_unitario: Number(l.precio) } : {}),
    })),
  }
  const json = await attempt(() => post('/compra/recibir', body), { success: (r) => r?.message })
  if (json) emit('done', json.data)
}
</script>

<template>
  <AppModal :open="true" :title="`Recibir compra ${compra.numero} · ${compra.proveedor}`" width="48rem" @close="emit('close')">
    <form @submit.prevent="recibir">
      <p class="muted intro">Escribe lo que llegó de verdad. Si algo llegó dañado o faltó, anótalo en la novedad.</p>
      <ul class="lineas">
        <li v-for="l in lineas" :key="l.id" class="linea">
          <div class="nombre">
            <strong>{{ l.insumo }}</strong>
            <small class="muted">Pedido {{ l.cantidad }} {{ medida(l) }}<template v-if="l.cantidad_recibida"> · ya llegaron {{ l.cantidad_recibida }}</template></small>
          </div>
          <div class="field">
            <label :for="`rc-llego-${l.id}`">Llegó ({{ medida(l) }})</label>
            <input :id="`rc-llego-${l.id}`" v-model.number="l.llego" class="input" type="number" min="0" step="any" inputmode="decimal">
            <small v-if="l.presentacion && l.llego" class="hint">= {{ formatCantidad(l.llego * l.factor, l.unidad) }}</small>
          </div>
          <div class="field">
            <label :for="`rc-precio-${l.id}`">Precio por {{ medida(l) }}</label>
            <input :id="`rc-precio-${l.id}`" v-model.number="l.precio" class="input" type="number" min="0" step="any"
                   inputmode="numeric" :disabled="l.cantidad_recibida > 0">
          </div>
          <div class="field novedad">
            <label :for="`rc-nov-${l.id}`">Novedad</label>
            <input :id="`rc-nov-${l.id}`" v-model="l.novedad" class="input" maxlength="200" placeholder="Opcional">
          </div>
        </li>
      </ul>

      <div class="form-grid espacio">
        <div class="field">
          <label for="rc-factura">Factura del proveedor</label>
          <input id="rc-factura" v-model="factura" class="input" maxlength="40" placeholder="Opcional">
        </div>
        <div class="field">
          <label for="rc-notas">Notas de la recepción</label>
          <input id="rc-notas" v-model="notas" class="input" maxlength="200" placeholder="Opcional">
        </div>
      </div>

      <p class="resumen">
        Entra al inventario por <strong>{{ formatMoney(valor) }}</strong>.
        <template v-if="faltantes"> {{ faltantes === 1 ? 'Un insumo queda pendiente' : `${faltantes} insumos quedan pendientes` }}.</template>
        <template v-if="compra.forma_pago === 'caja'"> Se paga con dinero de la caja.</template>
      </p>

      <div class="form-actions">
        <button class="btn btn-secundario" type="button" @click="emit('close')">Cancelar</button>
        <button class="btn" type="submit" :disabled="busy || !algo">Confirmar recepción</button>
      </div>
    </form>
  </AppModal>
</template>

<style scoped>
.intro {
  margin-bottom: var(--space-3);
}

.lineas {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.linea {
  display: grid;
  grid-template-columns: minmax(10rem, 1.4fr) minmax(7rem, 1fr) minmax(7rem, 1fr) minmax(9rem, 1.4fr);
  align-items: end;
  gap: var(--space-3);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--linea);
}

.nombre {
  display: flex;
  flex-direction: column;
  align-self: center;
}

.espacio {
  margin-top: var(--space-4);
}

.resumen {
  margin-top: var(--space-3);
}

@media (max-width: 40rem) {
  .linea {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }

  .nombre,
  .novedad {
    grid-column: 1 / -1;
  }
}
</style>
