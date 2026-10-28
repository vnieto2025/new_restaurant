"""
Cálculo de impuestos sobre precios con impuesto incluido (ADR-021).
Todo en pesos enteros: la base se redondea y el impuesto es la diferencia, así base + impuesto
siempre da el total exacto que pagó el cliente.
"""
from decimal import Decimal, ROUND_HALF_UP


def desglosar(total: int, porcentaje) -> tuple:
    """ Separa un valor con impuesto incluido en (base, impuesto) """
    porcentaje = Decimal(str(porcentaje or 0))
    if not total or porcentaje <= 0:
        return total, 0
    base = (Decimal(total) * 100 / (100 + porcentaje)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(base), total - int(base)


def repartir(valor: int, pesos: list) -> list:
    """ Reparte un valor (el descuento) en proporción a los pesos de cada línea.
        Lo que sobra por redondeo va a las líneas más grandes, para que la suma cuadre exacto. """
    total = sum(pesos)
    if not valor or not total:
        return [0] * len(pesos)
    partes = [valor * peso // total for peso in pesos]
    sobrante = valor - sum(partes)
    for indice in sorted(range(len(pesos)), key=lambda i: pesos[i], reverse=True)[:sobrante]:
        partes[indice] += 1
    return partes


def porcentaje_texto(porcentaje) -> str:
    """ 8.000 -> '8', 19.500 -> '19,5' """
    valor = Decimal(str(porcentaje or 0)).normalize()
    texto = format(valor, "f")
    return texto.replace(".", ",")
