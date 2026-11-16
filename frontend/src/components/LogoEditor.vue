<script setup>
import { ref } from 'vue'
import { postData } from '@/services/api'
import { useAction } from '@/composables/useAction'
import { mediaUrl } from '@/utils/format'
import { leerImagen } from '@/utils/imagen'

/*
  Logo del restaurante (ADR-060): horizontal, se ve en la carta, el seguimiento, el pago y las tirillas.
  Lo usa la configuración del restaurante y, con restauranteId, la consola de plataforma (soporte).
*/
const props = defineProps({
  logo: { type: String, default: null },
  restauranteId: { type: Number, default: null },
})
const emit = defineEmits(['change'])
const { busy, attempt } = useAction()
const error = ref('')
const medidas = ref(null)

const base = () => (props.restauranteId ? '/plataforma/restaurante/logo' : '/restaurante/logo')
const cuerpo = (extra = {}) => (props.restauranteId ? { restaurante_id: props.restauranteId, ...extra } : extra)

async function subir(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  error.value = ''
  if (!file) return
  let imagen
  try {
    imagen = await leerImagen(file)
  } catch (e) {
    error.value = e.message
    return
  }
  medidas.value = `${imagen.ancho} × ${imagen.alto} px`
  // Se avisa antes de subir; el servidor lo vuelve a revisar
  if (imagen.ancho < imagen.alto * 1.2) {
    error.value = `Tu imagen mide ${medidas.value}: el logo debe ser horizontal, más ancho que alto. Sugerido: 600 × 200 px.`
    return
  }
  const data = await attempt(() => postData(base(), cuerpo({ archivo: imagen.archivo })), { success: 'Logo guardado.' })
  if (data) emit('change', data.logo)
}

async function quitar() {
  const data = await attempt(() => postData(`${base()}/quitar`, cuerpo()), { success: 'Logo quitado.' })
  if (data) emit('change', null)
}
</script>

<template>
  <div class="logo-editor">
    <div class="marco" :class="{ vacio: !logo }">
      <img v-if="logo" :src="mediaUrl(logo)" alt="Logo del restaurante">
      <span v-else>Sin logo</span>
    </div>
    <div class="datos">
      <p class="muted">Horizontal. Tamaño sugerido: <strong>600 × 200 px</strong> (proporción 3:1). Un PNG con fondo transparente se ve mejor.
        Máximo 6 MB.</p>
      <div class="actions">
        <label v-escribe class="btn btn-secundario btn-sm subir">
          {{ logo ? 'Cambiar logo' : 'Subir logo' }}
          <input type="file" accept="image/png,image/jpeg,image/webp" class="visually-hidden" :disabled="busy" @change="subir">
        </label>
        <button v-if="logo" v-escribe class="btn btn-secundario btn-sm" type="button" :disabled="busy" @click="quitar">Quitar</button>
      </div>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
    </div>
  </div>
</template>

<style scoped>
.logo-editor {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-4);
}

/* Marco 3:1, la proporción sugerida: muestra cómo se verá */
.marco {
  display: grid;
  place-items: center;
  width: 15rem;
  max-width: 100%;
  aspect-ratio: 3 / 1;
  padding: var(--space-2);
  border: 1px solid var(--linea);
  border-radius: var(--radio-sm);
  background: repeating-conic-gradient(var(--fondo) 0 25%, var(--superficie) 0 50%) 0 0 / 16px 16px;
}

.marco img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.marco.vacio {
  background: var(--fondo);
  color: var(--acero);
  font-size: var(--text-sm);
}

.datos {
  flex: 1 1 16rem;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.subir {
  cursor: pointer;
}

.error {
  color: var(--peligro);
  font-size: var(--text-sm);
}
</style>
