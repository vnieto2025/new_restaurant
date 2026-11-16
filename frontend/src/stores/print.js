import { ref, nextTick } from 'vue'
import { defineStore } from 'pinia'

/*
  Impresión de tirillas con el diálogo del navegador (ADR-005, prototipo de la fase 0).
  La tirilla se arma en PrintHost y se imprime con estilos de 80 mm.
  Más adelante un agente local o una impresora en red pueden tomar el mismo contenido.
*/
export const usePrintStore = defineStore('print', () => {
  const ticket = ref(null)

  async function print(kind, data) {
    ticket.value = { kind, data }
    await nextTick()
    // Las imágenes de la tirilla (logo, QR de billeteras) deben haber cargado; si alguna falla, se imprime sin ella
    const imagenes = [...document.querySelectorAll('.print-root img')].filter((img) => !img.complete)
    await Promise.race([
      Promise.all(imagenes.map((img) => new Promise((resolve) => { img.onload = img.onerror = resolve }))),
      new Promise((resolve) => setTimeout(resolve, 3000)),
    ])
    // Deja que el navegador pinte la tirilla antes de abrir el diálogo
    await new Promise((resolve) => requestAnimationFrame(() => setTimeout(resolve, 50)))
    window.print()
  }

  // Imprime la página actual (reportes en hoja carta), sin menús ni botones
  function printPage() {
    const html = document.documentElement
    html.classList.add('imprimir-pagina')
    window.addEventListener('afterprint', () => html.classList.remove('imprimir-pagina'), { once: true })
    window.print()
  }

  return { ticket, print, printPage }
})
