<script setup>
import { mediaUrl } from '@/utils/format'

/*
  Cómo pagar por billetera (ADR-060): nombre, teléfono, titular y QR. Es informativo: quien paga así le muestra
  el comprobante a la caja, que registra el pago con su medio.
*/
defineProps({
  billeteras: { type: Array, default: () => [] },
  titulo: { type: String, default: 'También puedes pagar por billetera' },
})
</script>

<template>
  <section v-if="billeteras.length" class="billeteras" aria-labelledby="billeteras-titulo">
    <h2 id="billeteras-titulo">{{ titulo }}</h2>
    <ul>
      <li v-for="b in billeteras" :key="b.nombre" class="billetera">
        <img v-if="b.qr" :src="mediaUrl(b.qr)" :alt="`Código QR de ${b.nombre}`" class="qr">
        <div class="datos">
          <strong>{{ b.nombre }}</strong>
          <span v-if="b.telefono" class="telefono">{{ b.telefono }}</span>
          <span v-if="b.titular" class="muted">A nombre de {{ b.titular }}</span>
        </div>
      </li>
    </ul>
    <p class="muted nota">Al pagar, muestra el comprobante para que lo registren.</p>
  </section>
</template>

<style scoped>
.billeteras {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

h2 {
  font-size: var(--text-base);
}

ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 14rem), 1fr));
  gap: var(--space-2);
}

.billetera {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--linea);
  border-radius: var(--radio);
  background: var(--superficie);
}

.qr {
  flex: none;
  width: 6rem;
  height: 6rem;
  object-fit: contain;
  background: #fff;
  image-rendering: pixelated;
}

.datos {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.telefono {
  font-size: var(--text-lg);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.nota {
  font-size: var(--text-sm);
}
</style>
