import os
import secrets
import segno
from dotenv import load_dotenv
from Utils.tools import Tools, CustomException
from Querys.qr import QrQuerys
from Models.qr_acceso_model import QrAccesoModel
from Models.mesa_model import MesaModel

load_dotenv()

# Dirección pública de la carta digital; el QR lleva PUBLIC_URL/q/<token>
PUBLIC_URL = os.getenv("PUBLIC_URL", "http://localhost:5173").rstrip("/")


# Token aleatorio y largo, no adivinable (doc 10A, sección 2)
def new_token():
    return secrets.token_urlsafe(24)


def qr_url(token: str):
    return f"{PUBLIC_URL}/q/{token}"


def qr_svg(url: str):
    return segno.make(url, error="m").svg_inline(scale=8, border=2)


class Qr:

    def __init__(self, db, ctx: dict):
        self.ctx = ctx
        self.tools = Tools()
        self.querys = QrQuerys(db, ctx)

    # QR vigentes de las mesas, con la imagen lista para imprimir (doc 10A, sección 7)
    def list(self, data: dict):

        restaurante = self.querys.get_restaurante_nombre()
        result = []
        for qr, mesa, zona in self.querys.list_qr(data.get("zona_id")):
            url = qr_url(qr.token)
            result.append({
                "id": qr.id,
                "tipo": qr.tipo,
                "mesa_id": mesa.id,
                "mesa": mesa.nombre,
                "zona_id": zona.id,
                "zona": zona.nombre,
                "restaurante": restaurante,
                "activo_mesa": mesa.activo and not mesa.bloqueada,
                "creado_en": qr.creado_en,
                "url": url,
                "svg": qr_svg(url) if data.get("con_imagen") else None,
            })

        msg = "Listado de QR." if result else "No hay QR generados."
        return self.tools.output(200, msg, result)

    # Revocar y generar otro: el anterior deja de funcionar al instante
    def regenerate(self, data: dict):

        mesa = self.querys.get_own(MesaModel, data["mesa_id"], "mesa")
        anterior = self.querys.get_active_by_mesa(mesa.id)
        tipo = anterior.tipo if anterior else ("rapido" if mesa.tipo == "externa" else "mesa")

        self.querys.revoke_by_mesa(mesa.id)
        token = new_token()
        qr_id = self.querys.insert_data(QrAccesoModel, {
            "tipo": tipo, "zona_id": mesa.zona_id, "mesa_id": mesa.id, "token": token,
        }, commit=False)
        self.querys.audit("qr_regenerado", "mesa", mesa.id,
                          antes={"qr_id": anterior.id if anterior else None}, despues={"qr_id": qr_id})

        url = qr_url(token)
        return self.tools.output(200, "QR regenerado. El anterior ya no funciona: imprima el nuevo.",
                                 {"mesa_id": mesa.id, "url": url, "svg": qr_svg(url)})

    def create_for_mesa(self, mesa_id: int, zona_id: int, tipo="mesa"):
        if not self.querys.get_active_by_mesa(mesa_id):
            self.querys.insert_data(QrAccesoModel, {
                "tipo": tipo, "zona_id": zona_id, "mesa_id": mesa_id, "token": new_token(),
            }, commit=False)

    # Si la mesa cambia de zona, el QR sigue siendo el mismo pero apunta a la nueva zona
    def move_to_zone(self, mesa_id: int, zona_id: int):
        qr = self.querys.get_active_by_mesa(mesa_id)
        if not qr:
            raise CustomException("La mesa no tiene QR vigente.")
        qr.zona_id = zona_id
        self.querys.db.flush()
