// Lee un archivo de imagen como base64 para enviarlo en el JSON (ADR-049), con sus medidas para avisar antes de subir
export function leerImagen(file) {
  return new Promise((resolve, reject) => {
    const lector = new FileReader()
    lector.onerror = () => reject(new Error('No se pudo leer el archivo.'))
    lector.onload = () => {
      const vista = String(lector.result)
      const imagen = new Image()
      imagen.onload = () => resolve({ archivo: vista.split(',')[1], vista, ancho: imagen.width, alto: imagen.height })
      imagen.onerror = () => reject(new Error('El archivo no es una imagen válida.'))
      imagen.src = vista
    }
    lector.readAsDataURL(file)
  })
}
