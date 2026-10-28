"""
Franjas horarias semanales en la hora local del restaurante (doc 08A, sección 4; RG-08).
Una franja de 22:00 a 02:00 del viernes cubre el viernes desde las 22:00 y el sábado hasta las 02:00.
"""
from datetime import datetime, timedelta
from Utils.tools import now, to_local

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def en_franja(local, franja):
    """ ¿El momento local cae dentro de la franja? """
    hora = local.time()
    dia = local.weekday()
    if franja.desde < franja.hasta:
        return franja.dia_semana == dia and franja.desde <= hora < franja.hasta
    # Cruza la medianoche: la parte de la noche es del día de la franja, la madrugada del día siguiente
    if franja.dia_semana == dia and hora >= franja.desde:
        return True
    return franja.dia_semana == (dia - 1) % 7 and hora < franja.hasta


def franja_actual(franjas: list, tz_name: str, momento=None):
    local = to_local(momento or now(), tz_name)
    return next((f for f in franjas if en_franja(local, f)), None)


def abierto(franjas: list, tz_name: str, momento=None):
    """ Sin franjas configuradas no hay restricción """
    return not franjas or franja_actual(franjas, tz_name, momento) is not None


def proxima_apertura(franjas: list, tz_name: str, momento=None):
    """ Texto corto con la próxima apertura, para avisar al cliente: "hoy a las 18:00", "el lunes a las 07:00" """
    if not franjas:
        return None
    local = to_local(momento or now(), tz_name)
    # La próxima apertura es el inicio de franja más cercano en los próximos ocho días
    inicios = []
    for franja in franjas:
        for dias in range(8):
            fecha = local.date() + timedelta(days=dias)
            if fecha.weekday() == franja.dia_semana:
                inicio = datetime.combine(fecha, franja.desde, tzinfo=local.tzinfo)
                if inicio > local:
                    inicios.append(inicio)
    if not inicios:
        return None
    siguiente = min(inicios)
    hora = siguiente.strftime("%H:%M")
    if siguiente.date() == local.date():
        return f"hoy a las {hora}"
    if siguiente.date() == local.date() + timedelta(days=1):
        return f"mañana a las {hora}"
    return f"el {DIAS[siguiente.weekday()]} a las {hora}"
