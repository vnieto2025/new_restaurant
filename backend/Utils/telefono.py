import re
from Utils.tools import CustomException

INDICATIVO = "57"


def normalizar_telefono(valor, obligatorio=False):
    """ Deja solo dígitos con indicativo de país: "300 123 4567" -> "573001234567" (RN-NOT-05).
        Un celular colombiano de 10 dígitos recibe el indicativo 57. """
    if valor in [None, ""]:
        if obligatorio:
            raise CustomException("El teléfono es obligatorio.")
        return None
    digitos = re.sub(r"\D", "", str(valor))
    if len(digitos) == 10 and digitos.startswith("3"):
        digitos = INDICATIVO + digitos
    if not 10 <= len(digitos) <= 15:
        raise CustomException("El teléfono no es válido. Escribe el celular con 10 dígitos.")
    return digitos


def telefono_legible(digitos):
    if digitos and digitos.startswith(INDICATIVO) and len(digitos) == 12:
        local = digitos[2:]
        return f"{local[:3]} {local[3:6]} {local[6:]}"
    return digitos
