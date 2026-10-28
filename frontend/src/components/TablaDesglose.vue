<script setup>
import { computed } from 'vue'
import { formatMoney, downloadCsv } from '@/utils/format'

// Desglose de ventas (por producto, zona, canal...) con participación y descarga en CSV (doc 26)
const props = defineProps({
  titulo: { type: String, required: true },
  columna: { type: String, default: 'Nombre' },
  filas: { type: Array, required: true }, // [{ nombre, unidades?, pagos?, valor }]
  conteo: { type: String, default: 'unidades' }, // unidades | pagos | ninguno
  archivo: { type: String, default: 'reporte' },
})

const total = computed(() => props.filas.reduce((s, f) => s + f.valor, 0))
const etiquetaConteo = computed(() => ({ unidades: 'Unidades', pagos: 'Pagos' })[props.conteo])

function porcentaje(valor) {
  return total.value ? Math.round((valor * 100) / total.value) : 0
}

function exportar() {
  const columnas = [{ titulo: props.columna, campo: 'nombre' }]
  if (etiquetaConteo.value) columnas.push({ titulo: etiquetaConteo.value, campo: props.conteo })
  columnas.push({ titulo: 'Valor', campo: 'valor' })
  downloadCsv(props.archivo, columnas, props.filas)
}
</script>

<template>
  <section class="panel desglose">
    <header class="cabeza">
      <h3>{{ titulo }}</h3>
      <button v-if="filas.length" type="button" class="enlace no-print" @click="exportar">Descargar CSV</button>
    </header>
    <p v-if="!filas.length" class="empty">Sin datos en este periodo.</p>
    <div v-else class="table-wrap">
      <table class="table">
        <thead>
          <tr><th>{{ columna }}</th><th v-if="etiquetaConteo" class="num">{{ etiquetaConteo }}</th><th class="num">Valor</th><th class="num">%</th></tr>
        </thead>
        <tbody>
          <tr v-for="fila in filas" :key="fila.nombre">
            <td>{{ fila.nombre }}</td>
            <td v-if="etiquetaConteo" class="num">{{ fila[conteo] }}</td>
            <td class="num">{{ formatMoney(fila.valor) }}</td>
            <td class="num participacion">
              <span class="barra" :style="{ width: `${porcentaje(fila.valor)}%` }" aria-hidden="true"></span>
              <span>{{ porcentaje(fila.valor) }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.desglose {
  overflow: hidden;
}

.cabeza {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--linea);
}

.cabeza h3 {
  font-size: var(--text-base);
  font-stretch: 100%;
}

.enlace {
  border: none;
  background: none;
  color: var(--accion);
  text-decoration: underline;
  font-size: var(--text-sm);
  cursor: pointer;
}

.participacion {
  position: relative;
  width: 5.5rem;
}

.barra {
  position: absolute;
  left: var(--space-2);
  bottom: 0.45rem;
  height: 3px;
  max-width: calc(100% - 2.5rem);
  border-radius: 2px;
  background: #00899b;
}
</style>
