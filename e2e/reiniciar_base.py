"""
Deja la base de desarrollo como recién instalada: borra todas las tablas y vuelve a correr seed.py con los datos
demo y el superadministrador de soporte. Usa la configuración de backend/.env.

Solo para desarrollo: se niega a correr con APP_ENV=production o contra la base de pruebas automáticas.
"""
import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(BACKEND / ".env")
if os.getenv("APP_ENV") == "production":
    sys.exit("No se reinicia una base de producción.")

import Models  # noqa: E402,F401
from Config.db import BASE, admin_engine  # noqa: E402
from sqlalchemy import text  # noqa: E402

if admin_engine.url.database == os.getenv("DB_NAME_TEST"):
    sys.exit("Esa es la base de las pruebas automáticas: los recorridos usan la de desarrollo.")

BASE.metadata.drop_all(bind=admin_engine)
with admin_engine.begin() as conexion:
    conexion.execute(text("DROP TABLE IF EXISTS alembic_version"))
subprocess.run([sys.executable, "seed.py", "--demo", "--superadmin", "soporte", "--password", "Soporte12345",
                "--nombre", "Soporte plataforma"], check=True, capture_output=True)
print("Base de desarrollo reiniciada con los datos demo.")
