<script setup>
import { ref, computed } from 'vue'
import { post, postData, download, ApiError } from '@/services/api'
import { useAction } from '@/composables/useAction'
import { formatMoney, plural } from '@/utils/format'
import AppModal from '@/components/AppModal.vue'

/*
  Carga de la carta desde una hoja de cálculo (docs 12 y 41): se descarga la plantilla, se sube y se revisa fila
  por fila antes de guardar. Con errores no entra nada, para no dejar la carta a medias.
*/
defineProps({ open: { type: Boolean, default: false } })
const emit = defineEmits(['close', 'imported'])
const { busy, attempt } = useAction()

const archivo = ref(null)
const existentes = ref('omitir')
const revision = ref(null)
const error = ref('')
const busyLocal = ref(false)

const ACCIONES = { crear: 'Nuevo', actualizar: 'Se actualiza', omitir: 'Ya existe: se deja igual' }
const aplicable = computed(() => revision.value && !revision.value.errores && (revision.value.crear || revision.value.actualizar))
const filas = computed(() => [...(revision.value?.filas || [])].sort((a, b) => b.errores.length - a.errores.length))

function reiniciar() {
  archivo.value = null
  revision.value = null
  error.value = ''
  existentes.value = 'omitir'
}

function cerrar() {
  reiniciar()
  emit('close')
}

function plantilla() {
  attempt(() => download('/producto/importar/plantilla'))
}

function leer(file) {
  return new Promise((resolve, reject) => {
    const lector = new FileReader()
    lector.onload = () => resolve(String(lector.result).split(',')[1] || '')
    lector.onerror = reject
    lector.readAsDataURL(file)
  })
}

async function elegir(evento) {
  const file = evento.target.files[0]
  evento.target.value = ''
  if (!file) return
  revision.value = null
  error.value = ''
  try {
    archivo.value = { nombre: file.name, archivo: await leer(file) }
  } catch {
    error.value = 'No se pudo leer el archivo.'
    return
  }
  revisar()
}

// El rechazo de un archivo se muestra aquí mismo: hay que poder verlo mientras se corrige
async function revisar() {
  if (!archivo.value) return
  revision.value = null
  error.value = ''
  busyLocal.value = true
  try {
    revision.value = await postData('/producto/importar/revisar', { ...archivo.value, existentes: existentes.value })
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'No se pudo revisar el archivo.'
  } finally {
    busyLocal.value = false
  }
}

async function aplicar() {
  const json = await attempt(() => post('/producto/importar/aplicar', { ...archivo.value, existentes: existentes.value }),
    { success: (r) => r?.message })
  if (json) {
    emit('imported')
    cerrar()
  }
}

</script>

<template>
  <AppModal :open="open" title="Importar productos" width="52rem" @close="cerrar">
    <ol class="pasos">
      <li>
        Descarga la plantilla y llénala. Producto, categoría y precio son obligatorios; las categorías que no existan se crean.
        <button class="btn btn-secundario btn-sm" type="button" :disabled="busy" @click="plantilla">Descargar plantilla</button>
      </li>
      <li>
        Súbela en Excel o CSV, hasta 1.000 productos.
        <label class="btn btn-secundario btn-sm subir">
          {{ archivo ? 'Cambiar archivo' : 'Elegir archivo' }}
          <input class="visually-hidden" type="file" accept=".xlsx,.csv" aria-label="Archivo de productos" @change="elegir">
        </label>
        <span v-if="archivo" class="muted">{{ archivo.nombre }}</span>
      </li>
    </ol>

    <fieldset class="existentes">
      <legend>Si un producto ya existe</legend>
      <label class="check"><input v-model="existentes" type="radio" value="omitir" @change="revisar"> Dejarlo como está</label>
      <label class="check"><input v-model="existentes" type="radio" value="actualizar" @change="revisar"> Actualizarlo con los datos del archivo, incluido el precio</label>
    </fieldset>

    <p v-if="busyLocal" class="muted">Revisando…</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <template v-if="revision">
      <p class="resumen" role="status">
        <strong>{{ revision.crear }}</strong> {{ revision.crear === 1 ? 'nuevo' : 'nuevos' }} · <strong>{{ revision.actualizar }}</strong> por actualizar ·
        <strong>{{ revision.omitir }}</strong> sin cambios ·
        <strong :class="{ malos: revision.errores }">{{ revision.errores }}</strong> con errores
      </p>
      <p v-if="revision.categorias_nuevas.length" class="muted">Categorías nuevas: {{ revision.categorias_nuevas.join(', ') }}</p>
      <p v-if="revision.errores" class="error">Corrige las filas marcadas y sube el archivo de nuevo. Mientras tenga errores no se importa nada.</p>
      <div class="table-wrap tabla">
        <table class="table">
          <thead><tr><th>Fila</th><th>Producto</th><th>Categoría</th><th class="num">Precio</th><th>Resultado</th></tr></thead>
          <tbody>
            <tr v-for="f in filas" :key="f.fila" :class="{ mala: f.errores.length }">
              <td>{{ f.fila }}</td>
              <td>{{ f.producto || '—' }}</td>
              <td>{{ f.categoria || '—' }}</td>
              <td class="num">{{ f.precio === null ? '—' : formatMoney(f.precio) }}
                <small v-if="f.precio_anterior !== null && f.precio_anterior !== undefined && f.precio_anterior !== f.precio" class="muted bloque">antes {{ formatMoney(f.precio_anterior) }}</small></td>
              <td><template v-if="f.errores.length">{{ f.errores.join(' ') }}</template><template v-else>{{ ACCIONES[f.accion] }}</template></td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <div class="form-actions">
      <button class="btn btn-secundario" type="button" @click="cerrar">Cancelar</button>
      <button class="btn" type="button" :disabled="busy || !aplicable" @click="aplicar">
        {{ aplicable ? `Importar ${plural(revision.crear + revision.actualizar, 'producto')}` : 'Importar' }}
      </button>
    </div>
  </AppModal>
</template>

<style scoped>
.pasos {
  margin: 0 0 var(--space-4);
  padding-left: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.pasos .btn {
  display: inline-flex;
  margin-left: var(--space-2);
}

.subir {
  cursor: pointer;
}

.existentes {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0 0 var(--space-4);
  padding: var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio-sm);
}

.existentes input {
  flex: none;
}

.existentes legend {
  padding: 0 var(--space-1);
  font-weight: 700;
}

.resumen {
  margin-bottom: var(--space-2);
}

.malos,
.mala td:last-child {
  color: #7a1f19;
}

.mala {
  background: var(--estado-cancelado-suave);
}

.error {
  margin-bottom: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radio-sm);
  background: var(--estado-cancelado-suave);
  color: #7a1f19;
}

.tabla {
  max-height: 22rem;
  overflow-y: auto;
  margin-top: var(--space-3);
}

.bloque {
  display: block;
}
</style>
