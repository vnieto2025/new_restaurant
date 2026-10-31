"""
Corre todos los recorridos en orden, cada uno sobre la base de desarrollo recién reiniciada, y resume el resultado.

    python correr_todo.py                 todos
    python correr_todo.py cupones pagos   solo esos
    python correr_todo.py --sin-reiniciar no reinicia la base entre recorridos

Necesita el backend y el frontend corriendo (ver README.md). Sale con error si algún recorrido falla.
"""
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BACKEND = AQUI.parent / "backend"
# Orden de construcción del sistema: fase 1 y luego los pasos de la fase 2
RECORRIDOS = ["fase1", "clientes", "facturacion", "inventario", "compras", "domicilios", "avisos", "pagos",
              "cupones", "liquidaciones", "pos_planes", "domicilio_web", "exportar", "solo_lectura", "importar", "contador", "puesta_en_marcha", "analisis"]


def python_backend():
    """ reiniciar_base.py usa las librerías del backend: se corre con su entorno virtual """
    for candidato in (BACKEND / "env" / "Scripts" / "python.exe", BACKEND / "env" / "bin" / "python",
                      BACKEND / ".venv" / "Scripts" / "python.exe", BACKEND / ".venv" / "bin" / "python"):
        if candidato.exists():
            return str(candidato)
    return sys.executable


def main():
    argumentos = [a for a in sys.argv[1:] if not a.startswith("--")]
    reiniciar = "--sin-reiniciar" not in sys.argv
    elegidos = argumentos or RECORRIDOS
    desconocidos = set(elegidos) - set(RECORRIDOS)
    if desconocidos:
        sys.exit(f"Recorridos que no existen: {', '.join(sorted(desconocidos))}. Opciones: {', '.join(RECORRIDOS)}")

    resultados = []
    for nombre in elegidos:
        if reiniciar:
            subprocess.run([python_backend(), str(AQUI / "reiniciar_base.py")], check=True)
        inicio = time.monotonic()
        corrida = subprocess.run([sys.executable, str(AQUI / f"{nombre}.py"), str(AQUI / "capturas" / nombre)],
                                 cwd=AQUI, capture_output=True, text=True)
        segundos = time.monotonic() - inicio
        ok = corrida.returncode == 0
        resultados.append((nombre, ok, segundos))
        print(f"{'OK   ' if ok else 'FALLA'} {nombre} ({segundos:.0f} s)")
        if not ok:
            print("\n".join((corrida.stdout + corrida.stderr).strip().splitlines()[-15:]))

    fallas = [n for n, ok, _ in resultados if not ok]
    print(f"\n{len(resultados) - len(fallas)} de {len(resultados)} recorridos sin errores."
          + (f" Fallaron: {', '.join(fallas)}." if fallas else ""))
    print(f"Capturas en {AQUI / 'capturas'}")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
