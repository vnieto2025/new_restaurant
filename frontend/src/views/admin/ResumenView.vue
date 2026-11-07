<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { useToastStore } from '@/stores/toast'
import { formatMoney, formatChange, isoDate } from '@/utils/format'
import { enlaceWhatsapp } from '@/utils/inventario'

// Resumen de una jornada para el dueño (docs 26 y 31B): verlo, mandarlo por WhatsApp o imprimirlo
const auth = useAuthStore()
const toast = useToastStore()
const { busy, attempt, quiet } = useAction()

const resumen = ref(null)
const dia = ref('')
const envio = ref(null)

const configura = computed(() => auth.can('restaurante.configurar') && (!auth.acceso || auth.acceso.modo === 'completo'))
const whatsapp = computed(() => resumen.value && (enlaceWhatsapp(resumen.value.telefono, resumen.value.texto)
  || `https://wa.me/?text=${encodeURIComponent(resumen.value.texto)}`))

async function load(jornada = dia.value) {
  const data = await quiet(() => postData('/reporte/resumen_diario', jornada ? { jornada } : {}))
  if (data) {
    resumen.value = data
    dia.value = String(data.jornada)
  }
}

function moverDia(dias) {
  const fecha = new Date(`${dia.value}T12:00:00`)
  fecha.setDate(fecha.getDate() + dias)
  load(isoDate(fecha))
}

async function copiar() {
  try {
    await navigator.clipboard.writeText(resumen.value.texto)
    toast.success('Resumen copiado.')
  } catch {
    toast.error('El navegador no dejó copiar. Selecciona el texto y cópialo a mano.')
  }
}

function imprimir() {
  window.print()
}

async function cargarEnvio() {
  if (!configura.value) return
  const data = await quiet(() => postData('/reporte/resumen_diario/config/get'))
  if (data) envio.value = { ...data }
}

async function guardarEnvio() {
  const data = await attempt(() => postData('/reporte/resumen_diario/config/save', {
    activo: envio.value.activo, telefono: envio.value.telefono || null, nombre: envio.value.nombre?.trim() || null,
  }), { success: (d) => (d.activo ? 'Listo: el resumen quedará por enviar al cerrar cada jornada.' : 'Envío al cierre apagado.') })
  if (data) {
    envio.value = { ...data }
    await load()
  }
}

onMounted(() => {
  load()
  cargarEnvio()
})
</script>

