import { onMounted, onBeforeUnmount } from 'vue'

const EVENTOS = ['pointerdown', 'keydown', 'touchstart', 'wheel']

/*
  En una tablet compartida, la identificación del mesero se cierra sola por inactividad
  (doc 08, sección 2) para que la siguiente persona no opere a su nombre.
*/
export function useInactivity(activo, minutos, alVencer) {
  let timer = null

  function reiniciar() {
    clearTimeout(timer)
    if (activo()) timer = setTimeout(alVencer, minutos * 60 * 1000)
  }

  onMounted(() => {
    EVENTOS.forEach((evento) => window.addEventListener(evento, reiniciar, { passive: true }))
    reiniciar()
  })

  onBeforeUnmount(() => {
    clearTimeout(timer)
    EVENTOS.forEach((evento) => window.removeEventListener(evento, reiniciar))
  })

  return { reiniciar }
}
