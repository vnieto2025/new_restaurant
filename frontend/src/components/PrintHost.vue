<script setup>
import { computed } from 'vue'
import { usePrintStore } from '@/stores/print'
import { formatMoney, formatTime, formatDate, CANALES } from '@/utils/format'

const printer = usePrintStore()
const ticket = computed(() => printer.ticket)

// Documento de venta vigente de una cuenta pagada: el más reciente que no esté anulado (doc 21)
const documento = computed(() => {
  if (ticket.value?.kind !== 'cuenta' || ticket.value.data.estado !== 'pagada') return null
  return (ticket.value.data.documentos || []).find((d) => d.tipo !== 'nota_credito' && d.estado !== 'anulada' && !d.notas?.length) || null
})
</script>

<template>
  <div class="print-root" aria-hidden="true">
    <article v-if="ticket?.kind === 'comanda'" class="tirilla">
      <!-- Comanda de producción: sin precios (doc 18) -->
      <p class="centro">{{ ticket.data.restaurante }}</p>
      <p class="centro grande">{{ ticket.data.punto }}</p>
      <p v-if="ticket.data.es_adicion" class="centro aviso">** ADICIÓN **</p>
      <hr>
      <p class="grande">{{ ticket.data.numero_texto }} · {{ ticket.data.es_externa ? ticket.data.cliente_nombre || ticket.data.mesa : ticket.data.mesa }}</p>
      <p>{{ ticket.data.zona }}<template v-if="ticket.data.canal !== 'tablet'"> · {{ CANALES[ticket.data.canal] }}</template></p>
      <p v-if="ticket.data.mesero">Mesero: {{ ticket.data.mesero }}</p>
      <p>Hora: {{ formatTime(ticket.data.hora_local || ticket.data.creado_en) }}</p>
      <hr>
      <div v-for="item in ticket.data.items" :key="item.id" class="linea">
        <p class="grande">{{ item.cantidad }} x {{ item.nombre }}</p>
        <p v-for="mod in item.modificadores" :key="mod">   + {{ mod }}</p>
        <p v-if="item.nota" class="nota">&gt; {{ item.nota }}</p>
      </div>
      <template v-if="ticket.data.notas">
        <hr>
        <p class="nota">Nota: {{ ticket.data.notas }}</p>
      </template>
      <hr>
      <p class="centro">Impreso {{ formatTime(new Date()) }}</p>
    </article>

    <article v-else-if="ticket?.kind === 'orden'" class="tirilla">
      <!-- Tirilla de orden con precios (para llevar / pre-cuenta). No es factura. -->
      <p class="centro grande">{{ ticket.data.restaurante.nombre }}</p>
      <p v-if="ticket.data.restaurante.direccion" class="centro">{{ ticket.data.restaurante.direccion }}</p>
      <p v-if="ticket.data.restaurante.telefono" class="centro">Tel. {{ ticket.data.restaurante.telefono }}</p>
      <hr>
      <p class="grande">Orden {{ ticket.data.numero_texto }}</p>
      <p>{{ ticket.data.mesa_tipo === 'externa' ? ticket.data.cliente_nombre || ticket.data.mesa : `${ticket.data.zona} · ${ticket.data.mesa}` }}</p>
      <p>{{ formatTime(ticket.data.hora_local || ticket.data.creado_en) }}</p>
      <template v-if="ticket.data.entrega">
        <!-- El domiciliario sale con esta tirilla (doc 15B) -->
        <hr>
        <p class="grande">DOMICILIO · {{ ticket.data.entrega.zona_envio }}</p>
        <p>{{ ticket.data.entrega.direccion }}</p>
        <p v-if="ticket.data.entrega.barrio">{{ ticket.data.entrega.barrio }}</p>
        <p v-if="ticket.data.entrega.indicaciones">{{ ticket.data.entrega.indicaciones }}</p>
        <p>Tel. {{ ticket.data.entrega.telefono }}</p>
      </template>
      <hr>
      <div v-for="item in ticket.data.items" :key="item.id" class="linea fila">
        <span>{{ item.cantidad }} x {{ item.nombre }}<template v-if="item.modificadores?.length"> ({{ item.modificadores.map((m) => m.nombre).join(', ') }})</template></span>
        <span>{{ formatMoney(item.total) }}</span>
      </div>
      <hr>
      <p v-if="ticket.data.entrega?.tarifa" class="fila"><span>Domicilio</span><span>{{ formatMoney(ticket.data.entrega.tarifa) }}</span></p>
      <p class="fila grande"><span>Total</span><span>{{ formatMoney(ticket.data.total + (ticket.data.entrega?.tarifa || 0)) }}</span></p>
      <p class="centro pie">Documento no válido como factura</p>
    </article>

    <article v-else-if="ticket?.kind === 'cuenta'" class="tirilla">
      <!-- Precuenta (abierta) o comprobante de pago (pagada), doc 19A sección 3. No es factura. -->
      <p class="centro grande">{{ ticket.data.restaurante.nombre }}</p>
      <p v-if="ticket.data.restaurante.direccion" class="centro">{{ ticket.data.restaurante.direccion }}</p>
      <p v-if="ticket.data.restaurante.telefono" class="centro">Tel. {{ ticket.data.restaurante.telefono }}</p>
      <hr>
      <template v-if="documento">
        <p class="grande">{{ documento.tipo_texto }}</p>
        <p class="grande">No. {{ documento.numero }}</p>
        <p v-if="documento.receptor_documento">Cliente: {{ documento.receptor_nombre }}</p>
        <p v-if="documento.receptor_documento">{{ documento.receptor_tipo_documento }} {{ documento.receptor_documento }}</p>
        <p>Comprobante interno {{ ticket.data.numero_texto }}</p>
      </template>
      <p v-else class="grande">{{ ticket.data.estado === 'pagada' ? `Comprobante ${ticket.data.numero_texto}` : 'Precuenta' }}</p>
      <p>{{ ticket.data.mesa_tipo === 'externa' ? ticket.data.cliente_nombre || ticket.data.mesa : `${ticket.data.zona} · ${ticket.data.mesa}` }}</p>
      <p v-if="ticket.data.mesero">Mesero: {{ ticket.data.mesero }}</p>
      <p>{{ formatTime(ticket.data.pagada_local || new Date()) }}</p>
      <hr>
      <div v-for="linea in ticket.data.lineas" :key="linea.id" class="linea">
        <p class="fila"><span>{{ linea.cantidad }} x {{ linea.nombre }}</span><span>{{ formatMoney(linea.total) }}</span></p>
        <p v-for="mod in linea.modificadores" :key="mod.nombre">   + {{ mod.nombre }}</p>
      </div>
      <hr>
      <p class="fila"><span>Subtotal</span><span>{{ formatMoney(ticket.data.subtotal) }}</span></p>
      <p v-if="ticket.data.descuento" class="fila"><span>Descuento</span><span>-{{ formatMoney(ticket.data.descuento) }}</span></p>
      <p v-for="c in (ticket.data.cupones || []).filter((x) => x.tipo !== 'envio' && x.valor)" :key="c.redencion_id" class="fila">
        <span>Cupón {{ c.codigo }}</span><span>-{{ formatMoney(c.valor) }}</span></p>
      <p v-if="ticket.data.envio" class="fila"><span>Domicilio</span><span>{{ formatMoney(ticket.data.envio) }}</span></p>
      <p v-if="ticket.data.descuento_envio" class="fila"><span>Envío gratis (cupón)</span><span>-{{ formatMoney(ticket.data.descuento_envio) }}</span></p>
      <p v-if="ticket.data.propina" class="fila"><span>Propina voluntaria</span><span>{{ formatMoney(ticket.data.propina) }}</span></p>
      <p v-else-if="ticket.data.estado !== 'pagada' && ticket.data.propina_sugerida" class="fila">
        <span>Propina sugerida {{ ticket.data.propina_porcentaje }} %</span><span>{{ formatMoney(ticket.data.propina_sugerida) }}</span>
      </p>
      <p class="fila grande"><span>Total</span><span>{{ formatMoney(ticket.data.total) }}</span></p>
      <template v-if="documento">
        <!-- Desglose: el precio ya incluye el impuesto; la propina no hace parte de la base -->
        <hr>
        <p class="fila"><span>Base</span><span>{{ formatMoney(documento.base) }}</span></p>
        <p v-for="imp in documento.impuestos_detalle" :key="imp.impuesto + imp.porcentaje" class="fila">
          <span>{{ imp.impuesto }} {{ imp.porcentaje_texto }}</span><span>{{ formatMoney(imp.valor) }}</span>
        </p>
        <p class="fila"><span>Valor de la venta</span><span>{{ formatMoney(documento.total) }}</span></p>
      </template>
      <template v-if="ticket.data.estado === 'pagada'">
        <hr>
        <p v-for="pago in ticket.data.pagos.filter((p) => p.estado === 'aplicado')" :key="pago.id" class="fila">
          <span>{{ pago.medio }}<template v-if="pago.referencia"> {{ pago.referencia }}</template></span>
          <span>{{ formatMoney(pago.recibido || pago.monto) }}</span>
        </p>
        <p v-for="pago in ticket.data.pagos.filter((p) => p.cambio)" :key="`c${pago.id}`" class="fila">
          <span>Cambio</span><span>{{ formatMoney(pago.cambio) }}</span>
        </p>
      </template>
      <p v-if="ticket.data.estado !== 'pagada'" class="centro pie">La propina es voluntaria</p>
      <template v-if="documento">
        <hr>
        <p v-if="documento.resolucion" class="pie">
          Resolución {{ documento.resolucion.numero }} del {{ formatDate(documento.resolucion.vigente_desde) }},
          numeración {{ documento.resolucion.prefijo }}{{ documento.resolucion.desde }} a {{ documento.resolucion.prefijo }}{{ documento.resolucion.hasta }}<template
            v-if="documento.resolucion.vigente_hasta">, vigente hasta {{ formatDate(documento.resolucion.vigente_hasta) }}</template>.
        </p>
        <p v-if="documento.cufe" class="pie cufe">CUFE: {{ documento.cufe }}</p>
        <p v-else class="pie">Documento en proceso de validación electrónica.</p>
      </template>
      <p v-else class="centro pie">Documento no válido como factura</p>
      <template v-if="ticket.data.cupon_obsequio">
        <!-- Cupón para la próxima visita (doc 25A, sección 3) -->
        <hr>
        <p class="centro grande">Tu próxima visita</p>
        <p class="centro">{{ ticket.data.cupon_obsequio.descripcion }}</p>
        <p class="centro grande">{{ ticket.data.cupon_obsequio.codigo }}</p>
        <p class="centro pie">Válido hasta el {{ formatDate(ticket.data.cupon_obsequio.termina) }}. Solo para {{ ticket.data.cliente?.nombre }}.</p>
      </template>
    </article>

    <article v-else-if="ticket?.kind === 'liquidacion'" class="tirilla">
      <!-- Comprobante de pago de propinas o entregas (doc 26A, sección 4) -->
      <p class="centro grande">{{ ticket.data.liquidacion.restaurante }}</p>
      <p class="centro">Comprobante de {{ ticket.data.liquidacion.tipo === 'propinas' ? 'propinas' : 'pago de entregas' }}</p>
      <hr>
      <p class="grande">{{ ticket.data.linea.nombre }}</p>
      <p>Periodo {{ formatDate(ticket.data.liquidacion.desde) }} al {{ formatDate(ticket.data.liquidacion.hasta) }}</p>
      <hr>
      <template v-if="ticket.data.liquidacion.tipo === 'propinas'">
        <p v-if="ticket.data.linea.individual" class="fila"><span>De sus mesas</span><span>{{ formatMoney(ticket.data.linea.individual) }}</span></p>
        <p class="fila"><span>Del pozo</span><span>{{ formatMoney(ticket.data.linea.pozo) }}</span></p>
      </template>
      <template v-else>
        <p class="fila"><span>{{ ticket.data.linea.entregas }} entregas</span><span>{{ formatMoney(ticket.data.linea.pago_entregas) }}</span></p>
        <p v-if="ticket.data.linea.propinas" class="fila"><span>Propinas</span><span>{{ formatMoney(ticket.data.linea.propinas) }}</span></p>
        <p v-if="ticket.data.linea.descuentos" class="fila"><span>Faltantes</span><span>-{{ formatMoney(ticket.data.linea.descuentos) }}</span></p>
      </template>
      <p v-for="a in ticket.data.linea.detalle.ajustes || []" :key="a.motivo + a.valor" class="fila">
        <span>Ajuste: {{ a.motivo }}</span><span>{{ formatMoney(a.valor) }}</span></p>
      <p class="fila grande"><span>Total</span><span>{{ formatMoney(ticket.data.linea.total) }}</span></p>
      <p v-if="ticket.data.linea.pagado_en">Pagado {{ formatDate(ticket.data.linea.pagado_en) }} · {{ ticket.data.linea.medio_pago }}
        <template v-if="ticket.data.linea.referencia_pago"> · {{ ticket.data.linea.referencia_pago }}</template></p>
      <p class="pie">&nbsp;</p>
      <p class="pie">Recibí: ______________________</p>
    </article>

    <article v-else-if="ticket?.kind === 'turno'" class="tirilla">
      <!-- Cierre de turno de caja (doc 19A) -->
      <p class="centro grande">Cierre de turno</p>
      <p>Cajero: {{ ticket.data.usuario }}</p>
      <p>Abierto: {{ formatTime(ticket.data.abierto_en) }}</p>
      <p>Cerrado: {{ formatTime(ticket.data.cerrado_en) }}</p>
      <hr>
      <p class="fila"><span>Cuentas cobradas</span><span>{{ ticket.data.resumen.cuentas }}</span></p>
      <p class="fila"><span>Ventas</span><span>{{ formatMoney(ticket.data.resumen.ventas) }}</span></p>
      <p class="fila"><span>Propinas</span><span>{{ formatMoney(ticket.data.resumen.propinas) }}</span></p>
      <p class="fila"><span>Descuentos</span><span>{{ formatMoney(ticket.data.resumen.descuentos) }}</span></p>
      <hr>
      <p v-for="fila in ticket.data.resumen.por_medio" :key="fila.medio" class="fila">
        <span>{{ fila.medio }} ({{ fila.pagos }})</span><span>{{ formatMoney(fila.monto) }}</span>
      </p>
      <hr>
      <p class="fila"><span>Fondo inicial</span><span>{{ formatMoney(ticket.data.fondo_inicial) }}</span></p>
      <p class="fila"><span>Aportes</span><span>{{ formatMoney(ticket.data.resumen.aportes) }}</span></p>
      <p class="fila"><span>Gastos</span><span>-{{ formatMoney(ticket.data.resumen.gastos) }}</span></p>
      <p class="fila"><span>Retiros</span><span>-{{ formatMoney(ticket.data.resumen.retiros) }}</span></p>
      <p class="fila"><span>Efectivo esperado</span><span>{{ formatMoney(ticket.data.efectivo_esperado) }}</span></p>
      <p class="fila"><span>Efectivo contado</span><span>{{ formatMoney(ticket.data.efectivo_contado) }}</span></p>
      <p class="fila grande"><span>Diferencia</span><span>{{ formatMoney(ticket.data.diferencia) }}</span></p>
      <p v-if="ticket.data.observacion" class="nota">{{ ticket.data.observacion }}</p>
    </article>

    <section v-else-if="ticket?.kind === 'qr'" class="hoja">
      <!-- Hoja de QR para recortar y poner en las mesas (doc 10A, sección 7) -->
      <article v-for="qr in ticket.data" :key="qr.id" class="qr">
        <p class="qr-restaurante">{{ qr.restaurante }}</p>
        <div class="qr-imagen" v-html="qr.svg"></div>
        <p class="qr-mesa">{{ qr.tipo === 'rapido' ? 'Para llevar' : qr.tipo === 'domicilio' ? 'Domicilios' : qr.mesa }}</p>
        <p class="qr-zona">{{ qr.tipo === 'rapido' ? 'Pide desde tu celular' : qr.tipo === 'domicilio' ? 'Te lo llevamos a casa' : qr.zona }}</p>
        <p class="qr-instruccion">Escanea para pedir</p>
      </article>
    </section>
  </div>
