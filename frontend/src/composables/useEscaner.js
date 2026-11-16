import { onMounted, onBeforeUnmount } from 'vue'

/*
  Lector de código de barras (ADR-058). Los lectores USB o Bluetooth se comportan como un teclado: escriben el
  código muy rápido y terminan con Enter. Se distinguen de una persona por el tiempo entre teclas, así se puede
  escanear sin tocar ningún campo. Si el lector escribe dentro de un campo, el código igual se reconoce.
*/
const MAX_ENTRE_TECLAS = 50
const MIN_LARGO = 3

export function useEscaner(alLeer) {
  let buffer = ''
  let ultima = 0

  function onKeydown(event) {
    const ahora = Date.now()
    if (event.key === 'Enter') {
      const codigo = buffer
      buffer = ''
      if (codigo.length >= MIN_LARGO && ahora - ultima <= MAX_ENTRE_TECLAS * 2) {
        event.preventDefault()
        event.stopPropagation()
        alLeer(codigo, event.target)
      }
      return
    }
    if (event.key.length !== 1 || event.ctrlKey || event.altKey || event.metaKey) return
    // Una pausa larga significa que escribe una persona: se empieza de nuevo
    buffer = ahora - ultima > MAX_ENTRE_TECLAS ? event.key : buffer + event.key
    ultima = ahora
  }

  onMounted(() => window.addEventListener('keydown', onKeydown, true))
  onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown, true))
}
