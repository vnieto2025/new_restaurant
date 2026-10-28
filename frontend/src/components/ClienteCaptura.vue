<script setup>
import { ref, watch } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'

/*
  Captura de cliente en una orden externa (doc 15A, sección 3): al escribir el celular se busca
  al cliente y se autocompleta. Si no existe, se pide confirmar el aviso de datos para registrarlo.
*/
const props = defineProps({
  modelValue: { type: Object, required: true }, // { cliente_nombre, cliente_telefono, acepta_datos }
  // En domicilio el celular es obligatorio (RN-DOM-01)
  telefonoObligatorio: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'cliente'])

const auth = useAuthStore()
const encontrado = ref(null)
let timer = null

function actualizar(campo, valor) {
  emit('update:modelValue', { ...props.modelValue, [campo]: valor })
}

watch(() => props.modelValue.cliente_telefono, (telefono) => {
  clearTimeout(timer)
  const digitos = String(telefono || '').replace(/\D/g, '')
  if (digitos.length < 10 || !auth.can('clientes.ver')) {
    encontrado.value = null
    emit('cliente', null)
    return
  }
  timer = setTimeout(async () => {
    const lista = await postData('/cliente/buscar', { texto: digitos }).catch(() => [])
    encontrado.value = lista.find((c) => c.telefono.endsWith(digitos.slice(-10))) || null
    emit('cliente', encontrado.value)
    if (encontrado.value && !props.modelValue.cliente_nombre) actualizar('cliente_nombre', encontrado.value.nombre)
  }, 350)
})
</script>

<template>
  <div class="captura">
    <div class="field">
      <label for="cap-tel">Celular del cliente</label>
      <input id="cap-tel" :value="modelValue.cliente_telefono" class="input" type="tel" inputmode="tel" autocomplete="off"
             :placeholder="telefonoObligatorio ? 'Obligatorio para domicilio' : 'Opcional para recoger'"
             :required="telefonoObligatorio" @input="actualizar('cliente_telefono', $event.target.value)">
    </div>
    <p v-if="encontrado" class="reconocido">
      Cliente: <strong>{{ encontrado.nombre }}</strong>
      <template v-if="encontrado.notas"> · {{ encontrado.notas }}</template>
    </p>
    <div class="field">
      <label for="cap-nombre">Nombre del cliente</label>
      <input id="cap-nombre" :value="modelValue.cliente_nombre" class="input" maxlength="100" autocomplete="off"
             @input="actualizar('cliente_nombre', $event.target.value)">
    </div>
    <label v-if="modelValue.cliente_telefono && !encontrado" class="check">
      <input type="checkbox" :checked="modelValue.acepta_datos" @change="actualizar('acepta_datos', $event.target.checked)">
      Le informé el aviso de datos y acepta que lo registremos
    </label>
  </div>
</template>

<style scoped>
.captura {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.reconocido {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radio-sm);
  background: var(--accion-suave);
  font-size: var(--text-sm);
}

.check {
  font-size: var(--text-sm);
}
</style>