</template>

<style scoped>
.print-root {
  display: none;
}

.cufe {
  word-break: break-all;
}

@media print {
  .print-root {
    display: block;
  }

  @page tirilla {
    size: 80mm auto;
    margin: 0;
  }

  @page hoja {
    size: letter;
    margin: 12mm;
  }

  .hoja {
    page: hoja;
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8mm;
    font-family: var(--font-ui);
    color: #000;
  }

  .qr {
    break-inside: avoid;
    border: 1px dashed #777;
    padding: 6mm;
    text-align: center;
  }

  .qr-restaurante {
    font-size: 13pt;
    font-weight: 600;
  }

  .qr-imagen :deep(svg) {
    width: 55mm;
    height: 55mm;
  }

  .qr-mesa {
    font-size: 26pt;
    font-weight: 800;
    font-stretch: 70%;
    line-height: 1;
  }

  .qr-zona {
    font-size: 12pt;
    margin-top: 1mm;
  }

  .qr-instruccion {
    margin-top: 3mm;
    font-size: 11pt;
  }

  .tirilla {
    page: tirilla;
    width: 72mm;
    margin: 0 auto;
    padding: 3mm 0;
    font-family: var(--font-papel);
    font-size: 11pt;
    line-height: 1.3;
    color: #000;
  }

  .tirilla p {
    margin: 0 0 1mm;
  }

  .centro {
    text-align: center;
  }

  .grande {
    font-size: 14pt;
    font-weight: 600;
  }

  .aviso {
    font-weight: 600;
  }

  .nota {
    font-style: italic;
  }

  .linea {
    margin-bottom: 1.5mm;
  }

  .fila {
    display: flex;
    justify-content: space-between;
    gap: 2mm;
  }

  .pie {
    margin-top: 3mm;
    font-size: 9pt;
  }

  hr {
    border: none;
    border-top: 1px dashed #000;
    margin: 2mm 0;
  }
}
</style>
