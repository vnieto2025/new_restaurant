"""
Migraciones del esquema (ADR-025). Corren con el usuario dueño de las tablas (DB_USER),
nunca con el rol de la aplicación. Uso:

    env\\Scripts\\python -m alembic revision --autogenerate -m "descripción"
    env\\Scripts\\python -m alembic upgrade head      (seed.py lo hace solo)
"""
import sys
from pathlib import Path
from alembic import context

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import Models  # noqa: E402,F401 (registra todas las tablas)
from Config.db import BASE, admin_engine  # noqa: E402

target_metadata = BASE.metadata


def run_migrations_offline():
    context.configure(url=admin_engine.url.render_as_string(hide_password=False), target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    with admin_engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
