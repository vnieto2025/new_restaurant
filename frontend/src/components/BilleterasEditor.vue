<script setup>
import { ref, onMounted } from 'vue'
import { postData } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useAction } from '@/composables/useAction'
import { mediaUrl } from '@/utils/format'
import { leerImagen } from '@/utils/imagen'
import AppModal from '@/components/AppModal.vue'

// Billeteras para que el cliente sepa cómo pagar (ADR-060): se muestran al pagar desde el celular, en caja y en las tirillas
const auth = useAuthStore()
const { busy, attempt, quiet } = useAction()
const billeteras = ref([])
const form = ref(null)
const borrar = ref(null)

async function load() {
  billeteras.value = (await quiet(() => postData('/billetera/list'))) || []
}

function nueva() {
  form.value = { nombre: '', telefono: '', titular: '', orden: billeteras.value.length + 1, activo: true, qr: null, vista: null, qr_archivo: null }
}

async function elegirQr(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  const imagen = await leerImagen(file).catch(() => null)
  if (imagen) Object.assign(form.value, { qr_archivo: imagen.archivo, vista: imagen.vista, quitar_qr: false })
}

async function guardar() {
  const { id, nombre, telefono, titular, orden, activo, qr_archivo: qrArchivo, quitar_qr: quitarQr } = form.value
  const ok = await attempt(() => postData('/billetera/save', {
    billetera_id: id || null, nombre: nombre.trim(), telefono: telefono?.trim() || null, titular: titular?.trim() || null,
    orden: Number(orden) || 0, activo, ...(qrArchivo ? { qr_archivo: qrArchivo } : {}), ...(quitarQr ? { quitar_qr: true } : {}),
  }), { success: 'Billetera guardada.' })
  if (ok) {
    form.value = null
    await Promise.all([load(), auth.refresh()])
  }
}

async function confirmarBorrar() {
  const ok = await attempt(() => postData('/billetera/delete', { billetera_id: borrar.value.id }), { success: 'Billetera eliminada.' })
  borrar.value = null
  if (ok !== undefined) await Promise.all([load(), auth.refresh()])
}

onMounted(load)
</script>

<template>
  <div class="billeteras-editor">
    <div class="cabeza">
      <p class="muted">Nequi, Daviplata u otras: el cliente las ve al pagar desde el celular, en la caja y en la cuenta impresa. Solo
        informan; el cobro se registra en caja con su medio de pago.</p>
      <button v-escribe class="btn btn-secundario" type="button" @click="nueva">Agregar billetera</button>
    </div>
    <ul v-if="billeteras.length" class="lista">
      <li v-for="b in billeteras" :key="b.id" class="fila" :class="{ inactiva: !b.activo }">
        <img v-if="b.qr" :src="mediaUrl(b.qr)" :alt="`QR de ${b.nombre}`" class="qr">
        <span v-else class="qr sin">Sin QR</span>
        <div class="datos">
          <strong>{{ b.nombre }}<span v-if="!b.activo" class="muted"> (no se muestra)</span></strong>
          <span>{{ b.telefono || 'Sin teléfono' }}</span>
          <span v-if="b.titular" class="muted">{{ b.titular }}</span>
        </div>
        <div class="actions">
          <button v-escribe class="btn btn-secundario btn-sm" type="button" :aria-label="`Editar ${b.nombre}`"
                  @click="form = { ...b, vista: null, qr_archivo: null }">Editar</button>
          <button v-escribe class="btn btn-secundario btn-sm" type="button" :aria-label="`Eliminar ${b.nombre}`" @click="borrar = b">Eliminar</button>
        </div>
      </li>
    </ul>

    <AppModal :open="!!form" :title="form?.id ? `Editar ${form.nombre}` : 'Agregar billetera'" width="32rem" @close="form = null">
      <form v-if="form" v-escribe @submit.prevent="guardar">
        <div class="form-grid">
          <div class="field">
            <label for="b-nombre">Nombre</label>
            <input id="b-nombre" v-model="form.nombre" class="input" required maxlength="40" placeholder="Nequi">
          </div>
          <div class="field">
            <label for="b-telefono">Teléfono de la billetera</label>
            <input id="b-telefono" v-model="form.telefono" class="input" inputmode="tel" maxlength="20" placeholder="300 123 4567">
          </div>
          <div class="field">
            <label for="b-titular">A nombre de</label>
            <input id="b-titular" v-model="form.titular" class="input" maxlength="80" placeholder="Opcional">
          </div>
          <div class="field">
            <label for="b-orden">Orden</label>
            <input id="b-orden" v-model.number="form.orden" class="input" type="number" min="0">
          </div>
        </div>
        <div class="qr-campo">
          <img v-if="form.vista || (form.qr && !form.quitar_qr)" :src="form.vista || mediaUrl(form.qr)" alt="QR de la billetera" class="qr">
          <div class="datos">
            <span class="etiqueta">Imagen del QR</span>
            <span class="muted">La que te da la app de la billetera para recibir pagos.</span>
            <div class="actions">
              <label class="btn btn-secundario btn-sm subir">
                {{ form.vista || form.qr ? 'Cambiar QR' : 'Subir QR' }}
                <input type="file" accept="image/png,image/jpeg,image/webp" class="visually-hidden" @change="elegirQr">
              </label>
              <button v-if="form.qr && !form.vista && !form.quitar_qr" class="btn btn-secundario btn-sm" type="button"
                      @click="form.quitar_qr = true">Quitar QR</button>
            </div>
          </div>
        </div>
        <label class="check"><input v-model="form.activo" type="checkbox"> Mostrarla a los clientes</label>
        <div class="form-actions">
          <button class="btn btn-secundario" type="button" @click="form = null">Cancelar</button>
          <button class="btn" type="submit" :disabled="busy" :aria-busy="busy">Guardar</button>
        </div>
      </form>
    </AppModal>

    <AppModal :open="!!borrar" :title="`¿Eliminar ${borrar?.nombre}?`" width="26rem" @close="borrar = null">
      <p>Deja de mostrarse a los clientes. Los cobros ya registrados no cambian.</p>
      <div class="form-actions">
        <button class="btn btn-secundario" type="button" @click="borrar = null">Cancelar</button>
        <button v-escribe class="btn" type="button" :disabled="busy" @click="confirmarBorrar">Eliminar</button>
      </div>
    </AppModal>
  </div>
</template>

<style scoped>
.cabeza {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.cabeza p {
  flex: 1 1 20rem;
}

.lista {
  margin: var(--space-3) 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.fila {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
}

.fila.inactiva {
  opacity: 0.6;
}

.qr {
  flex: none;
  width: 4.5rem;
  height: 4.5rem;
  object-fit: contain;
  background: #fff;
  border: 1px solid var(--linea);
  border-radius: var(--radio-sm);
}

.qr.sin {
  display: grid;
  place-items: center;
  color: var(--acero);
  font-size: var(--text-sm);
}

.datos {
  flex: 1 1 10rem;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.qr-campo {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin: var(--space-3) 0;
}

.etiqueta {
  font-weight: 600;
}

.subir {
  cursor: pointer;
}
</style>
