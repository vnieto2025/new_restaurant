<script setup>
import { ref, computed } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'

/*
  Platos que se quedaron sin insumos según el inventario (doc 12, sección 5). Solo sugiere: quien está
  en la cocina sabe si de verdad se acabó, así que "Todavía hay" lo oculta hasta que el stock cambie.
  En la pantalla de producción muestra solo lo que hay que agotar; en Hoy, también lo que se está acabando.
*/
const props = defineProps({
  puntoId: { type: [Number, String], default: null },
  completo: { type: Boolean, default: false },
})

const auth = useAuthStore()
const { busy, attempt } = useAction()
const datos = ref(null)
const ocultos = ref(new Set())

const disponible = computed(() => auth.can('productos.agotar') && auth.modulos.has('inventario')
  && (!auth.acceso || auth.acceso.modo === 'completo'))

// Si el stock vuelve a cambiar, la sugerencia reaparece
const clave = (p) => `${p.producto_id}:${p.limitan.map((i) => i.stock).join(',')}`
const sugeridos = computed(() => (datos.value?.sugeridos || []).filter((p) => !ocultos.value.has(clave(p))))
const porAcabarse = computed(() => (props.completo && datos.value?.por_acabarse) || [])
const conInsumos = computed(() => (props.completo && datos.value?.con_insumos) || [])

async function load() {
  if (!disponible.value) return
  const data = props.puntoId ? { punto_produccion_id: Number(props.puntoId) } : {}
  datos.value = await postData('/producto/sugerir_agotados', data).catch(() => datos.value)
}

async function marcar(producto, agotado) {
  const ok = await attempt(() => postData('/producto/agotado', { producto_id: producto.producto_id, agotado }), {
    success: agotado ? `${producto.nombre} agotado en todas las cartas.` : `${producto.nombre} disponible de nuevo.`,
  })
  if (ok) await load()
}

async function marcarTodos() {
  const lista = [...sugeridos.value]
  for (const producto of lista) {
    const ok = await attempt(() => postData('/producto/agotado', { producto_id: producto.producto_id, agotado: true }))
    if (!ok) break
  }
  await load()
}

function ocultar(producto) {
  ocultos.value = new Set([...ocultos.value, clave(producto)])
}

const enLista = (nombres) => (nombres.length > 1 ? `${nombres.slice(0, -1).join(', ')} y ${nombres.at(-1)}` : nombres[0])

defineExpose({ load })
</script>

<template>
  <section v-if="disponible && (sugeridos.length || porAcabarse.length || conInsumos.length)" class="sugerencias"
           aria-label="Sugerencias de agotados">
    <div v-if="sugeridos.length" class="bloque alerta" role="status">
      <div class="cabeza">
        <h2>Se acabó con qué prepararlos</h2>
        <button v-if="sugeridos.length > 1" class="btn btn-sm" type="button" :disabled="busy" @click="marcarTodos">
          Marcar los {{ sugeridos.length }} agotados
        </button>
      </div>
      <p class="nota">Según el inventario. Si todavía hay, sigue vendiéndolo y ajusta el inventario después.</p>
      <ul>
        <li v-for="p in sugeridos" :key="p.producto_id">
          <div class="texto">
            <strong>{{ p.nombre }}</strong>
            <span class="motivo">{{ p.motivo }}</span>
            <span v-if="p.combos?.length" class="motivo">También deja sin {{ enLista(p.combos) }}.</span>
          </div>
          <div class="acciones">
            <button v-escribe class="btn btn-sm" type="button" :disabled="busy" :aria-label="`Marcar agotado ${p.nombre}`" @click="marcar(p, true)">
              Marcar agotado
            </button>
            <button class="btn btn-secundario btn-sm" type="button" :aria-label="`Todavía hay ${p.nombre}`" @click="ocultar(p)">
              Todavía hay
            </button>
          </div>
        </li>
      </ul>
    </div>

    <div v-if="porAcabarse.length" class="bloque">
      <h2>Se están acabando</h2>
      <ul>
        <li v-for="p in porAcabarse" :key="p.producto_id">
          <div class="texto">
            <strong>{{ p.nombre }}: {{ p.porciones === 1 ? 'queda para uno' : `quedan para ${p.porciones}` }}</strong>
            <span class="motivo">{{ p.motivo }}</span>
          </div>
        </li>
      </ul>
    </div>

    <div v-if="conInsumos.length" class="bloque">
      <h2>Agotados que ya se pueden preparar</h2>
      <ul>
        <li v-for="p in conInsumos" :key="p.producto_id">
          <div class="texto">
            <strong>{{ p.nombre }}</strong>
            <span class="motivo">Alcanza para {{ p.porciones }} con lo que hay en inventario.</span>
          </div>
          <div class="acciones">
            <button v-escribe class="btn btn-secundario btn-sm" type="button" :disabled="busy" :aria-label="`Volver a ofrecer ${p.nombre}`"
                    @click="marcar(p, false)">
              Volver a ofrecer
            </button>
          </div>
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.sugerencias {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.bloque {
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--kds-borde, var(--linea));
  border-radius: var(--radio);
  background: var(--kds-barra, var(--superficie));
  color: var(--kds-texto, var(--tinta));
}

.alerta {
  border-left: 6px solid var(--estado-proceso);
}

.cabeza {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

h2 {
  font-size: var(--text-lg);
}

.nota,
.motivo {
  color: var(--kds-suave, var(--acero));
  font-size: var(--text-sm);
}

ul {
  margin: var(--space-2) 0 0;
  padding: 0;
  list-style: none;
}

li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2) var(--space-4);
  padding: var(--space-2) 0;
  border-top: 1px solid var(--kds-borde, var(--linea));
}

li:first-child {
  border-top: 0;
}

.texto {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.acciones {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
</style>
