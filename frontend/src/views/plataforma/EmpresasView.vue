<script setup>
import { ref, computed, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { formatMoney, formatDate, isoDate } from '@/utils/format'
import AppModal from '@/components/AppModal.vue'

/*
  Consola del proveedor del software (doc 06): alta manual de empresas, sus restaurantes y contratos,
  con planes comerciales y el cobro manual del servicio (doc 42). Una empresa nueva queda lista para operar.
*/
const auth = useAuthStore()
const { busy, attempt, quiet } = useAction()

const empresas = ref([])
const modulos = ref([])
const catalogo = ref({ planes: [], complementos: [], dias_gracia: 10 })
const alta = ref(null)
const contrato = ref(null)
const cobros = ref(null)

const ESTADOS_CONTRATO = { prueba: 'Prueba', activo: 'Activo', suspendido: 'Suspendido', cancelado: 'Cancelado' }
const MEDIOS = { transferencia: 'Transferencia', efectivo: 'Efectivo', tarjeta: 'Tarjeta', otro: 'Otro' }
const complementos = computed(() => catalogo.value.complementos.map((c) => c.codigo))

async function load() {
  const [lista, mods, planes] = await Promise.all([
    quiet(() => postData('/plataforma/empresa/list')), quiet(() => postData('/plataforma/modulo/list')),
    quiet(() => postData('/plataforma/plan/list'))])
  empresas.value = lista || []
  modulos.value = mods || []
  if (planes) catalogo.value = planes
}

// Mismo criterio que el servidor: el plan sale de los módulos (Utils/catalogo.plan_de)
function planDe(seleccion) {
  const elegidos = new Set(seleccion)
  for (const plan of catalogo.value.planes) {
    const nucleo = plan.modulos
    const sobran = [...elegidos].filter((m) => !nucleo.includes(m) && !complementos.value.includes(m))
    if (nucleo.every((m) => elegidos.has(m)) && !sobran.length) return plan
  }
  return null
}

// Elegir un plan reemplaza su núcleo y conserva los complementos marcados
function aplicarPlan(destino, plan) {
  destino.modulos = [...plan.modulos, ...destino.modulos.filter((m) => complementos.value.includes(m) && !plan.modulos.includes(m))]
}

function nueva() {
  alta.value = {
    nombre_comercial: '', contacto_nombre: '', contacto_correo: '', contacto_telefono: '',
    modulos: ['pedidos'], estado_contrato: 'prueba',
    restaurante: { nombre: '', tipo: 'restaurante', hora_inicio_jornada: '06:00' },
    admin: { usuario: '', nombre: '', password: '' },
  }
}

async function crear() {
  const ok = await attempt(() => postData('/plataforma/empresa/create', alta.value),
    { success: `Empresa creada. El administrador entra con el usuario ${alta.value.admin.usuario}.` })
  if (ok) {
    alta.value = null
    load()
  }
}

function editarContrato(restaurante) {
  const c = restaurante.contrato
  contrato.value = {
    restaurante_id: restaurante.id, nombre: restaurante.nombre, estado: c.estado, fecha_fin: c.fecha_fin,
    modulos: c.modulos.filter((m) => m !== 'base'), mensualidad: c.mensualidad, proximo_vencimiento: c.proximo_vencimiento,
    notas_comerciales: c.notas_comerciales || '',
  }
}

async function guardarContrato() {
  const c = contrato.value
  const ok = await attempt(() => postData('/plataforma/contrato/update', {
    ...c, mensualidad: c.mensualidad === '' || c.mensualidad === null ? null : Number(c.mensualidad),
    proximo_vencimiento: c.proximo_vencimiento || null, fecha_fin: c.fecha_fin || null,
    notas_comerciales: c.notas_comerciales.trim() || null,
  }), { success: 'Contrato actualizado.' })
  if (ok) {
    contrato.value = null
    load()
  }
}

async function verCobros(restaurante) {
  const datos = await quiet(() => postData('/plataforma/suscripcion/pagos', { restaurante_id: restaurante.id }))
  if (!datos) return
  cobros.value = { ...datos, restaurante, form: nuevoPago(datos.suscripcion) }
}

function nuevoPago(suscripcion) {
  return { valor: suscripcion.mensualidad || null, meses: 1, medio: 'transferencia', referencia: '', factura: '', fecha: isoDate(new Date()) }
}

async function registrarPago() {
  const f = cobros.value.form
  const datos = await attempt(() => postData('/plataforma/suscripcion/pagar', {
    restaurante_id: cobros.value.restaurante.id, valor: Number(f.valor), meses: Number(f.meses), medio: f.medio, fecha: f.fecha,
    referencia: f.referencia.trim() || null, factura: f.factura.trim() || null,
  }), { success: (d) => d && `Pago registrado. Vence el ${formatDate(d.suscripcion.proximo_vencimiento)}.` })
  if (!datos) return
  cobros.value = { ...cobros.value, ...datos, restaurante: cobros.value.restaurante, form: nuevoPago(datos.suscripcion) }
  load()
}

onMounted(load)
</script>

<template>
  <main class="plataforma">
    <header class="page-head">
      <div>
        <h1>Empresas</h1>
        <p>Consola de soporte de la plataforma: contratos, planes y cobro del servicio.</p>
      </div>
      <div class="actions">
        <button class="btn" type="button" @click="nueva">Dar de alta una empresa</button>
        <button class="btn btn-secundario" type="button" @click="auth.logout()">Salir</button>
      </div>
    </header>

    <article v-for="empresa in empresas" :key="empresa.id" class="panel empresa">
      <header class="empresa-head">
        <h2>{{ empresa.nombre_comercial }}</h2>
        <span class="muted">{{ empresa.estado }} · {{ empresa.contacto_nombre || 'Sin contacto' }}</span>
      </header>
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>Restaurante</th><th>Plan</th><th>Contrato</th><th>Cuenta</th><th class="num">Mensualidad</th><th></th></tr></thead>
          <tbody>
            <tr v-for="restaurante in empresa.restaurantes" :key="restaurante.id">
              <td><strong>{{ restaurante.nombre }}</strong></td>
              <td>{{ restaurante.suscripcion?.plan_nombre }}
                <small v-if="restaurante.suscripcion?.complementos.length" class="muted bloque">+ {{ restaurante.suscripcion.complementos.join(', ') }}</small></td>
              <td>{{ ESTADOS_CONTRATO[restaurante.contrato?.estado] }}
                <small v-if="restaurante.contrato?.fecha_fin" class="muted bloque">hasta {{ formatDate(restaurante.contrato.fecha_fin) }}</small></td>
              <td><span class="cuenta" :class="restaurante.suscripcion?.cuenta.estado">{{ restaurante.suscripcion?.cuenta.texto }}</span>
                <small v-if="restaurante.suscripcion?.cuenta.suspender_sugerido" class="alerta bloque">Pasó el periodo de gracia</small>
                <small v-else-if="restaurante.contrato?.proximo_vencimiento" class="muted bloque">vence {{ formatDate(restaurante.contrato.proximo_vencimiento) }}</small></td>
              <td class="num">{{ restaurante.contrato?.mensualidad ? formatMoney(restaurante.contrato.mensualidad) : '—' }}</td>
              <td><div class="actions">
                <button class="btn btn-secundario btn-sm" type="button" @click="editarContrato(restaurante)">Contrato</button>
                <button class="btn btn-secundario btn-sm" type="button" @click="verCobros(restaurante)">Pagos</button>
              </div></td>
            </tr>
          </tbody>
        </table>
      </div>
    </article>
    <p v-if="!empresas.length" class="empty">Todavía no hay empresas.</p>

    <AppModal :open="!!alta" title="Dar de alta una empresa" width="44rem" @close="alta = null">
      <form v-if="alta" @submit.prevent="crear">
        <h3 class="seccion">Empresa</h3>
        <div class="form-grid">
          <div class="field"><label for="e-nombre">Nombre comercial</label><input id="e-nombre" v-model="alta.nombre_comercial" class="input" required></div>
          <div class="field"><label for="e-contacto">Contacto</label><input id="e-contacto" v-model="alta.contacto_nombre" class="input"></div>
          <div class="field"><label for="e-correo">Correo</label><input id="e-correo" v-model="alta.contacto_correo" class="input" type="email"></div>
          <div class="field"><label for="e-tel">Teléfono</label><input id="e-tel" v-model="alta.contacto_telefono" class="input" type="tel"></div>
        </div>
        <h3 class="seccion">Primer restaurante</h3>
        <div class="form-grid">
          <div class="field"><label for="e-rest">Nombre</label><input id="e-rest" v-model="alta.restaurante.nombre" class="input" required></div>
          <div class="field"><label for="e-jornada">Inicio de jornada</label><input id="e-jornada" v-model="alta.restaurante.hora_inicio_jornada" class="input" type="time"></div>
          <div class="field">
            <label for="e-contrato">Contrato</label>
            <select id="e-contrato" v-model="alta.estado_contrato" class="select">
              <option value="prueba">Prueba (30 días)</option>
              <option value="activo">Activo</option>
            </select>
          </div>
        </div>
        <fieldset class="modulos">
          <legend>Plan</legend>
          <div class="planes">
            <button v-for="plan in catalogo.planes" :key="plan.codigo" type="button" :aria-pressed="planDe(alta.modulos)?.codigo === plan.codigo"
                    @click="aplicarPlan(alta, plan)"><strong>{{ plan.nombre }}</strong><small>{{ plan.para }}</small></button>
          </div>
          <label v-for="modulo in modulos.filter((m) => !m.obligatorio)" :key="modulo.codigo" class="check">
            <input v-model="alta.modulos" type="checkbox" :value="modulo.codigo"> {{ modulo.nombre }}
            <small v-if="complementos.includes(modulo.codigo)" class="muted">complemento</small>
          </label>
        </fieldset>
        <h3 class="seccion">Administrador</h3>
        <div class="form-grid">
          <div class="field"><label for="e-admin-n">Nombre</label><input id="e-admin-n" v-model="alta.admin.nombre" class="input" required></div>
          <div class="field"><label for="e-admin-u">Usuario</label><input id="e-admin-u" v-model="alta.admin.usuario" class="input" required autocapitalize="none"></div>
          <div class="field"><label for="e-admin-p">Clave inicial</label><input id="e-admin-p" v-model="alta.admin.password" class="input" type="password" minlength="8" required autocomplete="new-password"></div>
        </div>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="alta = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy" :aria-busy="busy">Crear empresa</button>
        </div>
      </form>
    </AppModal>

    <AppModal :open="!!contrato" :title="`Contrato de ${contrato?.nombre}`" width="40rem" @close="contrato = null">
      <form v-if="contrato" @submit.prevent="guardarContrato">
        <div class="form-grid">
          <div class="field">
            <label for="c-estado">Estado</label>
            <select id="c-estado" v-model="contrato.estado" class="select">
              <option v-for="(label, value) in ESTADOS_CONTRATO" :key="value" :value="value">{{ label }}</option>
            </select>
          </div>
          <div class="field"><label for="c-fin">Fin de la prueba o vigencia</label><input id="c-fin" v-model="contrato.fecha_fin" class="input" type="date"></div>
          <div class="field"><label for="c-mes">Mensualidad</label><input id="c-mes" v-model.number="contrato.mensualidad" class="input" type="number" min="0" placeholder="Sin definir"></div>
          <div class="field"><label for="c-venc">Próximo vencimiento</label><input id="c-venc" v-model="contrato.proximo_vencimiento" class="input" type="date"></div>
        </div>
        <fieldset class="modulos">
          <legend>Plan: {{ planDe(contrato.modulos)?.nombre || 'Personalizado' }}</legend>
          <div class="planes">
            <button v-for="plan in catalogo.planes" :key="plan.codigo" type="button" :aria-pressed="planDe(contrato.modulos)?.codigo === plan.codigo"
                    @click="aplicarPlan(contrato, plan)"><strong>{{ plan.nombre }}</strong><small>{{ plan.para }}</small></button>
          </div>
          <label v-for="modulo in modulos.filter((m) => !m.obligatorio)" :key="modulo.codigo" class="check">
            <input v-model="contrato.modulos" type="checkbox" :value="modulo.codigo"> {{ modulo.nombre }}
            <small v-if="complementos.includes(modulo.codigo)" class="muted">complemento</small>
          </label>
        </fieldset>
        <div class="field espacio"><label for="c-notas">Notas comerciales</label>
          <input id="c-notas" v-model="contrato.notas_comerciales" class="input" maxlength="300" placeholder="Precio de lanzamiento, descuento del piloto…"></div>
        <p class="muted">Suspender nunca es automático: avisa al cliente antes. Suspendido no pierde datos.</p>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="contrato = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy" :aria-busy="busy">Guardar contrato</button>
        </div>
      </form>
    </AppModal>

    <AppModal :open="!!cobros" :title="`Pagos de ${cobros?.restaurante.nombre}`" width="44rem" @close="cobros = null">
      <template v-if="cobros">
        <p><span class="cuenta" :class="cobros.suscripcion.cuenta.estado">{{ cobros.suscripcion.cuenta.texto }}</span>
          <template v-if="cobros.suscripcion.proximo_vencimiento"> · vence {{ formatDate(cobros.suscripcion.proximo_vencimiento) }}</template>
          <template v-if="cobros.suscripcion.mensualidad"> · {{ formatMoney(cobros.suscripcion.mensualidad) }} al mes</template></p>
        <form class="pago" @submit.prevent="registrarPago">
          <div class="field"><label for="p-valor">Valor recibido</label><input id="p-valor" v-model.number="cobros.form.valor" class="input" type="number" min="1" required></div>
          <div class="field"><label for="p-meses">Meses que paga</label><input id="p-meses" v-model.number="cobros.form.meses" class="input" type="number" min="1" max="12"></div>
          <div class="field"><label for="p-fecha">Fecha</label><input id="p-fecha" v-model="cobros.form.fecha" class="input" type="date"></div>
          <div class="field"><label for="p-medio">Medio</label>
            <select id="p-medio" v-model="cobros.form.medio" class="select"><option v-for="(l, v) in MEDIOS" :key="v" :value="v">{{ l }}</option></select></div>
          <div class="field"><label for="p-ref">Referencia</label><input id="p-ref" v-model="cobros.form.referencia" class="input" maxlength="60"></div>
          <div class="field"><label for="p-fact">Factura del servicio</label><input id="p-fact" v-model="cobros.form.factura" class="input" maxlength="40"></div>
          <div class="form-actions"><button class="btn" type="submit" :disabled="busy || !cobros.form.valor">Registrar pago</button></div>
        </form>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>Fecha</th><th>Cubre</th><th class="num">Valor</th><th>Medio</th><th>Factura</th></tr></thead>
            <tbody>
              <tr v-for="p in cobros.pagos" :key="p.id">
                <td>{{ formatDate(p.fecha) }}</td>
                <td>{{ formatDate(p.periodo_desde) }} a {{ formatDate(p.periodo_hasta) }}</td>
                <td class="num">{{ formatMoney(p.valor) }}</td>
                <td>{{ MEDIOS[p.medio] }}<small v-if="p.referencia" class="muted bloque">{{ p.referencia }}</small></td>
                <td>{{ p.factura || '—' }}</td>
              </tr>
            </tbody>
          </table>
          <p v-if="!cobros.pagos.length" class="empty">Sin pagos registrados.</p>
        </div>
      </template>
    </AppModal>
  </main>
</template>

<style scoped>
.plataforma {
  max-width: 76rem;
  margin: 0 auto;
  padding: var(--space-6) var(--space-4);
}

.empresa {
  margin-bottom: var(--space-4);
}

.empresa-head {
  padding: var(--space-4);
  border-bottom: 1px solid var(--linea);
}

.seccion {
  margin: var(--space-5) 0 var(--space-3);
  font-size: var(--text-lg);
}

.modulos {
  margin: var(--space-4) 0 0;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
}

.planes {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.planes button {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--linea-fuerte);
  border-radius: var(--radio);
  background: var(--superficie);
  text-align: left;
  cursor: pointer;
}

.planes small {
  color: var(--acero);
  font-size: var(--text-sm);
}

.planes [aria-pressed='true'] {
  border: 2px solid var(--accion);
  background: var(--accion-suave);
}

.cuenta {
  font-weight: 700;
}

.cuenta.en_mora,
.cuenta.prueba_vencida,
.alerta {
  color: var(--estado-cancelado);
  font-weight: 700;
}

.cuenta.por_vencer {
  color: var(--estado-pendiente);
}

.cuenta.al_dia {
  color: var(--estado-entregado);
}

.bloque {
  display: block;
}

.espacio {
  margin-top: var(--space-3);
}

.pago .form-actions {
  grid-column: 1 / -1;
}

.pago {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: var(--space-3);
  align-items: end;
  margin: var(--space-3) 0 var(--space-4);
  padding: var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
}
</style>
