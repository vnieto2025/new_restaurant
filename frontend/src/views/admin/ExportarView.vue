<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData, download } from '@/services/api'
import { useAction } from '@/composables/useAction'
import { isoDate } from '@/utils/format'
import AppModal from '@/components/AppModal.vue'

/*
  Descarga de datos en CSV o Excel (docs 26, 26B y 41). El archivo sale completo del servidor, no de lo que se
  ve en pantalla. Lo que trae datos de personas se confirma antes, y cada descarga queda en Auditoría.
*/
const { busy, attempt, quiet } = useAction()

const grupos = ref([])
const cargado = ref(false)
const periodo = ref('mes')
const rango = ref({ desde: '', hasta: '' })
const confirmar = ref(null)

const PERIODOS = [
  { id: 'hoy', label: 'Hoy' },
  { id: 'semana', label: 'Últimos 7 días' },
  { id: 'mes', label: 'Este mes' },
  { id: 'mes_anterior', label: 'Mes anterior' },
  { id: 'rango', label: 'Otro rango' },
]
const FORMATOS = [{ id: 'xlsx', label: 'Excel' }, { id: 'csv', label: 'CSV' }]

const fechas = computed(() => {
  const hoy = new Date()
  const mes = (delta, dia) => isoDate(new Date(hoy.getFullYear(), hoy.getMonth() + delta, dia))
  if (periodo.value === 'hoy') return { desde: isoDate(hoy), hasta: isoDate(hoy) }
  if (periodo.value === 'semana') return { desde: isoDate(new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - 6)), hasta: isoDate(hoy) }
  if (periodo.value === 'mes') return { desde: mes(0, 1), hasta: isoDate(hoy) }
  if (periodo.value === 'mes_anterior') return { desde: mes(-1, 1), hasta: mes(0, 0) }
  return rango.value
})
const faltaRango = computed(() => !fechas.value.desde || !fechas.value.hasta)

function pedir(conjunto, formato) {
  if (conjunto.personal) confirmar.value = { conjunto, formato }
  else bajar(conjunto, formato)
}

async function bajar(conjunto, formato) {
  confirmar.value = null
  const cuerpo = { conjunto: conjunto.clave, formato, ...(conjunto.periodo ? fechas.value : {}) }
  await attempt(() => download('/exportacion/generar', cuerpo), { success: `${conjunto.titulo}: archivo descargado.` })
}

onMounted(async () => {
  const data = await quiet(() => postData('/exportacion/catalogo'))
  grupos.value = data?.grupos || []
  cargado.value = true
})
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Exportar datos</h1>
        <p>Descarga la información completa para tu contador, tu software de nómina o tu propio análisis.</p>
      </div>
    </header>

    <div class="periodos" role="group" aria-label="Periodo">
      <button v-for="p in PERIODOS" :key="p.id" type="button" class="btn btn-secundario btn-sm" :aria-pressed="periodo === p.id"
              @click="periodo = p.id">{{ p.label }}</button>
      <template v-if="periodo === 'rango'">
        <input v-model="rango.desde" class="input" type="date" aria-label="Desde">
        <input v-model="rango.hasta" class="input" type="date" aria-label="Hasta">
      </template>
    </div>

    <p v-if="!cargado" class="empty">Cargando…</p>
    <section v-for="grupo in grupos" :key="grupo.nombre" class="bloque">
      <h2>{{ grupo.nombre }}</h2>
      <ul class="panel lista">
        <li v-for="c in grupo.conjuntos" :key="c.clave" class="fila">
          <div class="info">
            <strong>{{ c.titulo }}</strong>
            <span class="muted">{{ c.descripcion }}<template v-if="!c.periodo"> Estado actual, no depende del periodo.</template></span>
            <span v-if="c.personal" class="personal">Incluye datos de personas</span>
          </div>
          <div class="actions">
            <button v-for="f in FORMATOS" :key="f.id" class="btn btn-secundario btn-sm" type="button"
                    :aria-label="`Descargar ${c.titulo} en ${f.label}`" :disabled="busy || (c.periodo && faltaRango)"
                    @click="pedir(c, f.id)">{{ f.label }}</button>
          </div>
        </li>
      </ul>
    </section>

    <AppModal :open="!!confirmar" :title="confirmar ? `Descargar ${confirmar.conjunto.titulo}` : ''" width="30rem" @close="confirmar = null">
      <template v-if="confirmar">
        <p>Este archivo trae datos de personas. Guárdalo en un lugar seguro, compártelo solo con quien lo necesite y bórralo cuando ya no lo uses.</p>
        <p class="muted espacio">La descarga queda registrada en Auditoría con tu usuario.</p>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="confirmar = null">Volver</button>
          <button class="btn" type="button" :disabled="busy" @click="bajar(confirmar.conjunto, confirmar.formato)">Descargar</button>
        </div>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.periodos {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-5);
}

.periodos [aria-pressed='true'] {
  background: var(--tinta);
  border-color: var(--tinta);
  color: #fff;
}

.periodos .input {
  width: auto;
}

.bloque {
  margin-bottom: var(--space-5);
}

.bloque h2 {
  font-size: var(--text-lg);
  margin-bottom: var(--space-2);
}

.lista {
  list-style: none;
  margin: 0;
  padding: 0;
}

.fila {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
}

.fila + .fila {
  border-top: 1px solid var(--linea);
}

.info {
  display: flex;
  flex: 1 1 16rem;
  flex-direction: column;
  min-width: 0;
}

.personal {
  font-size: var(--text-sm);
  font-weight: 600;
}

.espacio {
  margin-top: var(--space-3);
}
</style>
