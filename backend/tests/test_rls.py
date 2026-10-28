"""
Row Level Security (ADR-023): aunque una consulta olvide filtrar por empresa, la base de datos
solo entrega y acepta filas de la empresa de la petición.
"""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from Config.db import SessionLocal, engine
from Querys.base import Querys
from Models.zona_model import ZonaModel
from Models.orden_model import OrdenModel


def test_la_aplicacion_no_es_superusuario():
    with engine.connect() as conn:
        rol = conn.execute(text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")).one()
    assert rol == (False, False)


def test_consulta_sin_filtro_solo_ve_su_empresa(esquina, napoli):
    _, sesion = esquina["admin.esquina"]
    _, sesion_napoli = napoli["napoli"]
    db = SessionLocal()
    try:
        # Sin empresa fijada (ingreso, plataforma) se ven las dos
        empresas = {z.empresa_id for z in db.query(ZonaModel).all()}
        assert len(empresas) >= 2

        Querys(db, {"empresa_id": empresa_de(sesion), "restaurante_id": sesion["restaurante"]["id"], "usuario_id": 1})
        db.rollback()  # nueva transacción: la empresa se fija al empezar
        # Consulta "olvidando" el filtro: RLS la limita igual
        assert {z.empresa_id for z in db.query(ZonaModel).all()} == {empresa_de(sesion)}
        assert db.query(OrdenModel).filter(OrdenModel.empresa_id == empresa_de(sesion_napoli)).count() == 0
    finally:
        db.close()


def test_no_se_puede_escribir_en_otra_empresa(esquina, napoli):
    _, sesion = esquina["admin.esquina"]
    _, sesion_napoli = napoli["napoli"]
    db = SessionLocal()
    try:
        Querys(db, {"empresa_id": empresa_de(sesion), "restaurante_id": sesion["restaurante"]["id"], "usuario_id": 1})
        db.rollback()
        intruso = ZonaModel({"empresa_id": empresa_de(sesion_napoli), "restaurante_id": sesion_napoli["restaurante"]["id"],
                             "nombre": "Zona intrusa"})
        db.add(intruso)
        with pytest.raises(DBAPIError) as error:
            db.flush()
        # Violación de la política de RLS (el texto depende del idioma del servidor)
        assert error.value.orig.__class__.__name__ == "InsufficientPrivilege"
    finally:
        db.rollback()
        db.close()


def empresa_de(sesion):
    db = SessionLocal()
    try:
        return db.execute(text("SELECT empresa_id FROM restaurante WHERE id = :r"), {"r": sesion["restaurante"]["id"]}).scalar()
    finally:
        db.close()