<template>
  <div>
    <header class="page-head no-print">
      <div>
        <h1>Resumen del día</h1>
        <p>Cómo le fue al restaurante en una jornada, listo para mandar al dueño</p>
      </div>
      <div class="actions">
        <button class="btn btn-secundario" type="button" aria-label="Día anterior" @click="moverDia(-1)">‹</button>
        <input v-model="dia" class="input fecha" type="date" aria-label="Jornada" @change="load()">
        <button class="btn btn-secundario" type="button" aria-label="Día siguiente" :disabled="resumen?.en_curso" @click="moverDia(1)">›</button>
      </div>
    </header>

    <template v-if="resumen">
      <section class="hoja" aria-label="Resumen">
        <p class="muted">{{ resumen.restaurante }}</p>
        <h2 class="fecha-titulo"><span class="fecha-texto">{{ resumen.fecha }}</span><span v-if="resumen.en_curso" class="en-curso">en curso</span></h2>

        <div class="cifras">
          <div>
            <p class="muted">Ventas</p>
            <p class="cifra">{{ formatMoney(resumen.totales.ventas) }}</p>
            <p v-if="resumen.comparativo.variacion_ventas !== null" class="muted">
              {{ formatChange(resumen.comparativo.variacion_ventas) }} vs {{ resumen.comparativo.nombre.toLowerCase() }}
              ({{ formatMoney(resumen.comparativo.ventas) }})
            </p>
          </div>
          <div>
            <p class="muted">Cuentas</p>
            <p class="cifra">{{ resumen.totales.cuentas }}</p>
            <p class="muted">Ticket promedio {{ formatMoney(resumen.totales.ticket_promedio) }}</p>
          </div>
          <div v-if="resumen.totales.propinas || resumen.totales.descuentos">
            <p class="muted">Propinas</p>
            <p class="cifra">{{ formatMoney(resumen.totales.propinas) }}</p>
            <p class="muted">Descuentos {{ formatMoney(resumen.totales.descuentos) }}</p>
          </div>
        </div>

        <div class="bloques">
          <div v-if="resumen.caja?.medios.length">
            <h3>Cómo pagaron</h3>
            <p v-for="m in resumen.caja.medios" :key="m.nombre" class="fila"><span>{{ m.nombre }}</span><span>{{ formatMoney(m.valor) }}</span></p>
          </div>
          <div>
            <h3>Lo más pedido</h3>
            <p v-for="p in resumen.productos" :key="p.nombre" class="fila"><span>{{ p.nombre }}</span><span>{{ p.unidades }}</span></p>
            <p v-if="!resumen.productos.length" class="muted">Sin ventas.</p>
          </div>
          <div>
            <h3>Lo que hay que revisar</h3>
            <p v-if="resumen.cancelaciones.items" class="fila">
              <span>Cancelaciones ({{ resumen.cancelaciones.items }})</span><span>{{ formatMoney(resumen.cancelaciones.valor) }}</span>
            </p>
            <template v-for="t in resumen.caja?.turnos || []" :key="t.cajero + t.estado">
              <p v-if="t.estado !== 'cerrado'" class="fila"><span>Turno de {{ t.cajero }}</span><span>sigue abierto</span></p>
              <p v-else-if="t.diferencia" class="fila">
                <span>Caja de {{ t.cajero }}</span><span>{{ t.diferencia > 0 ? 'sobraron' : 'faltaron' }} {{ formatMoney(Math.abs(t.diferencia)) }}</span>
              </p>
            </template>
            <p v-if="resumen.inventario && (resumen.inventario.bajos || resumen.inventario.negativos)" class="fila">
              <span>Inventario</span><span>{{ resumen.inventario.bajos }} bajo el mínimo · {{ resumen.inventario.negativos }} en negativo</span>
            </p>
            <p v-if="resumen.agotados.length" class="fila"><span>Agotados</span><span>{{ resumen.agotados.join(', ') }}</span></p>
          </div>
        </div>
      </section>

      <div class="actions envio no-print">
        <a class="btn" :href="whatsapp" target="_blank" rel="noopener">
          {{ resumen.telefono ? `Enviar por WhatsApp a ${resumen.telefono_legible}` : 'Enviar por WhatsApp' }}
        </a>
        <button class="btn btn-secundario" type="button" @click="copiar">Copiar texto</button>
        <button class="btn btn-secundario" type="button" @click="imprimir">Imprimir</button>
      </div>

      <details class="panel texto no-print">
        <summary>Ver el texto que se envía</summary>
        <pre>{{ resumen.texto }}</pre>
      </details>
    </template>

    <form v-if="envio" class="panel envio-config no-print" @submit.prevent="guardarEnvio">
      <h2>Enviar al cerrar la jornada</h2>
      <p v-if="envio.puede_enviar" class="muted">
        Al cerrar la jornada en caja, el resumen queda en Avisos por enviar. Si los avisos son automáticos, sale solo.
      </p>
      <p v-else class="muted">Tu plan no incluye los avisos por WhatsApp: usa el botón de arriba para enviarlo.</p>
      <label class="check"><input v-model="envio.activo" type="checkbox" :disabled="!envio.puede_enviar"> Dejar listo el resumen al cerrar cada jornada</label>
      <div class="form-grid">
        <div class="field">
          <label for="r-tel">Celular del dueño</label>
          <input id="r-tel" v-model="envio.telefono" class="input" inputmode="tel" maxlength="20" placeholder="300 123 4567">
        </div>
        <div class="field">
          <label for="r-nombre">Nombre</label>
          <input id="r-nombre" v-model="envio.nombre" class="input" maxlength="60" placeholder="Marta">
        </div>
      </div>
      <div class="form-actions">
        <button class="btn" type="submit" :disabled="busy" :aria-busy="busy">Guardar</button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.fecha {
  width: auto;
}

.hoja {
  padding: var(--space-5);
  background: var(--superficie);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
}

.fecha-titulo {
  font-size: var(--text-2xl);
  font-stretch: 70%;
}

.fecha-texto {
  display: inline-block;
}

.fecha-texto::first-letter {
  text-transform: uppercase;
}

.en-curso {
  margin-left: var(--space-2);
  padding: 0 var(--space-2);
  border: 1px solid var(--linea-fuerte);
  border-radius: 999px;
  font-size: var(--text-sm);
  font-weight: 600;
  font-stretch: 100%;
  vertical-align: middle;
}

.cifras {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr));
  gap: var(--space-4);
  margin: var(--space-4) 0;
}

.cifra {
  font-size: var(--text-2xl);
  font-weight: 800;
  font-stretch: 65%;
  line-height: 1.1;
}

.bloques {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr));
  gap: var(--space-5);
  padding-top: var(--space-4);
  border-top: 1px solid var(--linea);
}

h3 {
  margin-bottom: var(--space-2);
  font-size: var(--text-base);
}

.fila {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-1) 0;
  border-bottom: 1px dashed var(--linea);
}

.fila span:last-child {
  text-align: right;
}

.envio {
  margin: var(--space-4) 0;
}

.texto,
.envio-config {
  padding: var(--space-4);
}

.texto summary {
  cursor: pointer;
  font-weight: 600;
}

.texto pre {
  margin: var(--space-3) 0 0;
  white-space: pre-wrap;
  font-family: var(--font-papel);
  font-size: var(--text-sm);
}

.envio-config {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-top: var(--space-4);
}

.envio-config h2 {
  font-size: var(--text-lg);
}
</style>
