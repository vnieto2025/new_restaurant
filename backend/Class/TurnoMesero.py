from Utils.tools import Tools, CustomException, jornada, now
from Querys.base import Querys
from Models.turno_mesero_model import TurnoMeseroModel
from Models.sesion_mesa_model import SesionMesaModel
from Models.mesa_model import MesaModel


class TurnoMesero:
    """ Turno operativo del mesero en la jornada (doc 08A, sección 2) """

    def __init__(self, db, ctx: dict):
        self.db = db
        self.ctx = ctx
        self.tools = Tools()
        self.querys = Querys(db, ctx)

    def open_turn(self, usuario_id=None):
        usuario_id = usuario_id or self.ctx["usuario_id"]
        return self.querys.scoped(TurnoMeseroModel).filter(
            TurnoMeseroModel.usuario_id == usuario_id, TurnoMeseroModel.estado == "abierto").first()

    # Se abre al identificarse, si no hay uno abierto
    def ensure_open(self, dispositivo_id=None):
        if self.open_turn():
            return
        try:
            self.querys.insert_data(TurnoMeseroModel, {
                "usuario_id": self.ctx["usuario_id"],
                "jornada": jornada(tz_name=self.ctx.get("zona_horaria"), inicio=self.ctx.get("hora_inicio_jornada")),
                "inicio": now(),
                "dispositivo_id": dispositivo_id,
            })
        except CustomException:
            # Otro ingreso simultáneo ya lo abrió
            self.db.rollback()

    def current(self):
        turno = self.open_turn()
        return self.tools.output(200, "Turno actual.", self.format(turno) if turno else None)

    # No se cierra con mesas a su cargo sin reasignarlas (RN-MSR-04)
    def close(self):
        turno = self.open_turn()
        if not turno:
            raise CustomException("No tienes un turno abierto.", 409)
        mesas = self.querys.scoped(SesionMesaModel).join(MesaModel, MesaModel.id == SesionMesaModel.mesa_id).filter(
            SesionMesaModel.mesero_id == self.ctx["usuario_id"], SesionMesaModel.estado == "abierta",
            SesionMesaModel.es_externa.is_(False)).add_columns(MesaModel.nombre).all()
        if mesas:
            nombres = ", ".join(nombre for _, nombre in mesas)
            raise CustomException(f"Tienes mesas abiertas ({nombres}). Pide que se las pasen a otro mesero antes de salir.", 409)

        turno.estado, turno.fin = "cerrado", now()
        self.db.commit()
        return self.tools.output(200, "Turno terminado. ¡Buen descanso!", self.format(turno))

    # Al cerrar la jornada se cierran los turnos que queden abiertos (RN-MSR-03)
    def close_all(self):
        abiertos = self.querys.scoped(TurnoMeseroModel).filter(TurnoMeseroModel.estado == "abierto").all()
        for turno in abiertos:
            turno.estado, turno.fin, turno.cierre_automatico = "cerrado", now(), True
        return len(abiertos)

    def format(self, turno):
        return {"id": turno.id, "inicio": turno.inicio, "fin": turno.fin, "estado": turno.estado,
                "jornada": turno.jornada, "cierre_automatico": turno.cierre_automatico}
