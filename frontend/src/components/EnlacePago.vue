<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'
import { formatMoney } from '@/utils/format'
import { enlaceWhatsapp } from '@/utils/inventario'
import AppModal from '@/components/AppModal.vue'

/*
  Enlace para que el cliente pague su pedido desde el celular (doc 20A): se envía por WhatsApp o se copia.
  El pago aparece solo en la cuenta cuando la pasarela lo confirma.
*/
const props = defineProps({ sesionMesaId: { type: Number, required: true } })
const emit = defineEmits(['close'])

const { attempt } = useAction()
const datos = ref(null)
const copiado = ref(false)

const url = computed(() => datos.value ? `${window.location.origin}/pagar?seguimiento=${datos.value.seguimiento}` : '')
const mensaje = computed(() => datos.value
  ? `Hola${datos.value.cliente_nombre ? ` ${datos.value.cliente_nombre.split(' ')[0]}` : ''}, puedes pagar tu pedido de ${datos.value.restaurante} (${formatMoney(datos.value.saldo)}) aquí: ${url.value}`
  : '')

async function copiar() {
  try {
    await navigator.clipboard.writeText(url.value)
    copiado.value = true
  } catch {
    copiado.value = false
  }
}

onMounted(async () => {
  datos.value = await attempt(() => postData('/pago_linea/enlace', { sesion_mesa_id: props.sesionMesaId }))
  if (!datos.value) emit('close')
})
</script>

<template>
  <AppModal :open="true" title="Enlace de pago" width="30rem" @close="emit('close')">
    <template v-if="datos">
      <p>Por pagar: <strong>{{ formatMoney(datos.saldo) }}</strong></p>
      <label class="visually-hidden" for="enlace-pago">Enlace de pago</label>
      <input id="enlace-pago" class="input espacio" :value="url" readonly @focus="$event.target.select()">
      <p class="muted espacio">El cliente elige la propina y paga en la página de la pasarela. El pago aparece en la cuenta apenas se confirme.</p>
      <div class="form-actions">
        <button class="btn btn-secundario" type="button" @click="copiar">{{ copiado ? 'Copiado' : 'Copiar enlace' }}</button>
        <a v-if="datos.telefono" class="btn" :href="enlaceWhatsapp(datos.telefono, mensaje)" target="_blank" rel="noopener">Enviar por WhatsApp</a>
      </div>
    </template>
  </AppModal>
</template>

<style scoped>
.espacio {
  margin-top: var(--space-3);
}
</style>
