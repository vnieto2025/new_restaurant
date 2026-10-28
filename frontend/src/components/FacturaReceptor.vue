<script setup>
import { ref } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { TIPOS_IDENTIFICACION } from '@/utils/format'

/*
  Datos del cliente para una factura a su nombre (doc 21, sección 2).
  Si ya está registrado se busca por nombre, celular o documento y se completan sus datos.
*/
const model = defineModel({ type: Object, required: true }) // { cliente_id, nombre, tipo_documento, documento, correo }

const auth = useAuthStore()
const texto = ref('')
const resultados = ref([])
const buscado = ref(false)

async function buscar() {
  if (texto.value.trim().length < 3) return
  resultados.value = await postData('/cliente/buscar', { texto: texto.value.trim() }).catch(() => [])
  buscado.value = true
}

function elegir(cliente) {
  model.value = {
    cliente_id: cliente.id,
    nombre: cliente.nombre,
    tipo_documento: cliente.tipo_documento || model.value.tipo_documento || 'CC',
    documento: cliente.documento || '',
    correo: cliente.correo || '',
  }
  resultados.value = []
  buscado.value = false
  texto.value = ''
}

function actualizar(campo, valor) {
  model.value = { ...model.value, [campo]: valor }
}
</script>

<template>
  <div class="receptor">
    <form v-if="auth.can('clientes.ver')" class="buscar" @submit.prevent="buscar">
      <input v-model="texto" class="input" type="search" placeholder="Buscar cliente registrado" aria-label="Buscar cliente registrado">
      <button class="btn btn-secundario btn-sm" type="submit">Buscar</button>
    </form>
    <ul v-if="resultados.length" class="resultados">
      <li v-for="c in resultados" :key="c.id">
        <button type="button" @click="elegir(c)">
          <strong>{{ c.nombre }}</strong>
          <span class="muted">{{ c.documento ? `${c.tipo_documento} ${c.documento}` : 'sin documento' }} · {{ c.telefono_legible }}</span>
        </button>
      </li>
    </ul>
    <p v-else-if="buscado" class="muted">No está registrado: escribe sus datos.</p>

    <div class="campos">
      <div class="field">
        <label for="fr-tipo">Tipo de documento</label>
        <select id="fr-tipo" :value="model.tipo_documento" class="select" @change="actualizar('tipo_documento', $event.target.value)">
          <option v-for="(label, valor) in TIPOS_IDENTIFICACION" :key="valor" :value="valor">{{ label }}</option>
        </select>
      </div>
      <div class="field">
        <label for="fr-doc">Número</label>
        <input id="fr-doc" :value="model.documento" class="input" maxlength="30" inputmode="numeric" required
               @input="actualizar('documento', $event.target.value)">
      </div>
      <div class="field ancho">
        <label for="fr-nombre">Nombre o razón social</label>
        <input id="fr-nombre" :value="model.nombre" class="input" maxlength="150" required
               @input="actualizar('nombre', $event.target.value)">
      </div>
      <div class="field ancho">
        <label for="fr-correo">Correo para enviarle la factura</label>
        <input id="fr-correo" :value="model.correo" class="input" type="email" @input="actualizar('correo', $event.target.value)">
      </div>
    </div>
  </div>
</template>

<style scoped>
.receptor {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.buscar {
  display: flex;
  gap: var(--space-2);
}

.buscar .input {
  flex: 1;
  min-width: 0;
}

.resultados {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.resultados button {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio-sm);
  background: var(--papel);
  text-align: left;
  cursor: pointer;
}

.resultados span {
  font-size: var(--text-sm);
}

.campos {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--space-3);
}

.ancho {
  grid-column: 1 / -1;
}
</style>
